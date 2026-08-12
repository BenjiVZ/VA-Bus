"""
Lógica de negocio compartida para resolver el resultado de una operación de
Débito Inmediato, reutilizada por las vistas y por el validador automático.
"""
import logging
from datetime import timedelta

from django.utils import timezone

from reservas.services import confirmar_grupo_pago

logger = logging.getLogger('r4conecta')

# Ventana de pago que se le devuelve al cliente cuando el banco rechaza y la
# original ya venció (es la misma que usa Reserva.save()).
MINUTOS_PARA_PAGAR = 15


def apartar_grupo(grupo_pago):
    """Mientras el banco decide, la reserva no puede vencerse.

    'apartado' es el mismo estado que deja un comprobante subido a mano:
    `cancelar_expiradas` no lo toca y la app y la web lo muestran como
    "EN VALIDACIÓN". Sin esto la reserva seguía en 'pendiente' con su ventana
    de 15 min y se cancelaba sola —liberando el asiento— mientras el dinero ya
    estaba debitado y el banco todavía no respondía.
    """
    from reservas.models import Reserva

    return (Reserva.objects
            .filter(grupo_pago=grupo_pago, estado='pendiente')
            .update(estado='apartado'))


def devolver_grupo_a_pendiente(grupo_pago):
    """El cobro no prosperó: soltar el apartado para que el cliente reintente.

    No se toca nada si queda otro cobro vivo o un comprobante en revisión para
    el mismo grupo (ese apartado no es nuestro). Si la ventana de pago ya había
    vencido se renueva: si no, la tarea de expiración cancelaría la reserva en
    el minuto siguiente y el cliente no alcanzaría a reintentar.
    """
    from pagos.models import ComprobantePago
    from reservas.models import Reserva
    from .models import OperacionDebitoOTP

    if OperacionDebitoOTP.objects.filter(
            grupo_pago=grupo_pago,
            estado__in=['procesando', 'en_espera', 'aceptada']).exists():
        return 0
    if ComprobantePago.objects.filter(
            grupo_pago=grupo_pago).exclude(estado='rechazado').exists():
        return 0

    devueltas = (Reserva.objects
                 .filter(grupo_pago=grupo_pago, estado='apartado')
                 .update(estado='pendiente'))
    if devueltas:
        ahora = timezone.now()
        (Reserva.objects
         .filter(grupo_pago=grupo_pago, estado='pendiente',
                 fecha_expiracion__lt=ahora + timedelta(minutes=5))
         .update(fecha_expiracion=ahora + timedelta(minutes=MINUTOS_PARA_PAGAR)))
    return devueltas


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
        _mover_reservas(apartar_grupo, op, 'apartar')
        return 'en_espera'

    op.estado = 'rechazada'
    op.save()
    _mover_reservas(devolver_grupo_a_pendiente, op, 'liberar')
    return 'rechazada'


def _mover_reservas(fn, op, que):
    """Mueve las reservas del grupo sin poder tumbar la respuesta al cliente."""
    try:
        fn(op.grupo_pago)
    except Exception:  # noqa: BLE001
        logger.exception('Op %s: no se pudo %s las reservas del grupo %s',
                         op.pk, que, op.grupo_pago)
