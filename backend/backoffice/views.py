"""Pantallas propias del back office (`/panel/`).

Nada de esto usa el admin de Django: son vistas normales con plantillas
propias. El admin queda disponible aparte, para tocar datos crudos.
"""
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date

from pagos.models import ComprobantePago, MetodoPago, PagoCaja
from pagos.services import validar_comprobante
from r4conecta.models import OperacionDebitoOTP
from reservas.models import Reserva
from viajes import agenda_precarga
from viajes.models import ConfiguracionGeneral, Viaje

from . import rutas as rutas_svc
from .auth import staff_requerido

# Cuántas filas por página en los listados.
POR_PAGINA = 25


def _destino_seguro(request):
    """Evita redirigir fuera del sitio con ?next=."""
    destino = request.POST.get('next') or request.GET.get('next') or ''
    if destino.startswith('/') and not destino.startswith('//'):
        return destino
    return reverse('backoffice:inicio')


# ══════════════════════════════════════════════════════════════════
#  Ingreso
# ══════════════════════════════════════════════════════════════════

def ingresar(request):
    """Login propio del back office. Solo entra personal (`is_staff`)."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect(_destino_seguro(request))

    error = ''
    if request.method == 'POST':
        usuario = authenticate(
            request,
            username=(request.POST.get('usuario') or '').strip(),
            password=request.POST.get('clave') or '',
        )
        if usuario is None:
            error = 'Usuario o contraseña incorrectos.'
        elif not usuario.is_active:
            error = 'Esta cuenta está desactivada.'
        elif not usuario.is_staff:
            error = 'Esta cuenta no tiene acceso al back office.'
        else:
            login(request, usuario)
            return redirect(_destino_seguro(request))

    return render(request, 'backoffice/ingresar.html', {
        'error': error,
        'next': request.GET.get('next', ''),
    })


def salir(request):
    logout(request)
    return redirect('backoffice:ingresar')


# ══════════════════════════════════════════════════════════════════
#  Inicio
# ══════════════════════════════════════════════════════════════════

@staff_requerido
def inicio(request):
    hoy = timezone.localdate()
    ahora = timezone.now()

    # Las pendientes vencidas se cancelan solas; así los números son reales.
    Reserva.limpiar_expiradas()

    caja_hoy = PagoCaja.objects.filter(fecha_creacion__date=hoy)
    boletos_hoy = Reserva.objects.filter(estado='confirmado', fecha_actualizacion__date=hoy)

    config = ConfiguracionGeneral.load()

    return render(request, 'backoffice/inicio.html', {
        'seccion': 'inicio',
        'titulo': 'Inicio',
        'subtitulo': f'Resumen del {hoy.strftime("%d/%m/%Y")}',

        'caja_hoy_n': caja_hoy.count(),
        'caja_hoy_usd': caja_hoy.aggregate(t=Sum('monto_usd'))['t'] or 0,
        'boletos_hoy': boletos_hoy.count(),
        'comprobantes_pend': ComprobantePago.objects.filter(estado='pendiente').count(),
        'r4_espera': OperacionDebitoOTP.objects.filter(
            estado__in=['en_espera', 'procesando', 'otp_generado']).count(),
        'reservas_pend': Reserva.objects.filter(
            estado__in=['pendiente', 'apartado']).count(),

        'viajes_hoy': (Viaje.objects
                       .filter(activo=True, fecha_salida=hoy)
                       .select_related('ruta', 'autobus')
                       .order_by('hora_salida')[:8]),
        'ultimas_ventas': (PagoCaja.objects
                           .select_related('metodo_pago', 'cajero')
                           .order_by('-fecha_creacion')[:8]),
        'tasa_actualizada': config.tasa_actualizada if config else None,
        'tasa_vieja': bool(
            config and config.tasa_actualizada
            and config.tasa_actualizada < ahora - timedelta(days=1)
        ),
    })


# ══════════════════════════════════════════════════════════════════
#  Rutas y salidas (qué se publica y qué no)
# ══════════════════════════════════════════════════════════════════

@staff_requerido
def rutas(request):
    hoy = timezone.localdate()
    # La fecha llega por la URL: si viene mal (enlace viejo, alguien la escribió
    # a mano), la consulta reventaba con un 500. Se avisa y se sigue con hoy.
    pedida = (request.GET.get('fecha') or '').strip()
    fecha_obj = parse_date(pedida) if pedida else None
    if pedida and fecha_obj is None:
        messages.error(request, f'«{pedida}» no es una fecha válida; se muestra el día de hoy.')
    fecha = (fecha_obj or hoy).isoformat()

    origen = (request.GET.get('origen') or '').strip()
    destino = (request.GET.get('destino') or '').strip()
    filtro = request.GET.get('filtro') or ''

    datos = rutas_svc.analizar(fecha, origen=origen, destino=destino, filtro=filtro)
    r = datos['resumen']

    proximo_cuando, proximo_modo = agenda_precarga.proximo()
    permitido, motivo = agenda_precarga.estado_manual()

    return render(request, 'backoffice/rutas.html', {
        'seccion': 'rutas',
        'titulo': 'Rutas y salidas',
        'subtitulo': f'{r["total"]} salida(s) para el {fecha} · '
                     f'{r["visibles"]} en la página, {r["ocultas"]} ocultas',
        'd': datos,
        'f': {'fecha': fecha, 'origen': origen, 'destino': destino, 'filtro': filtro},
        'agenda': {
            'filas': agenda_precarga.agenda(),
            'proximo_hora': proximo_cuando and timezone.localtime(proximo_cuando).strftime('%H:%M'),
            'proximo_etiqueta': proximo_modo and agenda_precarga.MODOS[proximo_modo]['etiqueta'],
            'modos': agenda_precarga.MODOS,
            'permitido': permitido,
            'motivo': motivo,
            'en_curso': agenda_precarga.en_curso(),
            'min_antes': agenda_precarga.MIN_ANTES,
            'crontab': agenda_precarga.lineas_crontab(),
        },
    })


@staff_requerido
def rutas_barrer(request):
    """Dispara a mano un barrido del catálogo. Solo POST desde la pantalla."""
    if request.method != 'POST':
        return redirect('backoffice:rutas')
    arranco, mensaje = agenda_precarga.lanzar(request.POST.get('modo') or '')
    (messages.success if arranco else messages.error)(request, mensaje)
    return redirect(_destino_seguro(request))


# ══════════════════════════════════════════════════════════════════
#  Boletos (reservas)
# ══════════════════════════════════════════════════════════════════

@staff_requerido
def boletos(request):
    Reserva.limpiar_expiradas()

    qs = (Reserva.objects
          .select_related('usuario', 'viaje__ruta', 'viaje__autobus')
          .order_by('-fecha_creacion'))

    estado = request.GET.get('estado', '')
    if estado:
        qs = qs.filter(estado=estado)

    busca = (request.GET.get('q') or '').strip()
    if busca:
        qs = qs.filter(
            Q(codigo_ticket__icontains=busca) |
            Q(nombre_pasajero__icontains=busca) |
            Q(cedula_pasajero__icontains=busca) |
            Q(usuario__username__icontains=busca) |
            Q(usuario__first_name__icontains=busca) |
            Q(usuario__email__icontains=busca)
        )

    desde = request.GET.get('desde', '')
    if desde:
        qs = qs.filter(viaje__fecha_salida__gte=desde)
    hasta = request.GET.get('hasta', '')
    if hasta:
        qs = qs.filter(viaje__fecha_salida__lte=hasta)

    pagina = Paginator(qs, POR_PAGINA).get_page(request.GET.get('p'))

    return render(request, 'backoffice/boletos.html', {
        'seccion': 'boletos',
        'titulo': 'Boletos',
        'subtitulo': f'{pagina.paginator.count} reserva(s) con los filtros actuales',
        'pagina': pagina,
        'estados': Reserva.ESTADO_CHOICES,
        'f': {'estado': estado, 'q': busca, 'desde': desde, 'hasta': hasta},
    })


# ══════════════════════════════════════════════════════════════════
#  Comprobantes (pagos reportados desde la web / app)
# ══════════════════════════════════════════════════════════════════

@staff_requerido
def comprobantes(request):
    if request.method == 'POST':
        comprobante = get_object_or_404(ComprobantePago, pk=request.POST.get('id'))
        decision = request.POST.get('decision')

        if comprobante.estado != 'pendiente':
            messages.error(request, f'Ese comprobante ya estaba {comprobante.get_estado_display()}.')
        elif decision not in ('aprobado', 'rechazado'):
            messages.error(request, 'Decisión no válida.')
        else:
            reservas = validar_comprobante(
                comprobante, decision, request.user, (request.POST.get('nota') or '').strip()
            )
            verbo = 'aprobado' if decision == 'aprobado' else 'rechazado'
            messages.success(
                request,
                f'Comprobante {verbo}: {reservas.count()} puesto(s) '
                f'{"confirmado(s)" if decision == "aprobado" else "liberado(s)"}.'
            )
        return redirect(f'{reverse("backoffice:comprobantes")}?estado={request.POST.get("volver_a", "pendiente")}')

    qs = (ComprobantePago.objects
          .select_related('usuario', 'metodo_pago', 'revisado_por')
          .order_by('-fecha_creacion'))

    estado = request.GET.get('estado', 'pendiente')
    if estado:
        qs = qs.filter(estado=estado)

    busca = (request.GET.get('q') or '').strip()
    if busca:
        qs = qs.filter(
            Q(numero_referencia__icontains=busca) |
            Q(usuario__username__icontains=busca) |
            Q(usuario__first_name__icontains=busca)
        )

    pagina = Paginator(qs, POR_PAGINA).get_page(request.GET.get('p'))

    # Los puestos de cada comprobante, para decidir con el viaje a la vista.
    # Se resuelven de una sola consulta y se cuelgan del objeto: las plantillas
    # de Django no saben leer un diccionario por clave variable.
    grupos = [c.grupo_pago for c in pagina.object_list]
    por_grupo = {}
    for r in (Reserva.objects.filter(grupo_pago__in=grupos)
              .select_related('viaje__ruta').order_by('numero_asiento')):
        por_grupo.setdefault(str(r.grupo_pago), []).append(r)
    for c in pagina.object_list:
        c.reservas_lista = por_grupo.get(str(c.grupo_pago), [])

    return render(request, 'backoffice/comprobantes.html', {
        'seccion': 'comprobantes',
        'titulo': 'Comprobantes',
        'subtitulo': 'Pagos reportados por los clientes desde la web y la app',
        'pagina': pagina,
        'estados': ComprobantePago.ESTADO_CHOICES,
        'f': {'estado': estado, 'q': busca},
    })


# ══════════════════════════════════════════════════════════════════
#  Arqueo de caja
# ══════════════════════════════════════════════════════════════════

@staff_requerido
def arqueo(request):
    hoy = timezone.localdate()
    desde = request.GET.get('desde') or hoy.isoformat()
    hasta = request.GET.get('hasta') or hoy.isoformat()

    qs = (PagoCaja.objects
          .select_related('metodo_pago', 'cajero')
          .filter(fecha_creacion__date__gte=desde, fecha_creacion__date__lte=hasta)
          .order_by('-fecha_creacion'))

    cajero = request.GET.get('cajero', '')
    if cajero:
        qs = qs.filter(cajero_id=cajero)

    metodo = request.GET.get('metodo', '')
    if metodo:
        qs = qs.filter(metodo_pago_id=metodo)

    # Totales por método: es lo que la cajera cuadra al cerrar el turno.
    por_metodo = (qs.values('metodo_pago__nombre', 'moneda')
                    .annotate(n=Count('id'), total=Sum('monto'), total_usd=Sum('monto_usd'))
                    .order_by('metodo_pago__nombre'))

    return render(request, 'backoffice/arqueo.html', {
        'seccion': 'arqueo',
        'titulo': 'Arqueo de caja',
        'subtitulo': f'Ventas de taquilla del {desde} al {hasta}',
        'ventas': qs[:400],
        'total_n': qs.count(),
        'total_usd': qs.aggregate(t=Sum('monto_usd'))['t'] or 0,
        'por_metodo': por_metodo,
        'cajeros': (PagoCaja.objects
                    .exclude(cajero=None)
                    .values('cajero_id', 'cajero__username')
                    .distinct().order_by('cajero__username')),
        'metodos': MetodoPago.objects.filter(disponible_caja=True).order_by('orden', 'nombre'),
        'f': {'desde': desde, 'hasta': hasta, 'cajero': cajero, 'metodo': metodo},
    })
