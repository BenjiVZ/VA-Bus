from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from .models import Ruta, Viaje, ConfiguracionGeneral
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
        queryset = Viaje.objects.filter(activo=True).select_related('ruta', 'autobus')
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

    reservas_activas = Reserva.objects.filter(
        viaje=viaje,
        estado__in=['pendiente', 'confirmado']
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
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        config = ConfiguracionGeneral.load()

        if not config.tasa_bcv or config.tasa_bcv == 0:
            actualizar_tasa_bcv()
            config.refresh_from_db()

        return Response({
            'tasa_bcv': float(config.tasa_bcv),
            'actualizada': config.tasa_actualizada,
            'fuente': 've.dolarapi.com - Oficial'
        })


class ConfiguracionPublicaView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        config = ConfiguracionGeneral.load()
        serializer = ConfiguracionSerializer(config)
        return Response(serializer.data)
