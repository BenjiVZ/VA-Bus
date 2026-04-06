"""
API Externa — Endpoints para integración con Sistema de Control empresarial.

Autenticación: Header X-API-KEY
Base URL: /api/externo/

Endpoints disponibles:
  GET  /api/externo/viajes/                     → Lista de viajes activos
  GET  /api/externo/viajes/{id}/                → Detalle de un viaje
  GET  /api/externo/viajes/{id}/asientos/       → Mapa de asientos con estado
  GET  /api/externo/viajes/{id}/pasajeros/      → Lista de pasajeros confirmados
  POST /api/externo/viajes/{id}/ocupar-asientos/→ Registrar asientos ocupados externamente
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from django.utils import timezone
from django.db import IntegrityError

from .authentication import APIKeyAuthentication
from viajes.models import Viaje, Ruta, Autobus, PisoAutobus
from reservas.models import Reserva


class ExternoBaseView(APIView):
    """Clase base para todos los endpoints externos."""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'externo'


class ViajesListView(ExternoBaseView):
    """
    GET /api/externo/viajes/
    Lista todos los viajes activos con información básica.

    Query params opcionales:
      - fecha_desde (YYYY-MM-DD): Filtrar desde esta fecha
      - fecha_hasta (YYYY-MM-DD): Filtrar hasta esta fecha
      - ruta_origen (string): Filtrar por origen
      - ruta_destino (string): Filtrar por destino
    """

    def get(self, request):
        viajes = Viaje.objects.filter(activo=True).select_related('ruta', 'autobus')

        # Filtros opcionales
        fecha_desde = request.query_params.get('fecha_desde')
        fecha_hasta = request.query_params.get('fecha_hasta')
        ruta_origen = request.query_params.get('ruta_origen')
        ruta_destino = request.query_params.get('ruta_destino')

        if fecha_desde:
            viajes = viajes.filter(fecha_salida__gte=fecha_desde)
        if fecha_hasta:
            viajes = viajes.filter(fecha_salida__lte=fecha_hasta)
        if ruta_origen:
            viajes = viajes.filter(ruta__origen__icontains=ruta_origen)
        if ruta_destino:
            viajes = viajes.filter(ruta__destino__icontains=ruta_destino)

        data = []
        for viaje in viajes:
            # Limpiar expiradas antes de contar
            Reserva.limpiar_expiradas(viaje=viaje)
            total_asientos = viaje.autobus.capacidad_total
            reservas_activas = Reserva.objects.filter(
                viaje=viaje,
                estado__in=['apartado', 'confirmado', 'pendiente']
            ).count()

            data.append({
                'id': viaje.id,
                'ruta': {
                    'id': viaje.ruta.id,
                    'origen': viaje.ruta.origen,
                    'destino': viaje.ruta.destino,
                    'duracion_estimada': viaje.ruta.duracion_estimada,
                },
                'autobus': {
                    'id': viaje.autobus.id,
                    'nombre': viaje.autobus.nombre,
                    'placa': viaje.autobus.placa,
                    'pisos': viaje.autobus.pisos,
                },
                'tipo_viaje': viaje.tipo_viaje,
                'fecha_salida': str(viaje.fecha_salida),
                'hora_salida': str(viaje.hora_salida),
                'fecha_vuelta': str(viaje.fecha_vuelta) if viaje.fecha_vuelta else None,
                'hora_vuelta': str(viaje.hora_vuelta) if viaje.hora_vuelta else None,
                'precio_usd': float(viaje.precio_usd),
                'asientos_totales': total_asientos,
                'asientos_ocupados': reservas_activas,
                'asientos_disponibles': total_asientos - reservas_activas,
            })

        return Response({
            'total': len(data),
            'viajes': data,
            'timestamp': timezone.now().isoformat(),
        })


class ViajeDetalleView(ExternoBaseView):
    """
    GET /api/externo/viajes/{id}/
    Detalle completo de un viaje específico.
    """

    def get(self, request, viaje_id):
        try:
            viaje = Viaje.objects.select_related('ruta', 'autobus').get(pk=viaje_id)
        except Viaje.DoesNotExist:
            return Response(
                {'error': 'Viaje no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )

        Reserva.limpiar_expiradas(viaje=viaje)

        total_asientos = viaje.autobus.capacidad_total
        reservas = Reserva.objects.filter(
            viaje=viaje,
            estado__in=['apartado', 'confirmado', 'pendiente']
        )

        return Response({
            'id': viaje.id,
            'ruta': {
                'id': viaje.ruta.id,
                'origen': viaje.ruta.origen,
                'destino': viaje.ruta.destino,
                'duracion_estimada': viaje.ruta.duracion_estimada,
            },
            'autobus': {
                'id': viaje.autobus.id,
                'nombre': viaje.autobus.nombre,
                'placa': viaje.autobus.placa,
                'marca': viaje.autobus.marca,
                'color': viaje.autobus.color,
                'anio': viaje.autobus.anio,
                'pisos': viaje.autobus.pisos,
                'capacidad_total': total_asientos,
            },
            'tipo_viaje': viaje.tipo_viaje,
            'fecha_salida': str(viaje.fecha_salida),
            'hora_salida': str(viaje.hora_salida),
            'fecha_vuelta': str(viaje.fecha_vuelta) if viaje.fecha_vuelta else None,
            'hora_vuelta': str(viaje.hora_vuelta) if viaje.hora_vuelta else None,
            'precio_usd': float(viaje.precio_usd),
            'asientos_totales': total_asientos,
            'asientos_ocupados': reservas.count(),
            'asientos_disponibles': total_asientos - reservas.count(),
            'timestamp': timezone.now().isoformat(),
        })


class AsientosViajeView(ExternoBaseView):
    """
    GET /api/externo/viajes/{id}/asientos/
    Mapa completo de asientos con estado (disponible/ocupado/pendiente).
    """

    def get(self, request, viaje_id):
        try:
            viaje = Viaje.objects.select_related('autobus').get(pk=viaje_id)
        except Viaje.DoesNotExist:
            return Response(
                {'error': 'Viaje no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Limpiar expiradas y obtener reservas activas
        Reserva.limpiar_expiradas(viaje=viaje)

        reservas = Reserva.objects.filter(
            viaje=viaje,
            estado__in=['pendiente', 'apartado', 'confirmado']
        ).values(
            'numero_asiento', 'piso_asiento', 'estado',
            'nombre_pasajero', 'cedula_pasajero',
            'nombre_asignado', 'cedula_asignado',
            'para_otra_persona', 'es_menor_edad',
        )

        # Indexar por (piso, asiento)
        reservas_map = {}
        for r in reservas:
            key = (r['piso_asiento'], r['numero_asiento'])
            reservas_map[key] = r

        # Construir mapa por piso
        pisos_data = []
        for piso in viaje.autobus.pisos_config.all().order_by('numero_piso'):
            asientos_piso = []
            for row in (piso.layout or []):
                for cell in row:
                    if isinstance(cell, dict) and cell.get('type') == 'seat':
                        num = cell.get('number')
                        if num is None:
                            continue
                        key = (piso.numero_piso, num)
                        reserva = reservas_map.get(key)

                        asiento_data = {
                            'numero': num,
                            'piso': piso.numero_piso,
                            'estado': 'disponible',
                        }

                        if reserva:
                            asiento_data['estado'] = reserva['estado']
                            # Solo mostrar datos del pasajero si está confirmado
                            if reserva['estado'] == 'confirmado':
                                if reserva['para_otra_persona'] and reserva['nombre_asignado']:
                                    asiento_data['pasajero'] = {
                                        'nombre': reserva['nombre_asignado'],
                                        'cedula': reserva['cedula_asignado'],
                                        'es_menor': reserva['es_menor_edad'],
                                    }
                                else:
                                    asiento_data['pasajero'] = {
                                        'nombre': reserva['nombre_pasajero'],
                                        'cedula': reserva['cedula_pasajero'],
                                        'es_menor': reserva['es_menor_edad'],
                                    }

                        asientos_piso.append(asiento_data)

            pisos_data.append({
                'piso': piso.numero_piso,
                'filas': piso.filas,
                'columnas': piso.columnas,
                'asientos': asientos_piso,
            })

        total = sum(len(p['asientos']) for p in pisos_data)
        ocupados = sum(1 for p in pisos_data for a in p['asientos'] if a['estado'] != 'disponible')

        return Response({
            'viaje_id': viaje.id,
            'autobus': viaje.autobus.nombre,
            'placa': viaje.autobus.placa,
            'asientos_totales': total,
            'asientos_ocupados': ocupados,
            'asientos_disponibles': total - ocupados,
            'pisos': pisos_data,
            'timestamp': timezone.now().isoformat(),
        })


class PasajerosViajeView(ExternoBaseView):
    """
    GET /api/externo/viajes/{id}/pasajeros/
    Lista de pasajeros confirmados para un viaje.
    """

    def get(self, request, viaje_id):
        try:
            viaje = Viaje.objects.select_related('ruta').get(pk=viaje_id)
        except Viaje.DoesNotExist:
            return Response(
                {'error': 'Viaje no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )

        reservas = Reserva.objects.filter(
            viaje=viaje,
            estado='confirmado'
        ).select_related('usuario').order_by('piso_asiento', 'numero_asiento')

        pasajeros = []
        for r in reservas:
            # Determinar nombre/cédula del pasajero real
            if r.para_otra_persona and r.nombre_asignado:
                nombre = r.nombre_asignado
                cedula = r.cedula_asignado
            else:
                nombre = r.nombre_pasajero or r.usuario.get_full_name()
                cedula = r.cedula_pasajero or getattr(r.usuario, 'cedula', '')

            pasajeros.append({
                'asiento': r.numero_asiento,
                'piso': r.piso_asiento,
                'nombre': nombre,
                'cedula': cedula,
                'es_menor': r.es_menor_edad,
                'codigo_ticket': r.codigo_ticket,
                'fecha_confirmacion': r.fecha_actualizacion.isoformat() if r.fecha_actualizacion else None,
            })

        return Response({
            'viaje_id': viaje.id,
            'ruta': f"{viaje.ruta.origen} → {viaje.ruta.destino}",
            'fecha_salida': str(viaje.fecha_salida),
            'hora_salida': str(viaje.hora_salida),
            'total_pasajeros': len(pasajeros),
            'pasajeros': pasajeros,
            'timestamp': timezone.now().isoformat(),
        })


class OcuparAsientosView(ExternoBaseView):
    """
    POST /api/externo/viajes/{id}/ocupar-asientos/

    Recibe asientos ocupados desde el sistema externo.
    Crea reservas con estado 'confirmado' directamente.

    Body JSON:
    {
        "asientos": [
            {
                "numero": 5,
                "piso": 1,
                "nombre_pasajero": "Juan Pérez",
                "cedula_pasajero": "V-12345678"
            }
        ],
        "referencia_externa": "TICKET-EXT-001"
    }
    """

    def post(self, request, viaje_id):
        try:
            viaje = Viaje.objects.get(pk=viaje_id, activo=True)
        except Viaje.DoesNotExist:
            return Response(
                {'error': 'Viaje no encontrado o no activo.'},
                status=status.HTTP_404_NOT_FOUND
            )

        asientos_data = request.data.get('asientos', [])
        referencia = request.data.get('referencia_externa', '')

        if not asientos_data:
            return Response(
                {'error': 'Debe enviar al menos un asiento.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(asientos_data) > 50:
            return Response(
                {'error': 'Máximo 50 asientos por petición.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Limpiar expiradas antes de validar
        Reserva.limpiar_expiradas(viaje=viaje)

        # Validar cada asiento
        errores = []
        asientos_validos = []
        for i, asiento in enumerate(asientos_data):
            numero = asiento.get('numero')
            piso = asiento.get('piso', 1)
            nombre = asiento.get('nombre_pasajero', '').strip()
            cedula = asiento.get('cedula_pasajero', '').strip()

            if not numero:
                errores.append(f'Asiento #{i+1}: "numero" es requerido.')
                continue
            if not nombre:
                errores.append(f'Asiento #{i+1}: "nombre_pasajero" es requerido.')
                continue
            if not cedula:
                errores.append(f'Asiento #{i+1}: "cedula_pasajero" es requerido.')
                continue

            # Verificar que el asiento no esté ya ocupado
            existe = Reserva.objects.filter(
                viaje=viaje,
                numero_asiento=numero,
                piso_asiento=piso,
                estado__in=['pendiente', 'apartado', 'confirmado']
            ).exists()

            if existe:
                errores.append(f'Asiento #{i+1} (Piso {piso}, Asiento {numero}): ya está ocupado.')
                continue

            asientos_validos.append({
                'numero': numero,
                'piso': piso,
                'nombre': nombre,
                'cedula': cedula,
            })

        if errores and not asientos_validos:
            return Response(
                {'error': 'Ningún asiento pudo ser registrado.', 'detalles': errores},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Necesitamos un usuario para las reservas.
        # Usamos o creamos un usuario "sistema_externo"
        from usuarios.models import Usuario
        user_externo, _ = Usuario.objects.get_or_create(
            username='sistema_externo',
            defaults={
                'first_name': 'Sistema',
                'last_name': 'Externo',
                'email': 'sistema@externo.local',
                'is_active': True,
                'email_verificado': True,
            }
        )

        # Crear un grupo_pago para agrupar estas reservas externas
        import uuid
        grupo = uuid.uuid4()

        creadas = []
        for asiento in asientos_validos:
            try:
                reserva = Reserva.objects.create(
                    usuario=user_externo,
                    viaje=viaje,
                    numero_asiento=asiento['numero'],
                    piso_asiento=asiento['piso'],
                    estado='confirmado',
                    nombre_pasajero=asiento['nombre'],
                    cedula_pasajero=asiento['cedula'],
                    grupo_pago=grupo,
                    para_otra_persona=True,
                    nombre_asignado=asiento['nombre'],
                    cedula_asignado=asiento['cedula'],
                )
                creadas.append({
                    'reserva_id': reserva.id,
                    'asiento': asiento['numero'],
                    'piso': asiento['piso'],
                    'codigo_ticket': reserva.codigo_ticket,
                    'nombre': asiento['nombre'],
                    'cedula': asiento['cedula'],
                })
            except IntegrityError:
                errores.append(f'Asiento Piso {asiento["piso"]}, Número {asiento["numero"]}: conflicto al crear.')

        return Response({
            'mensaje': f'{len(creadas)} asiento(s) registrado(s) exitosamente.',
            'referencia_externa': referencia,
            'grupo_pago': str(grupo),
            'asientos_creados': creadas,
            'errores': errores if errores else None,
            'timestamp': timezone.now().isoformat(),
        }, status=status.HTTP_201_CREATED)
