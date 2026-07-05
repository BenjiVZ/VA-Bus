from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.authentication import SessionAuthentication
from django.shortcuts import render
from django.contrib.auth.views import redirect_to_login
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import Q, Count, Subquery, OuterRef, IntegerField, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from .models import Ruta, Viaje, Autobus, ConfiguracionGeneral, Oficina, RutaAerorutasSnapshot
from .serializers import (
    RutaSerializer, ViajeListSerializer, ViajeDetailSerializer,
    ConfiguracionSerializer, OficinaSerializer,
)
from .services import actualizar_tasa_bcv


class ViajePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class RutaListView(generics.ListAPIView):
    queryset = Ruta.objects.all()
    serializer_class = RutaSerializer
    permission_classes = [permissions.AllowAny]


class OficinaListView(generics.ListAPIView):
    """Lista pública de oficinas/sucursales activas."""
    queryset = Oficina.objects.filter(activa=True).order_by('desofi')
    serializer_class = OficinaSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class ViajeListView(generics.ListAPIView):
    serializer_class = ViajeListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = ViajePagination

    def get_queryset(self):
        from reservas.models import Reserva
        # localdate(): fecha en hora de Venezuela (settings.TIME_ZONE). Con USE_TZ,
        # timezone.now().date() daría la fecha en UTC y ocultaría/incluiría viajes
        # del día equivocado según la hora.
        hoy = timezone.localdate()

        # 1) Limpiar expiradas una sola vez (no por viaje)
        Reserva.limpiar_expiradas()

        # 2) Subquery: contar reservas activas por viaje
        reservas_count = Reserva.objects.filter(
            viaje=OuterRef('pk'),
            estado__in=['pendiente', 'apartado', 'confirmado']
        ).order_by().values('viaje').annotate(cnt=Count('pk')).values('cnt')

        # 3) Subquery: capacidad total del autobus (sum de capacidad de cada piso)
        #    Capacidad se calcula desde el layout JSON, pero podemos aproximar
        #    usando pisos_config. Prefetch pisos_config instead.
        from viajes.models import PisoAutobus

        queryset = Viaje.objects.filter(
            activo=True,
            fecha_salida__gte=hoy,
        ).select_related(
            'ruta', 'autobus'
        ).prefetch_related(
            'autobus__pisos_config'
        ).annotate(
            _reservas_activas_count=Coalesce(
                Subquery(reservas_count, output_field=IntegerField()),
                0
            )
        )

        # Filter by sales window
        queryset = queryset.filter(
            Q(fecha_inicio_venta__isnull=True) | Q(fecha_inicio_venta__lte=hoy)
        ).filter(
            Q(fecha_fin_venta__isnull=True) | Q(fecha_fin_venta__gte=hoy)
        )

        origen = self.request.query_params.get('origen')
        destino = self.request.query_params.get('destino')
        fecha = self.request.query_params.get('fecha')

        if origen:
            queryset = queryset.filter(ruta__origen__icontains=origen)
        if destino:
            queryset = queryset.filter(ruta__destino__icontains=destino)
        if fecha:
            queryset = queryset.filter(fecha_salida=fecha)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Paginate first
        page = self.paginate_queryset(queryset)
        viajes = page if page is not None else list(queryset)

        # Pre-compute capacidad_total per autobus (avoid N queries)
        autobus_cache = {}
        for viaje in viajes:
            bus_id = viaje.autobus_id
            if bus_id not in autobus_cache:
                autobus_cache[bus_id] = viaje.autobus.capacidad_total
            viaje._asientos_disponibles = autobus_cache[bus_id] - viaje._reservas_activas_count

        serializer = self.get_serializer(viajes, many=True)

        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class ViajeDetailView(generics.RetrieveAPIView):
    queryset = Viaje.objects.filter(activo=True).select_related('ruta', 'autobus').prefetch_related('autobus__pisos_config')
    serializer_class = ViajeDetailSerializer
    permission_classes = [permissions.AllowAny]


def generar_mapa_desde_layout(viaje, user=None):
    """Lee el layout JSON de cada piso y cruza con las reservas activas."""
    from reservas.models import Reserva, BloqueoAsiento

    # Limpiar reservas expiradas antes de consultar disponibilidad
    Reserva.limpiar_expiradas(viaje=viaje)
    BloqueoAsiento.limpiar_expirados(viaje=viaje)

    reservas_activas = Reserva.objects.filter(
        viaje=viaje,
        estado__in=['pendiente', 'apartado', 'confirmado']
    ).values_list('numero_asiento', 'piso_asiento', flat=False)

    now = timezone.now()
    bloqueos_activos = BloqueoAsiento.objects.filter(
        viaje=viaje,
        fecha_expiracion__gt=now,
    ).values_list('numero_asiento', 'piso_asiento', 'usuario_id')

    asientos_ocupados = set()
    for numero, piso in reservas_activas:
        asientos_ocupados.add((piso, numero))

    user_id = user.id if user and user.is_authenticated else None
    asientos_bloqueados_mios = set()
    for numero, piso, bloqueo_user_id in bloqueos_activos:
        asiento_key = (piso, numero)
        if user_id and bloqueo_user_id == user_id:
            asientos_bloqueados_mios.add(asiento_key)
            continue
        asientos_ocupados.add(asiento_key)

    resultado = []

    for piso_config in viaje.autobus.pisos_config.all().order_by('numero_piso'):
        piso_num = piso_config.numero_piso
        layout = piso_config.layout or []

        # Build layout with availability info
        layout_con_disponibilidad = []
        for row in layout:
            fila_result = []
            for cell in row:
                cell_copy = dict(cell) if isinstance(cell, dict) else {'type': 'empty'}
                if cell_copy.get('type') == 'seat' and cell_copy.get('number'):
                    num = cell_copy['number']
                    seat_key = (piso_num, num)
                    cell_copy['disponible'] = seat_key not in asientos_ocupados
                    if user_id:
                        cell_copy['bloqueado_por_mi'] = seat_key in asientos_bloqueados_mios
                fila_result.append(cell_copy)
            layout_con_disponibilidad.append(fila_result)

        resultado.append({
            'numero_piso': piso_num,
            'filas': piso_config.filas,
            'columnas': piso_config.columnas,
            'layout': layout_con_disponibilidad,
            'capacidad': piso_config.capacidad,
        })

    return resultado


class ViajeAsientosView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            viaje = Viaje.objects.select_related('autobus').prefetch_related(
                'autobus__pisos_config'
            ).get(pk=pk, activo=True)
        except Viaje.DoesNotExist:
            return Response({"error": "Viaje no encontrado."}, status=404)

        pisos_data = generar_mapa_desde_layout(viaje, request.user)

        return Response({
            'viaje': ViajeDetailSerializer(viaje).data,
            'pisos_config': pisos_data,
        })


class TasaCambioView(APIView):
    """
    Endpoint para obtener la tasa de cambio.
    - Cache en memoria de 5 min para respuesta instantánea.
    - Si necesita actualizar, lo hace en background (no bloquea).
    """
    permission_classes = [permissions.AllowAny]
    _cache = {'data': None, 'timestamp': 0}
    _updating = False

    def get(self, request):
        import time as _time
        import threading
        now = _time.time()

        # Cache en memoria: responde instantáneo si <5 min
        if self._cache['data'] and (now - self._cache['timestamp']) < 300:
            return Response(self._cache['data'])

        config = ConfiguracionGeneral.load()

        # Construir respuesta con el valor actual de la DB (inmediato)
        fuente = 'automatica' if config.tasa_actualizada else 'manual'
        response_data = {
            'tasa_bcv': float(config.tasa_bcv) if config.tasa_bcv else 0,
            'actualizada': config.tasa_actualizada,
            'fuente': 've.dolarapi.com - BCV Oficial',
            'fuente_tipo': fuente,
        }

        # Guardar en cache inmediatamente con lo que hay en DB
        self.__class__._cache = {
            'data': response_data,
            'timestamp': now,
        }

        # Determinar si necesita actualizar desde la API externa
        should_update = False
        if not config.tasa_bcv or config.tasa_bcv == 0:
            should_update = True
        elif config.tasa_actualizada:
            from datetime import timedelta
            age = timezone.now() - config.tasa_actualizada
            if age > timedelta(hours=6):
                should_update = True
        else:
            should_update = True

        # Actualizar en background si es necesario (no bloquea la respuesta)
        if should_update and not self.__class__._updating:
            def _update_bg():
                try:
                    self.__class__._updating = True
                    import django
                    django.db.connections.close_all()
                    exito, _ = actualizar_tasa_bcv()
                    if exito:
                        cfg = ConfiguracionGeneral.load()
                        self.__class__._cache = {
                            'data': {
                                'tasa_bcv': float(cfg.tasa_bcv),
                                'actualizada': cfg.tasa_actualizada,
                                'fuente': 've.dolarapi.com - BCV Oficial',
                                'fuente_tipo': 'automatica',
                            },
                            'timestamp': _time.time(),
                        }
                finally:
                    self.__class__._updating = False

            threading.Thread(target=_update_bg, daemon=True).start()

        return Response(response_data)


class ConfiguracionPublicaView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        config = ConfiguracionGeneral.load()
        serializer = ConfiguracionSerializer(config)
        return Response(serializer.data)


# ────────────────────────────────────────────────
#  Portal de Viajes (custom admin view)
# ────────────────────────────────────────────────
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime, timedelta, date as date_type


@staff_member_required
def portal_viajes_view(request):
    """Portal cómodo para crear viajes desde el admin."""

    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            ruta_id = request.POST.get('ruta')
            autobus_id = request.POST.get('autobus')
            tipo_viaje = request.POST.get('tipo_viaje', 'ida')
            hora_salida = request.POST.get('hora_salida')
            precio_usd = request.POST.get('precio_usd')
            activo = request.POST.get('activo') == 'on'

            if not all([ruta_id, autobus_id, hora_salida, precio_usd]):
                return JsonResponse({'ok': False, 'msg': 'Todos los campos son obligatorios.'})

            ruta = Ruta.objects.get(pk=ruta_id)
            autobus = Autobus.objects.get(pk=autobus_id)

            # ── Batch mode ──
            is_batch = request.POST.get('batch') == '1'
            if is_batch:
                batch_desde = request.POST.get('batch_desde')
                batch_hasta = request.POST.get('batch_hasta')
                batch_dias = json.loads(request.POST.get('batch_dias', '[]'))

                if not batch_desde or not batch_hasta:
                    return JsonResponse({'ok': False, 'msg': 'Selecciona las fechas del lote.'})

                fecha_desde = datetime.strptime(batch_desde, '%Y-%m-%d').date()
                fecha_hasta = datetime.strptime(batch_hasta, '%Y-%m-%d').date()

                if fecha_hasta < fecha_desde:
                    return JsonResponse({'ok': False, 'msg': 'La fecha "Hasta" debe ser posterior a "Desde".'})

                hora = datetime.strptime(hora_salida, '%H:%M').time()

                created = 0
                skipped = 0
                current = fecha_desde
                while current <= fecha_hasta:
                    # weekday(): 0=Monday ... 6=Sunday
                    if current.weekday() in batch_dias:
                        # Check if same trip already exists
                        exists = Viaje.objects.filter(
                            ruta=ruta, autobus=autobus,
                            fecha_salida=current, hora_salida=hora
                        ).exists()
                        if not exists:
                            Viaje.objects.create(
                                ruta=ruta, autobus=autobus,
                                tipo_viaje=tipo_viaje,
                                fecha_salida=current,
                                hora_salida=hora,
                                precio_usd=precio_usd,
                                activo=activo,
                            )
                            created += 1
                        else:
                            skipped += 1
                    current += timedelta(days=1)

                msg = f'Se crearon {created} viajes en lote.'
                if skipped:
                    msg += f' ({skipped} ya existian y fueron omitidos.)'
                return JsonResponse({'ok': True, 'msg': msg})

            # ── Single mode ──
            fecha_salida = request.POST.get('fecha_salida')
            if not fecha_salida:
                return JsonResponse({'ok': False, 'msg': 'La fecha de salida es obligatoria.'})

            hora = datetime.strptime(hora_salida, '%H:%M').time()
            fecha = datetime.strptime(fecha_salida, '%Y-%m-%d').date()

            # Check duplicate
            exists = Viaje.objects.filter(
                ruta=ruta, autobus=autobus,
                fecha_salida=fecha, hora_salida=hora
            ).exists()
            if exists:
                return JsonResponse({'ok': False, 'msg': 'Ya existe un viaje con la misma ruta, autobus, fecha y hora.'})

            viaje_data = {
                'ruta': ruta,
                'autobus': autobus,
                'tipo_viaje': tipo_viaje,
                'fecha_salida': fecha,
                'hora_salida': hora,
                'precio_usd': precio_usd,
                'activo': activo,
            }

            # Vuelta fields
            if tipo_viaje == 'ida_vuelta':
                fv = request.POST.get('fecha_vuelta')
                hv = request.POST.get('hora_vuelta')
                if fv:
                    viaje_data['fecha_vuelta'] = datetime.strptime(fv, '%Y-%m-%d').date()
                if hv:
                    viaje_data['hora_vuelta'] = datetime.strptime(hv, '%H:%M').time()

            viaje = Viaje.objects.create(**viaje_data)
            return JsonResponse({
                'ok': True,
                'msg': f'Viaje #{viaje.id} creado: {ruta} — {fecha_salida} {hora_salida} — ${precio_usd}'
            })

        except Ruta.DoesNotExist:
            return JsonResponse({'ok': False, 'msg': 'La ruta seleccionada no existe.'})
        except Autobus.DoesNotExist:
            return JsonResponse({'ok': False, 'msg': 'El autobus seleccionado no existe.'})
        except Exception as e:
            return JsonResponse({'ok': False, 'msg': f'Error: {str(e)}'})

    # ── GET: Render form ──
    context = {
        'rutas': Ruta.objects.all().order_by('origen', 'destino'),
        'autobuses': Autobus.objects.all().order_by('nombre'),
        'recientes': Viaje.objects.select_related('ruta', 'autobus').order_by('-id')[:15],
        'title': 'Portal de Viajes',
    }
    return render(request, 'admin/portal_viajes.html', context)


@staff_member_required
@require_http_methods(["DELETE"])
def eliminar_viaje_view(request, viaje_id):
    """Eliminar un viaje desde el portal de admin."""
    try:
        viaje = Viaje.objects.get(pk=viaje_id)

        # Verificar si tiene reservas activas
        from reservas.models import Reserva
        reservas_activas = Reserva.objects.filter(
            viaje=viaje,
            estado__in=['pendiente', 'confirmado', 'apartado']
        ).count()

        if reservas_activas > 0:
            return JsonResponse({
                'ok': False,
                'msg': f'No se puede eliminar: el viaje tiene {reservas_activas} reserva(s) activa(s). Cancélalas primero.'
            })

        viaje_info = f"#{viaje.id} — {viaje.ruta} — {viaje.fecha_salida}"
        viaje.delete()
        return JsonResponse({
            'ok': True,
            'msg': f'Viaje {viaje_info} eliminado correctamente.'
        })

    except Viaje.DoesNotExist:
        return JsonResponse({'ok': False, 'msg': 'El viaje no existe.'})
    except Exception as e:
        return JsonResponse({'ok': False, 'msg': f'Error: {str(e)}'})


class StatsPublicView(APIView):
    """Public endpoint returning homepage stats from DB."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from reservas.models import Reserva

        # Datos reales del catálogo de Aerorutas precargado para hoy.
        # localdate() = fecha en hora de Venezuela, no el reloj del SO/UTC.
        snap = RutaAerorutasSnapshot.objects.filter(fecha=timezone.localdate()).first()
        viajes = snap.data if (snap and snap.data) else []
        # Rutas nacionales = corredores distintos (origen → destino) de hoy.
        total_rutas = len({
            (v.get('ruta', {}).get('origen'), v.get('ruta', {}).get('destino'))
            for v in viajes
        })
        # Autobuses operativos = líneas/buses distintos en circulación hoy.
        total_buses = len({
            v.get('autobus', {}).get('nombre')
            for v in viajes if v.get('autobus', {}).get('nombre')
        })
        # Si aún no hay catálogo cargado, caer a las tablas locales.
        if not total_rutas:
            total_rutas = Ruta.objects.count()
        if not total_buses:
            total_buses = Autobus.objects.filter(disponible=True).count()

        total_pasajeros = Reserva.objects.filter(
            estado__in=['confirmado', 'completado']
        ).count()

        return Response({
            'rutas': total_rutas,
            'buses': total_buses,
            'pasajeros': total_pasajeros,
        })


# ────────────────────────────────────────────────
#  Integración Aerorutas (sistema de control externo)
#  Consulta en vivo de oficinas / rutas / puestos.
# ────────────────────────────────────────────────
from . import aerorutas


class AerorutasOficinasView(APIView):
    """Oficinas en vivo desde Aerorutas (las sincronizadas están en /oficinas/)."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Cacheado (1h): las oficinas son estables; evita llamar al banco en cada apertura.
        return Response(aerorutas.consultar_oficinas_cacheado())


class AerorutasRutasView(APIView):
    """Rutas disponibles entre dos oficinas en una fecha. Params: inicio, fin, fecha."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        inicio = request.query_params.get('inicio')
        fin = request.query_params.get('fin')
        fecha = request.query_params.get('fecha')
        if not (inicio and fin and fecha):
            return Response({'error': 'Parámetros requeridos: inicio, fin, fecha.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            return Response(aerorutas.consultar_rutas(inicio, fin, fecha))
        except aerorutas.AerorutasError as e:
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class AerorutasPuestosView(APIView):
    """Puestos disponibles de una ruta. Params: codofi, codrut, fecha."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        codofi = request.query_params.get('codofi')
        codrut = request.query_params.get('codrut')
        fecha = request.query_params.get('fecha')
        if not (codofi and codrut and fecha):
            return Response({'error': 'Parámetros requeridos: codofi, codrut, fecha.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            return Response(aerorutas.consultar_puestos(codofi, codrut, fecha))
        except aerorutas.AerorutasError as e:
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class AerorutasViajesView(APIView):
    """
    Búsqueda de viajes de Aerorutas devuelta con el MISMO formato que /viajes/
    (paginación DRF + ViajeListSerializer), para reusar la UI actual.
    Params: inicio, fin (codofi), fecha. (acepta origen/destino como alias)

    Autorecuperación: si piden el catálogo de HOY y no hay snapshot (cron caído,
    droplet recreado, etc.), dispara la precarga en background — mismo patrón
    que TasaCambioView. El sitio se repara solo en unos minutos.
    """
    permission_classes = [permissions.AllowAny]
    _precargando = False

    @classmethod
    def _lanzar_precarga_bg(cls):
        """Corre precargar_rutas en un hilo daemon, con candado anti-estampida."""
        if cls._precargando:
            return
        cls._precargando = True

        def _run():
            try:
                import django
                from django.core.management import call_command
                django.db.connections.close_all()
                call_command('precargar_rutas', dias=1, solo_si_falta=True,
                             intentos=2, espera_red=30)
            except Exception:
                pass  # red caída: el próximo request lo reintenta
            finally:
                cls._precargando = False

        import threading
        threading.Thread(target=_run, daemon=True).start()

    def get(self, request):
        q = request.query_params
        inicio = q.get('inicio') or q.get('origen')
        fin = q.get('fin') or q.get('destino')
        fecha = q.get('fecha')
        if not fecha:
            return Response({'count': 0, 'next': None, 'previous': None, 'results': []})

        try:
            if inicio and fin:
                # Par específico
                rutas = aerorutas.consultar_rutas(inicio, fin, fecha)
                results = []
                for r in rutas:
                    try:
                        disp = len(aerorutas.consultar_puestos(inicio, r.get('codrut', ''), fecha))
                    except aerorutas.AerorutasError:
                        disp = None
                    results.append(aerorutas.viaje_shape(r, inicio, fin, fecha, disp))
            else:
                # Sin origen/destino: servir el catálogo PRECARGADO (instantáneo).
                snap = RutaAerorutasSnapshot.objects.filter(fecha=fecha).first()
                results = snap.data if snap else []
                # Falta el catálogo de HOY → autorecuperación en background.
                if not results and fecha == timezone.localdate().isoformat():
                    self._lanzar_precarga_bg()
        except aerorutas.AerorutasError as e:
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        # Ocultar viajes sin precio (precio 0 o vacío).
        def _precio(v):
            try:
                return float(v.get('precio_usd') or 0)
            except (TypeError, ValueError):
                return 0
        results = [v for v in results if _precio(v) > 0]

        return Response({'count': len(results), 'next': None, 'previous': None,
                         'results': results})


class AerorutasViajeAsientosView(APIView):
    """Asientos de un viaje de Aerorutas con el MISMO formato que /viajes/<id>/asientos/."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, trip_id):
        try:
            codrut, inicio, fin, fecha = aerorutas.parse_viaje_id(trip_id)
        except ValueError:
            return Response({'error': 'ID de viaje inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        # Cabecera (origen/destino/precio/hora) desde el catálogo precargado:
        # es instantáneo y evita una llamada externa. Solo los asientos van en vivo.
        viaje = None
        snap = RutaAerorutasSnapshot.objects.filter(fecha=fecha).first()
        if snap and snap.data:
            viaje = next((v for v in snap.data if v.get('id') == trip_id), None)

        try:
            puestos = aerorutas.consultar_puestos(inicio, codrut, fecha)
        except aerorutas.AerorutasError as e:
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        if viaje is None:
            # Fallback: no está precargado (link directo / snapshot ausente) → en vivo.
            try:
                rutas = aerorutas.consultar_rutas(inicio, fin, fecha)
            except aerorutas.AerorutasError as e:
                return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)
            ruta = next((r for r in rutas if str(r.get('codrut')) == str(codrut)), {})
            viaje = aerorutas.viaje_shape(ruta, inicio, fin, fecha, len(puestos))
        else:
            # Refrescar el conteo de disponibles con el dato en vivo.
            viaje = {**viaje, 'asientos_disponibles': len(puestos)}

        return Response({
            'viaje': viaje,
            'pisos_config': aerorutas.pisos_shape(puestos),
        })


class AerorutasApartarView(APIView):
    """Aparta un puesto temporalmente (TMPPUESTO). MUTA estado en Aerorutas."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        d = request.data
        requeridos = ['fecha', 'codrut', 'nroasi', 'ofisal', 'ofides']
        faltan = [k for k in requeridos if not d.get(k)]
        if faltan:
            return Response({'error': f'Faltan parámetros: {", ".join(faltan)}'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            items, raw = aerorutas.apartar_puesto(
                d['fecha'], d['codrut'], d['nroasi'], d['ofisal'], d['ofides'])
        except aerorutas.AerorutasError as e:
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'items': items, 'raw': raw})


class _IsSuperuser(permissions.BasePermission):
    """Solo superusuarios autenticados."""
    message = 'Solo superusuarios.'

    def has_permission(self, request, view):
        u = getattr(request, 'user', None)
        return bool(u and u.is_authenticated and u.is_superuser)


class AerorutasAsignarView(APIView):
    """
    Marca un puesto como VENDIDO POR WEB en Aerorutas (ASIGPASA).

    Se invoca al aprobarse el pago de una reserva de Aerorutas para sincronizar la
    venta con el sistema de control externo. Por ahora restringido a superusuarios
    (sesión del admin) para poder hacer QA del endpoint; el flujo de compra de
    viajes Aerorutas lo llamará automáticamente cuando esté armado.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [_IsSuperuser]

    def post(self, request):
        d = request.data
        requeridos = ['fecha', 'codrut', 'nroasi', 'ofisal', 'ofides']
        faltan = [k for k in requeridos if not d.get(k)]
        if faltan:
            return Response({'ok': False, 'error': f'Faltan parámetros: {", ".join(faltan)}'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            items, raw = aerorutas.asignar_pasaje(
                d['fecha'], d['codrut'], d['nroasi'], d['ofisal'], d['ofides'])
        except aerorutas.AerorutasError as e:
            return Response({'ok': False, 'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'ok': True, 'items': items, 'raw': raw})


@ensure_csrf_cookie
def aerorutas_asignar_test_page(request):
    """Página de QA (solo superusuario) para probar ASIGPASA contra Aerorutas."""
    u = request.user
    if not (u.is_authenticated and u.is_superuser):
        return redirect_to_login(request.get_full_path(), '/admin/login/')
    return render(request, 'viajes/asignar_test.html')
