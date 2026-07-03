"""
Lógica de negocio compartida para resolver el resultado de una operación de
Débito Inmediato, reutilizada por las vistas y por el validador automático.
"""
import logging

from reservas.services import confirmar_grupo_pago

logger = logging.getLogger('r4conecta')


def validar_pendientes(limite=200):
    """Consulta al banco todas las operaciones en espera (AC00) y las resuelve.

    Reutilizado por el panel del admin, la página de prueba y el comando
    r4_validar_pendientes. Devuelve un dict con el conteo por resultado.
    """
    from . import services
    from .models import OperacionDebitoOTP

    res = {'total': 0, 'aprobadas': 0, 'en_espera': 0, 'rechazadas': 0, 'error': 0}
    pendientes = OperacionDebitoOTP.objects.filter(
        estado='en_espera').exclude(operacion_id='')[:limite]
    for op in pendientes:
        res['total'] += 1
        try:
            resp = services.consultar_operacion(op.operacion_id)
        except services.R4Error:
            res['error'] += 1
            continue
        estado = aplicar_respuesta(op, resp, campo='consulta_response')
        if estado == 'aceptada':
            res['aprobadas'] += 1
        elif estado == 'en_espera':
            res['en_espera'] += 1
        else:
            res['rechazadas'] += 1
    return res


def aplicar_respuesta(op, resp, campo=None):
    """
    Actualiza `op` (OperacionDebitoOTP) según la respuesta del banco y, si fue
    aprobada (ACCP), confirma la reserva (libera/asigna la silla pagada).

    `campo`: nombre del campo JSON donde guardar la respuesta cruda
             ('debito_response' o 'consulta_response'). Opcional.

    Devuelve el nuevo estado: 'aceptada' | 'en_espera' | 'rechazada'.
    """
    code = str(resp.get('code', ''))
    if campo:
        setattr(op, campo, resp)
    op.code = code[:10]
    op.mensaje = str(resp.get('message', ''))[:255]
    if resp.get('reference'):
        op.referencia = str(resp.get('reference'))[:100]
    nuevo_id = resp.get('id') or resp.get('Id')
    if nuevo_id:
        op.operacion_id = str(nuevo_id)[:36]

    aprobado = code == 'ACCP' or resp.get('success') is True
    if aprobado:
        op.estado = 'aceptada'
        op.save()
        try:
            confirmar_grupo_pago(op.grupo_pago)
        except Exception as e:  # noqa: BLE001 — el pago ya se cobró; no romper
            logger.error('Op %s aprobada pero falló confirmar la reserva: %s', op.pk, e)
        return 'aceptada'

    if code == 'AC00':
        op.estado = 'en_espera'
        op.save()
        return 'en_espera'

    op.estado = 'rechazada'
    op.save()
    return 'rechazada'
