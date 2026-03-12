from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import IntegrityError
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

        reservas_creadas = []
        errores = []

        for asiento_data in asientos:
            numero = asiento_data.get('numero')
            piso = asiento_data.get('piso', 1)

            try:
                reserva = Reserva.objects.create(
                    usuario=request.user,
                    viaje=viaje,
                    numero_asiento=numero,
                    piso_asiento=piso,
                    nombre_pasajero=nombre,
                    cedula_pasajero=cedula,
                    estado='pendiente'
                )
                reservas_creadas.append(reserva)
            except IntegrityError:
                errores.append(f"Asiento {numero} (Piso {piso}) ya está reservado.")

        if errores and not reservas_creadas:
            return Response(
                {"error": "No se pudo crear ninguna reserva.", "detalles": errores},
                status=status.HTTP_409_CONFLICT
            )

        # Generar info para WhatsApp
        config = ConfiguracionGeneral.load()
        asientos_str = ', '.join([f"#{r.numero_asiento} (P{r.piso_asiento})" for r in reservas_creadas])
        detalles = (
            f"🚌 *Reserva Aerorutas*\n"
            f"📍 {viaje.ruta.origen} → {viaje.ruta.destino}\n"
            f"📅 {viaje.fecha_salida} a las {viaje.hora_salida}\n"
            f"💺 Asientos: {asientos_str}\n"
            f"💰 Total: ${viaje.precio_usd * len(reservas_creadas)} USD\n"
            f"👤 {nombre} - CI: {cedula}\n"
            f"🔖 Reserva(s): {', '.join([f'#{r.id}' for r in reservas_creadas])}"
        )

        mensaje_wsp = config.mensaje_whatsapp.replace('{detalles}', detalles)
        whatsapp_url = f"https://wa.me/{config.whatsapp_vendedor}?text={mensaje_wsp}"

        return Response({
            "mensaje": "Reserva(s) creada(s) exitosamente. Estado: Pendiente.",
            "reservas": ReservaSerializer(reservas_creadas, many=True).data,
            "whatsapp_url": whatsapp_url,
            "whatsapp_numero": config.whatsapp_vendedor,
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
            reserva = Reserva.objects.select_related('viaje', 'viaje__ruta', 'usuario').get(pk=reserva_id)
        except Reserva.DoesNotExist:
            return Response({"error": "Reserva no encontrada."}, status=404)

        nuevo_estado = request.data.get('estado')
        if nuevo_estado not in ['pendiente', 'confirmado', 'cancelado']:
            return Response({"error": "Estado inválido."}, status=400)

        reserva.estado = nuevo_estado
        reserva.save()

        return Response({
            'mensaje': f'Reserva #{reserva.id} actualizada a "{reserva.get_estado_display()}".',
            'reserva': AdminReservaSerializer(reserva).data,
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
