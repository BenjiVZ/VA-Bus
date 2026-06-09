"""
Lógica de negocio compartida para resolver el resultado de una operación de
Débito Inmediato, reutilizada por las vistas y por el validador automático.
"""
import logging

from reservas.services import confirmar_grupo_pago

logger = logging.getLogger('r4conecta')


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
        op.referencia = str(resp.get('reference'))[:30]
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
