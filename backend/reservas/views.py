from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta
import uuid as uuid_lib
from .models import Reserva
from .serializers import ReservaSerializer, CrearReservaSerializer, AdminReservaSerializer
from viajes.models import Viaje, Autobus, ConfiguracionGeneral


class IsAdminUser(permissions.BasePermission):
    """Only staff/superuser can access."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class CrearReservaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # ── Anti-spam check ──
        ordenes_pendientes = Reserva.objects.filter(
            usuario=request.user,
            estado__in=['pendiente', 'apartado']
        ).values('grupo_pago').distinct().count()

        if ordenes_pendientes >= 3:
            return Response({
                "error": "Tienes demasiadas órdenes activas. Completa o espera que se procesen antes de crear nuevas. "
                         "El abuso del sistema puede resultar en el bloqueo de tu cuenta.",
                "bloqueado": True,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        serializer = CrearReservaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        viaje_id = serializer.validated_data['viaje_id']
        asientos = serializer.validated_data['asientos']
        nombre = serializer.validated_data.get('nombre_pasajero', '')
        cedula = serializer.validated_data.get('cedula_pasajero', '')

        try:
            viaje = Viaje.objects.get(pk=viaje_id, activo=True)
        except Viaje.DoesNotExist:
            return Response(
                {"error": "Viaje no encontrado o no está activo."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Generate grupo_pago and expiration
        grupo_pago = uuid_lib.uuid4()
        fecha_expiracion = timezone.now() + timedelta(minutes=15)

        reservas_creadas = []
        errores = []

        for asiento_data in asientos:
            numero = asiento_data.get('numero')
            piso = asiento_data.get('piso', 1)
            es_menor = asiento_data.get('es_menor', False)
            para_otra = asiento_data.get('para_otra', False)
            nombre_asig = asiento_data.get('nombre_asignado', '')
            cedula_asig = asiento_data.get('cedula_asignado', '')

            try:
                reserva = Reserva.objects.create(
                    usuario=request.user,
                    viaje=viaje,
                    numero_asiento=numero,
                    piso_asiento=piso,
                    nombre_pasajero=nombre,
                    cedula_pasajero=cedula,
                    estado='pendiente',
                    grupo_pago=grupo_pago,
                    fecha_expiracion=fecha_expiracion,
                    es_menor_edad=es_menor,
                    para_otra_persona=para_otra,
                    nombre_asignado=nombre_asig,
                    cedula_asignado=cedula_asig,
                )
                reservas_creadas.append(reserva)
            except IntegrityError:
                errores.append(f"Asiento {numero} (Piso {piso}) ya está reservado.")

        if errores and not reservas_creadas:
            return Response(
                {"error": "No se pudo crear ninguna reserva.", "detalles": errores},
                status=status.HTTP_409_CONFLICT
            )

        return Response({
            "mensaje": "Reserva(s) creada(s). Tienes 15 minutos para completar el pago.",
            "reservas": ReservaSerializer(reservas_creadas, many=True).data,
            "grupo_pago": str(grupo_pago),
            "fecha_expiracion": fecha_expiracion.isoformat(),
            "viaje_info": {
                "id": viaje.id,
                "origen": viaje.ruta.origen,
                "destino": viaje.ruta.destino,
                "fecha_salida": str(viaje.fecha_salida),
                "hora_salida": str(viaje.hora_salida),
                "precio_usd": float(viaje.precio_usd),
                "autobus": viaje.autobus.nombre,
            },
            "errores": errores if errores else None
        }, status=status.HTTP_201_CREATED)


class MisReservasView(generics.ListAPIView):
    serializer_class = ReservaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Reserva.objects.filter(
            usuario=self.request.user
        ).select_related('viaje', 'viaje__ruta', 'viaje__autobus')


# ═══════════════════════════════════════════════
# ── ADMIN API ENDPOINTS ──
# ═══════════════════════════════════════════════

class AdminReservasViajeView(APIView):
    """Listar todas las reservas de un viaje (admin only)."""
    permission_classes = [IsAdminUser]

    def get(self, request, viaje_id):
        reservas = Reserva.objects.filter(
            viaje_id=viaje_id
        ).select_related('usuario', 'viaje', 'viaje__ruta', 'viaje__autobus').order_by('piso_asiento', 'numero_asiento')

        return Response({
            'reservas': AdminReservaSerializer(reservas, many=True).data,
            'total': reservas.count(),
            'confirmadas': reservas.filter(estado='confirmado').count(),
            'pendientes': reservas.filter(estado='pendiente').count(),
        })


class AdminCambiarEstadoView(APIView):
    """Cambiar estado de una reserva (confirmar/cancelar)."""
    permission_classes = [IsAdminUser]

    def patch(self, request, reserva_id):
        try:
            reserva = Reserva.objects.select_related('viaje', 'viaje__ruta', 'viaje__autobus', 'usuario').get(pk=reserva_id)
        except Reserva.DoesNotExist:
            return Response({"error": "Reserva no encontrada."}, status=404)

        nuevo_estado = request.data.get('estado')
        if nuevo_estado not in ['pendiente', 'confirmado', 'cancelado']:
            return Response({"error": "Estado inválido."}, status=400)

        old_estado = reserva.estado
        reserva.estado = nuevo_estado
        reserva.save()

        # If confirming, send email with PDF ticket
        email_enviado = False
        if nuevo_estado == 'confirmado' and old_estado != 'confirmado':
            import threading
            from .services import enviar_email_ticket

            config = ConfiguracionGeneral.load()
            viaje = reserva.viaje
            usuario = reserva.usuario

            # Get all reservas in same grupo_pago for this user
            if reserva.grupo_pago:
                reservas_grupo = list(Reserva.objects.filter(
                    grupo_pago=reserva.grupo_pago,
                    estado='confirmado',
                ).select_related('viaje', 'viaje__ruta', 'viaje__autobus'))
            else:
                reservas_grupo = [reserva]

            base_url = request.build_absolute_uri('/').rstrip('/')
            # Use frontend URL for QR codes
            frontend_url = base_url.replace(':8001', ':3000')

            # Send email in a background thread to avoid blocking
            def send_email():
                enviar_email_ticket(reservas_grupo, viaje, config, usuario, frontend_url)

            threading.Thread(target=send_email, daemon=True).start()
            email_enviado = True

        return Response({
            'mensaje': f'Reserva #{reserva.id} actualizada a "{reserva.get_estado_display()}".',
            'reserva': AdminReservaSerializer(reserva).data,
            'email_enviado': email_enviado,
        })


class AdminCambiarAsientoView(APIView):
    """Cambiar el asiento de una reserva existente."""
    permission_classes = [IsAdminUser]

    def patch(self, request, reserva_id):
        try:
            reserva = Reserva.objects.select_related('viaje').get(pk=reserva_id)
        except Reserva.DoesNotExist:
            return Response({"error": "Reserva no encontrada."}, status=404)

        nuevo_numero = request.data.get('numero_asiento')
        nuevo_piso = request.data.get('piso_asiento', reserva.piso_asiento)

        if not nuevo_numero:
            return Response({"error": "Debe especificar numero_asiento."}, status=400)

        # Check if the target seat is available
        exists = Reserva.objects.filter(
            viaje=reserva.viaje,
            numero_asiento=nuevo_numero,
            piso_asiento=nuevo_piso,
            estado__in=['pendiente', 'confirmado']
        ).exclude(pk=reserva.pk).exists()

        if exists:
            return Response({"error": f"El asiento #{nuevo_numero} (Piso {nuevo_piso}) ya está ocupado."}, status=409)

        old_seat = f"#{reserva.numero_asiento} (P{reserva.piso_asiento})"
        reserva.numero_asiento = nuevo_numero
        reserva.piso_asiento = nuevo_piso
        reserva.save()
        new_seat = f"#{reserva.numero_asiento} (P{reserva.piso_asiento})"

        return Response({
            'mensaje': f'Reserva #{reserva.id} movida de {old_seat} a {new_seat}.',
            'reserva': AdminReservaSerializer(reserva).data,
        })


class AdminViajesListView(APIView):
    """Listar viajes activos con conteo de reservas (admin only)."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        from django.db.models import Count, Q
        viajes = Viaje.objects.filter(activo=True).select_related('ruta', 'autobus').annotate(
            total_reservas=Count('reservas', filter=Q(reservas__estado__in=['pendiente', 'confirmado'])),
            reservas_confirmadas=Count('reservas', filter=Q(reservas__estado='confirmado')),
            reservas_pendientes=Count('reservas', filter=Q(reservas__estado='pendiente')),
        ).order_by('fecha_salida', 'hora_salida')

        data = []
        for v in viajes:
            data.append({
                'id': v.id,
                'ruta': f"{v.ruta.origen} → {v.ruta.destino}",
                'autobus': v.autobus.nombre,
                'fecha_salida': v.fecha_salida,
                'hora_salida': v.hora_salida,
                'precio_usd': float(v.precio_usd),
                'capacidad': v.autobus.capacidad_total,
                'total_reservas': v.total_reservas,
                'confirmadas': v.reservas_confirmadas,
                'pendientes': v.reservas_pendientes,
            })

        return Response(data)


class AdminBusesListView(APIView):
    """Listar autobuses con su layout (admin only)."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        from viajes.serializers import AutobusSerializer
        buses = Autobus.objects.prefetch_related('pisos_config').all()
        return Response(AutobusSerializer(buses, many=True).data)


class TicketView(APIView):
    """Retorna datos del ticket para un grupo de pago confirmado."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, grupo_pago):
        reservas = Reserva.objects.filter(
            grupo_pago=grupo_pago,
            usuario=request.user,
            estado='confirmado',
        ).select_related('viaje', 'viaje__ruta', 'viaje__autobus')

        if not reservas.exists():
            return Response(
                {"error": "No se encontraron reservas confirmadas para este grupo."},
                status=status.HTTP_404_NOT_FOUND
            )

        viaje = reservas.first().viaje
        config = ConfiguracionGeneral.load()

        tickets = []
        for r in reservas:
            tickets.append({
                'id': r.id,
                'codigo_ticket': r.codigo_ticket,
                'numero_asiento': r.numero_asiento,
                'piso_asiento': r.piso_asiento,
                'nombre_pasajero': r.nombre_pasajero,
                'cedula_pasajero': r.cedula_pasajero,
                'es_menor_edad': r.es_menor_edad,
                'para_otra_persona': r.para_otra_persona,
                'nombre_asignado': r.nombre_asignado,
                'cedula_asignado': r.cedula_asignado,
                'fecha_confirmacion': r.fecha_actualizacion.isoformat(),
            })

        return Response({
            'grupo_pago': str(grupo_pago),
            'empresa': config.nombre_empresa if config else 'VA-Bus',
            'rif': config.rif if config else '',
            'viaje': {
                'origen': viaje.ruta.origen,
                'destino': viaje.ruta.destino,
                'fecha_salida': str(viaje.fecha_salida),
                'hora_salida': str(viaje.hora_salida),
                'autobus': viaje.autobus.nombre,
                'precio_usd': float(viaje.precio_usd),
                'tipo_viaje': viaje.tipo_viaje,
                'fecha_vuelta': str(viaje.fecha_vuelta) if viaje.fecha_vuelta else None,
                'hora_vuelta': str(viaje.hora_vuelta) if viaje.hora_vuelta else None,
            },
            'tickets': tickets,
        })


class VerificarTicketView(APIView):
    """Endpoint público para verificar un ticket por código QR."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, codigo_ticket):
        try:
            reserva = Reserva.objects.select_related(
                'viaje', 'viaje__ruta', 'viaje__autobus'
            ).get(codigo_ticket=codigo_ticket.upper())
        except Reserva.DoesNotExist:
            return Response({
                'valido': False,
                'mensaje': 'Ticket no encontrado. Código inválido.',
            }, status=status.HTTP_404_NOT_FOUND)

        viaje = reserva.viaje
        es_valido = reserva.estado == 'confirmado'

        return Response({
            'valido': es_valido,
            'estado': reserva.get_estado_display(),
            'mensaje': 'Ticket válido ✅' if es_valido else f'Ticket {reserva.get_estado_display()} ⚠️',
            'datos': {
                'nombre_pasajero': reserva.nombre_pasajero,
                'cedula_pasajero': reserva.cedula_pasajero,
                'es_menor_edad': reserva.es_menor_edad,
                'para_otra_persona': reserva.para_otra_persona,
                'nombre_asignado': reserva.nombre_asignado,
                'cedula_asignado': reserva.cedula_asignado,
                'numero_asiento': reserva.numero_asiento,
                'piso_asiento': reserva.piso_asiento,
                'origen': viaje.ruta.origen,
                'destino': viaje.ruta.destino,
                'fecha_salida': str(viaje.fecha_salida),
                'hora_salida': str(viaje.hora_salida),
                'autobus': viaje.autobus.nombre,
                'tipo_viaje': viaje.tipo_viaje,
            },
        })
