"""
Módulo de CAJA (taquilla) para el back office.

Flujo pensado para el mostrador: llega el cliente, la cajera busca la ruta,
elige el/los puestos, carga los datos del cliente, registra con qué pagó y
listo — el boleto queda confirmado en el acto (el dinero ya se recibió).

Reutiliza la maquinaria que ya existe, no la duplica:
  · Aerorutas  → BUSQPUESTO (ver libres), TMPPUESTO (apartar), viaje espejo
                 local y ASIGPASA al confirmar (lo hace confirmar_grupo_pago).
  · Locales    → el mapa de asientos desde el layout del autobús.
  · Confirmación, ticket y WebSocket → reservas.services.confirmar_grupo_pago.

Las reservas quedan a nombre del usuario de la cajera (no se crean cuentas
basura por cada cliente de mostrador); los datos del pasajero van en los
campos nombre_pasajero / cedula_pasajero, que son los que salen en el ticket.
"""
import json
import uuid as uuid_lib
from datetime import datetime
from decimal import Decimal, InvalidOperation

from backoffice.auth import staff_requerido
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from reservas.models import Reserva
from reservas.services import confirmar_grupo_pago
from viajes import aerorutas
from viajes.models import ConfiguracionGeneral, RutaAerorutasSnapshot, Viaje
from viajes.views import (
    generar_mapa_desde_layout,
    obtener_o_crear_viaje_espejo,
    _overlay_bloqueos_aerorutas,
)

from .models import MetodoPago, PagoCaja


def _es_aerorutas(viaje_id: str) -> bool:
    """Los viajes de Aerorutas tienen id compuesto 'codrut_inicio_fin_fecha'."""
    return '_' in str(viaje_id)


def _tasa():
    config = ConfiguracionGeneral.load()
    return config.tasa_bcv if config else None


def _dec(valor, campo):
    """Convierte a Decimal o lanza ValueError con un mensaje claro."""
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f'{campo} inválido.')


# ══════════════════════════════════════════════════════════════════
#  Acciones (AJAX)
# ══════════════════════════════════════════════════════════════════

def _accion_buscar(request):
    """Viajes de una fecha: catálogo de Aerorutas + viajes locales."""
    fecha = request.POST.get('fecha') or timezone.localdate().isoformat()
    origen = (request.POST.get('origen') or '').strip()
    destino = (request.POST.get('destino') or '').strip()

    resultados = []

    # ── Aerorutas ──
    try:
        if origen:
            # Barrido EN VIVO desde ese origen: no depende del catálogo
            # precargado, así no se queda ninguna ruta por fuera.
            codigos = [o.get('codofi') for o in aerorutas.consultar_oficinas_cacheado()
                       if o.get('codofi') and o.get('codofi') != origen]
            pares = [(origen, destino)] if destino else [(origen, f) for f in codigos]
            encontrados = aerorutas.barrer_rutas(fecha, pares)
            resultados += aerorutas.construir_viajes(encontrados, fecha)
    except aerorutas.AerorutasError as e:
        return JsonResponse({'ok': False, 'msg': f'Aerorutas no responde: {e}'})

    # Sin precio publicado no se puede vender.
    def _precio(v):
        try:
            return float(v.get('precio_usd') or 0)
        except (TypeError, ValueError):
            return 0
    resultados = [v for v in resultados if _precio(v) > 0]

    # ── Viajes locales (los creados en el Portal de Viajes) ──
    locales = (Viaje.objects
               .filter(activo=True, aerorutas_codrut='', fecha_salida=fecha)
               .select_related('ruta', 'autobus'))
    for v in locales:
        if origen or destino:
            texto = f"{v.ruta.origen} {v.ruta.destino}".upper()
            # Los locales no tienen codofi; se filtran por nombre solo si el
            # usuario escribió algo que calce. Si no calza, no se muestran.
            if origen and origen.upper() not in texto and destino.upper() not in texto:
                continue
        resultados.append({
            'id': str(v.id),
            'local': True,
            'fecha_salida': str(v.fecha_salida),
            'hora_salida': str(v.hora_salida),
            'precio_usd': str(v.precio_usd),
            'asientos_disponibles': None,
            'ruta': {'origen': v.ruta.origen, 'destino': v.ruta.destino},
            'autobus': {'nombre': v.autobus.nombre},
        })

    resultados.sort(key=lambda v: str(v.get('hora_salida') or ''))

    # Destinos realmente alcanzables desde ese origen: con esto el desplegable
    # de destino deja de ofrecer ciudades a las que no sale nada ese día.
    destinos, vistos = [], set()
    for v in resultados:
        nombre = (v.get('ruta') or {}).get('destino') or ''
        if nombre and nombre not in vistos:
            vistos.add(nombre)
            destinos.append(nombre)
    destinos.sort()

    return JsonResponse({'ok': True, 'viajes': resultados,
                         'total': len(resultados), 'destinos': destinos})


def _accion_catalogo(request):
    """Oficinas que ese día tienen salidas publicadas (con precio).

    Sale del catálogo precargado, así que es instantáneo. No se usa para
    bloquear: las que no aparecen se siguen ofreciendo aparte, porque el
    snapshot puede estar incompleto y la cajera igual tiene que poder vender.
    """
    fecha = request.POST.get('fecha') or timezone.localdate().isoformat()

    snap = RutaAerorutasSnapshot.objects.filter(fecha=fecha).first()
    catalogo = snap.data if snap else []

    con_salidas = set()
    for v in catalogo:
        try:
            precio = float(v.get('precio_usd') or 0)
        except (TypeError, ValueError):
            precio = 0
        if precio <= 0:
            continue  # sin precio no se puede vender: Aerorutas no lo publicó
        partes = str(v.get('id') or '').split('_')
        if len(partes) > 2 and partes[1]:
            con_salidas.add(partes[1])

    return JsonResponse({
        'ok': True,
        'origenes': sorted(con_salidas),
        'hay_catalogo': bool(catalogo),
    })


def _accion_asientos(request):
    """Mapa de asientos del viaje elegido (Aerorutas o local)."""
    viaje_id = (request.POST.get('viaje_id') or '').strip()
    if not viaje_id:
        return JsonResponse({'ok': False, 'msg': 'Falta el viaje.'})

    if _es_aerorutas(viaje_id):
        try:
            codrut, inicio, fin, fecha_str = aerorutas.parse_viaje_id(viaje_id)
            puestos = aerorutas.consultar_puestos(inicio, codrut, fecha_str)
        except (ValueError, aerorutas.AerorutasError) as e:
            return JsonResponse({'ok': False, 'msg': f'No se pudo leer el bus: {e}'})
        pisos = aerorutas.pisos_shape(puestos)
        # Cruzar con lo que ya está tomado en NUESTRO sistema (viaje espejo).
        espejo = Viaje.objects.filter(
            aerorutas_codrut=codrut, aerorutas_ofisal=inicio,
            aerorutas_ofides=fin, fecha_salida=fecha_str,
        ).first()
        if espejo:
            _overlay_bloqueos_aerorutas(pisos, espejo, request.user)
        return JsonResponse({'ok': True, 'pisos': pisos})

    try:
        viaje = Viaje.objects.select_related('autobus').get(pk=int(viaje_id))
    except (Viaje.DoesNotExist, ValueError):
        return JsonResponse({'ok': False, 'msg': 'El viaje no existe.'})
    return JsonResponse({'ok': True, 'pisos': generar_mapa_desde_layout(viaje, request.user)})


def _enviar_ticket_al_cliente(reservas, email, nombre):
    """Manda el ticket al correo del cliente (opcional en caja).

    confirmar_grupo_pago ya envía el ticket al dueño de la reserva — que aquí
    es la cajera —, así que si el cliente dio su correo se le envía aparte con
    un objeto mínimo que expone lo que usa la plantilla del email.
    """
    from types import SimpleNamespace
    from reservas.services import enviar_email_ticket

    primera = reservas.select_related('viaje__ruta', 'viaje__autobus').first()
    if not primera:
        return
    destinatario = SimpleNamespace(
        email=email,
        username=nombre or email,
        get_full_name=lambda: nombre or '',
    )
    enviar_email_ticket(reservas, primera.viaje, ConfiguracionGeneral.load(),
                        destinatario, '')


@transaction.atomic
def _accion_vender(request):
    """Cobra en taquilla: aparta, reserva, confirma y registra el pago."""
    viaje_id = (request.POST.get('viaje_id') or '').strip()
    nombre = (request.POST.get('cliente_nombre') or '').strip()
    cedula = (request.POST.get('cliente_cedula') or '').strip()
    telefono = (request.POST.get('cliente_telefono') or '').strip()
    email = (request.POST.get('cliente_email') or '').strip()
    referencia = (request.POST.get('referencia') or '').strip()
    nota = (request.POST.get('nota') or '').strip()
    moneda = (request.POST.get('moneda') or 'BS').upper()

    try:
        asientos = json.loads(request.POST.get('asientos') or '[]')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'msg': 'Selección de asientos inválida.'})

    if not viaje_id:
        return JsonResponse({'ok': False, 'msg': 'Elige el viaje.'})
    if not asientos:
        return JsonResponse({'ok': False, 'msg': 'Elige al menos un puesto.'})
    if not nombre:
        return JsonResponse({'ok': False, 'msg': 'El nombre del cliente es obligatorio.'})
    if moneda not in ('BS', 'USD'):
        return JsonResponse({'ok': False, 'msg': 'Moneda inválida.'})

    metodo = MetodoPago.objects.filter(
        pk=request.POST.get('metodo_pago'), activo=True, disponible_caja=True).first()
    if not metodo:
        return JsonResponse({'ok': False, 'msg': 'Elige un método de pago habilitado para caja.'})

    try:
        monto = _dec(request.POST.get('monto'), 'Monto')
    except ValueError as e:
        return JsonResponse({'ok': False, 'msg': str(e)})
    if monto <= 0:
        return JsonResponse({'ok': False, 'msg': 'El monto debe ser mayor que cero.'})

    numeros = []
    for a in asientos:
        try:
            numeros.append(int(a.get('numero')))
        except (TypeError, ValueError, AttributeError):
            return JsonResponse({'ok': False, 'msg': 'Número de asiento inválido.'})

    # ── Resolver el viaje (y apartar en Aerorutas si aplica) ──
    if _es_aerorutas(viaje_id):
        try:
            codrut, inicio, fin, fecha_str = aerorutas.parse_viaje_id(viaje_id)
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'ok': False, 'msg': 'ID de viaje inválido.'})
        if fecha < timezone.localdate():
            return JsonResponse({'ok': False, 'msg': 'Ese viaje ya pasó.'})

        try:
            libres = set()
            for p in aerorutas.consultar_puestos(inicio, codrut, fecha_str):
                try:
                    libres.add(int(p.get('puesto')))
                except (TypeError, ValueError):
                    continue
            ocupados = [n for n in numeros if n not in libres]
            if ocupados:
                return JsonResponse({'ok': False, 'msg':
                    f"El/los puesto(s) {', '.join(map(str, ocupados))} ya no está(n) libre(s)."})

            rutas = aerorutas.consultar_rutas(inicio, fin, fecha_str)
            ruta_ext = next((r for r in rutas if str(r.get('codrut')) == str(codrut)), None)
            if ruta_ext is None:
                return JsonResponse({'ok': False, 'msg': 'El viaje ya no está disponible en Aerorutas.'})
            info = aerorutas.viaje_shape(ruta_ext, inicio, fin, fecha_str, None)

            # Apartar cada puesto allá antes de cobrarlo acá.
            for n in numeros:
                aerorutas.apartar_puesto(fecha_str, codrut, str(n), inicio, fin)
        except aerorutas.AerorutasError as e:
            return JsonResponse({'ok': False, 'msg': f'Aerorutas no respondió: {e}'})

        viaje = obtener_o_crear_viaje_espejo(codrut, inicio, fin, fecha, info)
        piso_fijo = 1
    else:
        try:
            viaje = Viaje.objects.select_related('ruta').get(pk=int(viaje_id), activo=True)
        except (Viaje.DoesNotExist, ValueError):
            return JsonResponse({'ok': False, 'msg': 'El viaje no existe o está inactivo.'})
        if viaje.fecha_salida < timezone.localdate():
            return JsonResponse({'ok': False, 'msg': 'Ese viaje ya pasó.'})
        piso_fijo = None

    # ── Crear las reservas ──
    grupo_pago = uuid_lib.uuid4()
    creadas, errores = [], []
    try:
        Reserva.limpiar_expiradas(viaje=viaje)
        for a in asientos:
            numero = int(a.get('numero'))
            piso = piso_fijo or int(a.get('piso') or 1)
            tomado = Reserva.objects.select_for_update().filter(
                viaje=viaje, numero_asiento=numero, piso_asiento=piso,
                estado__in=['pendiente', 'apartado', 'confirmado'],
            ).exists()
            if tomado:
                errores.append(f'Puesto {numero} ya estaba reservado.')
                continue
            creadas.append(Reserva.objects.create(
                usuario=request.user,          # la cajera es la titular del registro
                viaje=viaje,
                numero_asiento=numero,
                piso_asiento=piso,
                nombre_pasajero=nombre,
                cedula_pasajero=cedula,
                estado='pendiente',            # confirmar_grupo_pago lo pasa a confirmado
                grupo_pago=grupo_pago,
            ))
        if not creadas:
            raise IntegrityError('Sin asientos disponibles')
    except IntegrityError:
        return JsonResponse({'ok': False,
                             'msg': 'No se pudo reservar ningún puesto.',
                             'detalles': errores})

    # ── Confirmar (genera ticket, avisa por WebSocket y marca ASIGPASA) ──
    reservas = confirmar_grupo_pago(grupo_pago)

    # ── Registrar el cobro para el arqueo ──
    tasa = _tasa()
    monto_usd = sum((r.viaje.precio_usd for r in reservas), Decimal('0'))
    PagoCaja.objects.create(
        grupo_pago=grupo_pago,
        cajero=request.user,
        metodo_pago=metodo,
        moneda=moneda,
        monto=monto,
        monto_usd=monto_usd,
        tasa_bcv=tasa,
        referencia=referencia,
        cliente_nombre=nombre,
        cliente_cedula=cedula,
        cliente_telefono=telefono,
        nota=nota,
    )

    if email:
        try:
            _enviar_ticket_al_cliente(reservas, email, nombre)
        except Exception as e:  # el correo no debe tumbar una venta ya cobrada
            print(f'[CAJA] No se pudo enviar el ticket a {email}: {e}')

    return JsonResponse({
        'ok': True,
        'grupo_pago': str(grupo_pago),
        'tickets': [{'codigo': r.codigo_ticket, 'asiento': r.numero_asiento}
                    for r in reservas],
        'monto_usd': str(monto_usd),
        'avisos': errores,
    })


# ══════════════════════════════════════════════════════════════════
#  Vista principal
# ══════════════════════════════════════════════════════════════════

ACCIONES = {
    'catalogo': _accion_catalogo,
    'buscar': _accion_buscar,
    'asientos': _accion_asientos,
    'vender': _accion_vender,
}


@staff_requerido
def caja_view(request):
    """Punto de venta de taquilla dentro del back office."""
    if request.method == 'POST':
        handler = ACCIONES.get(request.POST.get('accion'))
        if handler is None:
            return JsonResponse({'ok': False, 'msg': 'Acción desconocida.'})
        try:
            return handler(request)
        except Exception as e:  # nunca dejar la caja con un 500 sin explicación
            import traceback
            traceback.print_exc()
            return JsonResponse({'ok': False, 'msg': f'Error inesperado: {e}'})

    try:
        oficinas = aerorutas.consultar_oficinas_cacheado()
    except aerorutas.AerorutasError:
        oficinas = []

    return render(request, 'backoffice/caja.html', {
        'seccion': 'caja',
        'titulo': 'Caja — venta en taquilla',
        'subtitulo': 'Cobra en el mostrador y emite el boleto en el acto',
        'oficinas': sorted(oficinas, key=lambda o: str(o.get('desofi') or '')),
        'metodos': MetodoPago.objects.filter(activo=True, disponible_caja=True),
        'tasa_bcv': _tasa(),
        'hoy': timezone.localdate().isoformat(),
    })
