from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import IntegrityError, transaction
from django.utils import timezone
from datetime import timedelta
import uuid as uuid_lib
from .models import Reserva, BloqueoAsiento
from .serializers import ReservaSerializer, CrearReservaSerializer, AdminReservaSerializer
from viajes.models import Viaje, Autobus, ConfiguracionGeneral
from viajes.ws_broadcast import broadcast_seat_change


BLOQUEO_ASIENTO_MINUTOS = 2
MAX_SESION_SELECCION_MINUTOS = 10


EXTENSIONES_PERMITIDAS = {'.jpg', '.jpeg', '.png', '.webp', '.pdf'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def validar_archivo(archivo, nombre_campo):
    """Valida extensión y tamaño de un archivo subido."""
    if not archivo:
        return f'{nombre_campo} es requerido.'
    if archivo.size > MAX_FILE_SIZE:
        return f'{nombre_campo}: El archivo no debe superar 5MB.'
    ext = '.' + archivo.name.rsplit('.', 1)[-1].lower() if '.' in archivo.name else ''
    if ext not in EXTENSIONES_PERMITIDAS:
        return f'{nombre_campo}: Solo se permiten archivos JPG, PNG, WEBP o PDF.'
    return None


class IsAdminUser(permissions.BasePermission):
    """Only staff/superuser can access."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class BloquearAsientoView(APIView):
    """Bloquea temporalmente un asiento para evitar dobles selecciones."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        viaje_id = request.data.get('viaje_id')
        numero_asiento = request.data.get('numero_asiento')
        piso_asiento = request.data.get('piso_asiento', 1)

        if not viaje_id or not numero_asiento:
            return Response(
                {"error": "viaje_id y numero_asiento son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            viaje = Viaje.objects.get(pk=viaje_id, activo=True)
            numero_asiento = int(numero_asiento)
            piso_asiento = int(piso_asiento)
        except (Viaje.DoesNotExist, ValueError, TypeError):
            return Response(
                {"error": "Datos de asiento inválidos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        Reserva.limpiar_expiradas(viaje=viaje)
        BloqueoAsiento.limpiar_expirados(viaje=viaje)

        now = timezone.now()

        # ── Límite máximo de sesión de selección (anti-hoarding) ──
        primer_bloqueo = BloqueoAsiento.objects.filter(
            usuario=request.user,
            viaje=viaje,
        ).order_by('fecha_creacion').first()

        if primer_bloqueo:
            tiempo_seleccion = (now - primer_bloqueo.fecha_creacion).total_seconds()
            if tiempo_seleccion > MAX_SESION_SELECCION_MINUTOS * 60:
                BloqueoAsiento.objects.filter(usuario=request.user, viaje=viaje).delete()
                return Response(
                    {
                        "error": "Tu tiempo de selección ha expirado (10 minutos). "
                                 "Los asientos fueron liberados. Puedes seleccionar nuevamente.",
                        "sesion_expirada": True,
                    },
                    status=status.HTTP_408_REQUEST_TIMEOUT
                )

        fecha_expiracion = now + timedelta(minutes=BLOQUEO_ASIENTO_MINUTOS)

        with transaction.atomic():
            asiento_reservado = Reserva.objects.select_for_update().filter(
                viaje=viaje,
                numero_asiento=numero_asiento,
                piso_asiento=piso_asiento,
                estado__in=['pendiente', 'apartado', 'confirmado']
            ).exists()
            if asiento_reservado:
                return Response(
                    {"error": "Este asiento ya no está disponible."},
                    status=status.HTTP_409_CONFLICT
                )

            bloqueo = BloqueoAsiento.objects.select_for_update().filter(
                viaje=viaje,
                numero_asiento=numero_asiento,
                piso_asiento=piso_asiento,
            ).first()

            if bloqueo and bloqueo.usuario_id != request.user.id and bloqueo.fecha_expiracion > now:
                return Response(
                    {"error": "Este asiento está siendo seleccionado por otro usuario."},
                    status=status.HTTP_409_CONFLICT
                )

            if bloqueo:
                bloqueo.usuario = request.user
                bloqueo.fecha_expiracion = fecha_expiracion
                bloqueo.save(update_fields=['usuario', 'fecha_expiracion'])
            else:
                try:
                    bloqueo = BloqueoAsiento.objects.create(
                        usuario=request.user,
                        viaje=viaje,
                        numero_asiento=numero_asiento,
                        piso_asiento=piso_asiento,
                        fecha_expiracion=fecha_expiracion,
                    )
                except IntegrityError:
                    return Response(
                        {"error": "Este asiento acaba de ser tomado por otro usuario."},
                        status=status.HTTP_409_CONFLICT
                    )

        # ── Broadcast WS: avisar al resto que este asiento quedó "locked" ──
        broadcast_seat_change(
            viaje_id=viaje.id,
            numero=numero_asiento,
            piso=piso_asiento,
            estado='locked',
            usuario_id=request.user.id,
        )

        return Response({
            "ok": True,
            "mensaje": "Asiento bloqueado temporalmente.",
            "fecha_expiracion": bloqueo.fecha_expiracion.isoformat(),
        })


class LiberarAsientoView(APIView):
    """Libera un asiento previamente bloqueado por el usuario."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        viaje_id = request.data.get('viaje_id')
        numero_asiento = request.data.get('numero_asiento')
        piso_asiento = request.data.get('piso_asiento', 1)

        if not viaje_id or not numero_asiento:
            return Response(
                {"error": "viaje_id y numero_asiento son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            numero_asiento = int(numero_asiento)
            piso_asiento = int(piso_asiento)
        except (ValueError, TypeError):
            return Response(
                {"error": "Datos de asiento inválidos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        deleted_count, _ = BloqueoAsiento.objects.filter(
            usuario=request.user,
            viaje_id=viaje_id,
            numero_asiento=numero_asiento,
            piso_asiento=piso_asiento,
        ).delete()

        if deleted_count > 0:
            broadcast_seat_change(
                viaje_id=int(viaje_id),
                numero=numero_asiento,
                piso=piso_asiento,
                estado='unlocked',
                usuario_id=request.user.id,
            )

        return Response({
            "ok": True,
            "liberado": deleted_count > 0,
        })


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

        # ── TRANSACCIÓN ATÓMICA: protege contra reservas simultáneas ──
        try:
            with transaction.atomic():
                # 1. Primero, auto-cancelar reservas expiradas de este viaje
                Reserva.limpiar_expiradas(viaje=viaje)
                BloqueoAsiento.limpiar_expirados(viaje=viaje)

                for asiento_data in asientos:
                    numero = asiento_data.get('numero')
                    piso = asiento_data.get('piso', 1)
                    es_menor = asiento_data.get('es_menor', False)
                    para_otra = asiento_data.get('para_otra', False)
                    nombre_asig = asiento_data.get('nombre_asignado', '')
                    cedula_asig = asiento_data.get('cedula_asignado', '')
                    viaja_animal = asiento_data.get('viaja_con_animal', False)
                    tipo_mascota = asiento_data.get('tipo_mascota', '')
                    es_discap = asiento_data.get('es_discapacitado', False)

                    bloqueo_otro = BloqueoAsiento.objects.select_for_update().filter(
                        viaje=viaje,
                        numero_asiento=numero,
                        piso_asiento=piso,
                        fecha_expiracion__gt=timezone.now(),
                    ).exclude(usuario=request.user).exists()

                    if bloqueo_otro:
                        errores.append(f"Asiento {numero} (Piso {piso}) está siendo seleccionado por otro usuario.")
                        continue

                    # 2. Bloqueo pesimista: select_for_update() bloquea las filas
                    #    hasta que la transacción termine, impidiendo que otro
                    #    usuario reserve el mismo asiento al mismo tiempo.
                    asiento_ocupado = Reserva.objects.select_for_update().filter(
                        viaje=viaje,
                        numero_asiento=numero,
                        piso_asiento=piso,
                        estado__in=['pendiente', 'apartado', 'confirmado']
                    ).exists()

                    if asiento_ocupado:
                        errores.append(f"Asiento {numero} (Piso {piso}) ya está reservado.")
                        continue

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
                        viaja_con_animal=viaja_animal,
                        tipo_mascota=tipo_mascota if viaja_animal else '',
                        es_discapacitado=es_discap,
                    )
                    reservas_creadas.append(reserva)

                # Liberar bloqueos temporales de los asientos ya convertidos en reserva
                for reserva in reservas_creadas:
                    BloqueoAsiento.objects.filter(
                        usuario=request.user,
                        viaje=viaje,
                        numero_asiento=reserva.numero_asiento,
                        piso_asiento=reserva.piso_asiento,
                    ).delete()

                # Si ningún asiento se pudo reservar, revertir todo
                if not reservas_creadas:
                    raise IntegrityError("Ningún asiento disponible")

        except IntegrityError:
            if not reservas_creadas:
                return Response(
                    {"error": "No se pudo crear ninguna reserva.", "detalles": errores},
                    status=status.HTTP_409_CONFLICT
                )

        # ── Broadcast WS: asientos pasan a "reserved" para el resto ──
        # Usamos on_commit para asegurar que sólo se emite si la transacción
        # se guardó realmente (evita emitir y luego rollback).
        usuario_id = request.user.id

        def _emit():
            for r in reservas_creadas:
                broadcast_seat_change(
                    viaje_id=viaje.id,
                    numero=r.numero_asiento,
                    piso=r.piso_asiento,
                    estado='reserved',
                    usuario_id=usuario_id,
                )

        transaction.on_commit(_emit)

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


class SubirDocumentosMenorView(APIView):
    """Sube los documentos requeridos para un pasajero menor de edad."""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, reserva_id):
        try:
            reserva = Reserva.objects.get(pk=reserva_id, usuario=request.user)
        except Reserva.DoesNotExist:
            return Response(
                {"error": "Reserva no encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not reserva.es_menor_edad:
            return Response(
                {"error": "Esta reserva no está marcada como menor de edad."},
                status=status.HTTP_400_BAD_REQUEST
            )

        partida = request.FILES.get('doc_partida_nacimiento')
        foto = request.FILES.get('doc_foto_menor')
        cedula_rep = request.FILES.get('doc_cedula_representante')

        # Validar archivos
        errores = []
        for archivo, nombre in [
            (partida, 'Partida de nacimiento'),
            (foto, 'Foto del menor'),
            (cedula_rep, 'Cédula del representante'),
        ]:
            err = validar_archivo(archivo, nombre)
            if err:
                errores.append(err)

        if errores:
            return Response(
                {"error": "Errores en los documentos.", "detalles": errores},
                status=status.HTTP_400_BAD_REQUEST
            )

        reserva.doc_partida_nacimiento = partida
        reserva.doc_foto_menor = foto
        reserva.doc_cedula_representante = cedula_rep
        reserva.save(update_fields=[
            'doc_partida_nacimiento', 'doc_foto_menor', 'doc_cedula_representante'
        ])

        return Response({
            "ok": True,
            "mensaje": "Documentos del menor subidos correctamente.",
        })


class SubirDocVacunacionView(APIView):
    """Sube el documento de vacunación para un pasajero que viaja con animal."""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, reserva_id):
        try:
            reserva = Reserva.objects.get(pk=reserva_id, usuario=request.user)
        except Reserva.DoesNotExist:
            return Response(
                {"error": "Reserva no encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not reserva.viaja_con_animal:
            return Response(
                {"error": "Esta reserva no está marcada como viaje con animal."},
                status=status.HTTP_400_BAD_REQUEST
            )

        archivo = request.FILES.get('doc_vacunacion_animal')
        err = validar_archivo(archivo, 'Tarjeta de vacunación')
        if err:
            return Response(
                {"error": err},
                status=status.HTTP_400_BAD_REQUEST
            )

        reserva.doc_vacunacion_animal = archivo
        reserva.save(update_fields=['doc_vacunacion_animal'])

        return Response({
            "ok": True,
            "mensaje": "Documento de vacunación subido correctamente.",
        })


class SubirDocDiscapacidadView(APIView):
    """Sube el documento de discapacidad (certificado médico, RCP, etc.)."""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, reserva_id):
        try:
            reserva = Reserva.objects.get(pk=reserva_id, usuario=request.user)
        except Reserva.DoesNotExist:
            return Response(
                {"error": "Reserva no encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not reserva.es_discapacitado:
            return Response(
                {"error": "Esta reserva no está marcada como persona con discapacidad."},
                status=status.HTTP_400_BAD_REQUEST
            )

        archivo = request.FILES.get('doc_discapacidad')
        err = validar_archivo(archivo, 'Documento de discapacidad')
        if err:
            return Response(
                {"error": err},
                status=status.HTTP_400_BAD_REQUEST
            )

        reserva.doc_discapacidad = archivo
        reserva.save(update_fields=['doc_discapacidad'])

        return Response({
            "ok": True,
            "mensaje": "Documento de discapacidad subido correctamente.",
        })


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

        # ── Broadcast WS si el cambio de estado libera o ocupa el asiento ──
        if nuevo_estado == 'cancelado' and old_estado != 'cancelado':
            broadcast_seat_change(
                viaje_id=reserva.viaje_id,
                numero=reserva.numero_asiento,
                piso=reserva.piso_asiento,
                estado='released',
            )
        elif (
            nuevo_estado in ('pendiente', 'confirmado')
            and old_estado == 'cancelado'
        ):
            broadcast_seat_change(
                viaje_id=reserva.viaje_id,
                numero=reserva.numero_asiento,
                piso=reserva.piso_asiento,
                estado='reserved',
            )

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

        # Limpiar expiradas y verificar disponibilidad
        Reserva.limpiar_expiradas(viaje=reserva.viaje)
        exists = Reserva.objects.filter(
            viaje=reserva.viaje,
            numero_asiento=nuevo_numero,
            piso_asiento=nuevo_piso,
            estado__in=['pendiente', 'apartado', 'confirmado']
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
            total_reservas=Count('reservas', filter=Q(reservas__estado__in=['pendiente', 'apartado', 'confirmado'])),
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
                'viaja_con_animal': r.viaja_con_animal,
                'es_discapacitado': r.es_discapacitado,
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
                'viaja_con_animal': reserva.viaja_con_animal,
                'es_discapacitado': reserva.es_discapacitado,
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
