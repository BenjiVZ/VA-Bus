from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from .models import Ruta, Viaje, Autobus, ConfiguracionGeneral
from .serializers import (
    RutaSerializer, ViajeListSerializer,
    ConfiguracionSerializer
)
from .services import actualizar_tasa_bcv


class RutaListView(generics.ListAPIView):
    queryset = Ruta.objects.all()
    serializer_class = RutaSerializer
    permission_classes = [permissions.AllowAny]


class ViajeListView(generics.ListAPIView):
    serializer_class = ViajeListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        from django.utils import timezone
        from django.db.models import Q
        hoy = timezone.now().date()

        queryset = Viaje.objects.filter(
            activo=True,
            fecha_salida__gte=hoy,
        ).select_related('ruta', 'autobus')

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


class ViajeDetailView(generics.RetrieveAPIView):
    queryset = Viaje.objects.filter(activo=True).select_related('ruta', 'autobus')
    serializer_class = ViajeListSerializer
    permission_classes = [permissions.AllowAny]


def generar_mapa_desde_layout(viaje):
    """Lee el layout JSON de cada piso y cruza con las reservas activas."""
    from reservas.models import Reserva

    # Limpiar reservas expiradas antes de consultar disponibilidad
    Reserva.limpiar_expiradas(viaje=viaje)

    reservas_activas = Reserva.objects.filter(
        viaje=viaje,
        estado__in=['pendiente', 'apartado', 'confirmado']
    ).values_list('numero_asiento', 'piso_asiento', flat=False)

    asientos_ocupados = set()
    for numero, piso in reservas_activas:
        asientos_ocupados.add((piso, numero))

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
                    cell_copy['disponible'] = (piso_num, num) not in asientos_ocupados
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

        pisos_data = generar_mapa_desde_layout(viaje)

        return Response({
            'viaje': ViajeListSerializer(viaje).data,
            'pisos_config': pisos_data,
        })


class TasaCambioView(APIView):
    """
    Endpoint para obtener la tasa de cambio.
    - El frontend SOLO consulta este endpoint del backend.
    - El backend consulta la API externa (ve.dolarapi.com).
    - Si la API externa falla, se usa el valor manual del admin.
    - Cache en memoria de 60s para evitar sobrecarga.
    """
    permission_classes = [permissions.AllowAny]
    _cache = {'tasa': None, 'data': None, 'timestamp': 0}

    def get(self, request):
        import time as _time
        now = _time.time()

        # Cache en memoria: responde instantáneo si <60s
        if self._cache['data'] and (now - self._cache['timestamp']) < 60:
            return Response(self._cache['data'])

        config = ConfiguracionGeneral.load()

        # Determinar si necesita actualizar desde la API externa
        should_update = False
        if not config.tasa_bcv or config.tasa_bcv == 0:
            should_update = True
        elif config.tasa_actualizada:
            from django.utils import timezone
            from datetime import timedelta
            age = timezone.now() - config.tasa_actualizada
            if age > timedelta(hours=6):
                should_update = True
        else:
            should_update = True

        if should_update:
            exito, mensaje = actualizar_tasa_bcv()
            if exito:
                config.refresh_from_db()

        fuente = 'automatica' if config.tasa_actualizada else 'manual'
        response_data = {
            'tasa_bcv': float(config.tasa_bcv),
            'actualizada': config.tasa_actualizada,
            'fuente': 've.dolarapi.com - BCV Oficial',
            'fuente_tipo': fuente,
        }

        # Guardar en cache
        self.__class__._cache = {
            'data': response_data,
            'timestamp': now,
        }

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

