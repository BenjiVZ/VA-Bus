import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../config/theme.dart';
import '../data/venezuela_cities.dart';

/// Mapa que muestra la ruta entre dos ciudades de Venezuela.
///
/// Resuelve [origen] y [destino] contra el catálogo de ciudades VE y
/// consulta OSRM (router.project-osrm.org) para trazar la ruta por carretera
/// real. Si OSRM no responde en ~5s o falla, cae a una línea recta.
///
///   - Marker verde en origen
///   - Marker rojo en destino
///   - Polyline navy siguiendo la vía (o recta como fallback)
///   - Distancia por carretera como tag flotante
class RouteMap extends StatefulWidget {
  final String origen;
  final String destino;
  final double height;
  final BorderRadius? borderRadius;

  const RouteMap({
    super.key,
    required this.origen,
    required this.destino,
    this.height = 200,
    this.borderRadius,
  });

  @override
  State<RouteMap> createState() => _RouteMapState();
}

class _RouteMapState extends State<RouteMap> {
  // Caché compartida entre instancias para no repetir requests al volver
  // a abrir el mismo viaje.
  static final Map<String, _RouteData> _cache = {};

  List<LatLng>? _roadPoints;
  double? _roadKm;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _fetchRoute();
  }

  @override
  void didUpdateWidget(covariant RouteMap old) {
    super.didUpdateWidget(old);
    if (old.origen != widget.origen || old.destino != widget.destino) {
      setState(() {
        _roadPoints = null;
        _roadKm = null;
      });
      _fetchRoute();
    }
  }

  Future<void> _fetchRoute() async {
    final origen = VenezuelaCities.resolve(widget.origen);
    final destino = VenezuelaCities.resolve(widget.destino);
    final key =
        '${origen.longitude},${origen.latitude};${destino.longitude},${destino.latitude}';

    final cached = _cache[key];
    if (cached != null) {
      setState(() {
        _roadPoints = cached.points;
        _roadKm = cached.km;
      });
      return;
    }

    setState(() => _loading = true);

    try {
      final dio = Dio(BaseOptions(
        connectTimeout: const Duration(seconds: 5),
        receiveTimeout: const Duration(seconds: 5),
      ));
      final url =
          'https://router.project-osrm.org/route/v1/driving/$key?overview=full&geometries=geojson';
      final res = await dio.get(url);
      final data = res.data as Map<String, dynamic>;
      final routes = data['routes'] as List?;
      if (routes != null && routes.isNotEmpty) {
        final route = routes.first as Map<String, dynamic>;
        final geom = route['geometry'] as Map<String, dynamic>;
        final coords = geom['coordinates'] as List;
        final points = coords
            .whereType<List>()
            .map((c) => LatLng(
                  (c[1] as num).toDouble(),
                  (c[0] as num).toDouble(),
                ))
            .toList();
        final meters = (route['distance'] as num?)?.toDouble() ?? 0;
        final km = meters / 1000.0;
        _cache[key] = _RouteData(points, km);
        if (mounted) {
          setState(() {
            _roadPoints = points;
            _roadKm = km;
            _loading = false;
          });
        }
        return;
      }
    } catch (_) {
      // Fallback silencioso a línea recta.
    }
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final origenLatLng = VenezuelaCities.resolve(widget.origen);
    final destinoLatLng = VenezuelaCities.resolve(widget.destino);
    final bothKnown = VenezuelaCities.isKnown(widget.origen) &&
        VenezuelaCities.isKnown(widget.destino);

    // Distancia: real por carretera si OSRM respondió; recta como fallback.
    final straightKm = const Distance()
        .as(LengthUnit.Kilometer, origenLatLng, destinoLatLng);
    final displayKm = _roadKm ?? straightKm;
    final isRoadDistance = _roadKm != null;

    final radius = widget.borderRadius ?? BorderRadius.circular(16);
    final hasRoad = _roadPoints != null && _roadPoints!.length >= 2;
    final polylinePoints = hasRoad ? _roadPoints! : [origenLatLng, destinoLatLng];

    return ClipRRect(
      borderRadius: radius,
      child: Container(
        height: widget.height,
        decoration: BoxDecoration(
          borderRadius: radius,
          border: Border.all(color: AppColors.borderSubtle),
        ),
        child: Stack(
          children: [
            FlutterMap(
              options: MapOptions(
                interactionOptions: const InteractionOptions(
                  flags: InteractiveFlag.pinchZoom | InteractiveFlag.drag,
                ),
                initialCameraFit: CameraFit.coordinates(
                  coordinates: [origenLatLng, destinoLatLng],
                  padding: const EdgeInsets.all(40),
                ),
                minZoom: 5,
                maxZoom: 13,
              ),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'com.aerorutas.va_bus_mobile',
                  maxZoom: 19,
                ),
                PolylineLayer(
                  polylines: [
                    Polyline(
                      points: polylinePoints,
                      color: AppColors.blue500,
                      strokeWidth: 4,
                      // Recta = punteada (es solo aproximación);
                      // ruta real = sólida.
                      pattern: hasRoad
                          ? const StrokePattern.solid()
                          : StrokePattern.dashed(segments: const [10, 6]),
                      borderColor: Colors.white,
                      borderStrokeWidth: 1.5,
                    ),
                  ],
                ),
                MarkerLayer(
                  markers: [
                    _marker(origenLatLng,
                        color: AppColors.green500, isOrigin: true),
                    _marker(destinoLatLng,
                        color: AppColors.red500, isOrigin: false),
                  ],
                ),
              ],
            ),

            // Tag de distancia (esquina superior derecha)
            if (bothKnown)
              Positioned(
                top: 10,
                right: 10,
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.1),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        isRoadDistance
                            ? Icons.alt_route_rounded
                            : Icons.straighten_rounded,
                        size: 14,
                        color: AppColors.blue500,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        '${isRoadDistance ? '' : '~'}${displayKm.toStringAsFixed(0)} km',
                        style: const TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 12,
                          color: AppColors.blue700,
                        ),
                      ),
                    ],
                  ),
                ),
              ),

            // Indicador sutil mientras OSRM responde
            if (_loading)
              Positioned(
                top: 10,
                left: 10,
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.9),
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.08),
                        blurRadius: 6,
                      ),
                    ],
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      SizedBox(
                        width: 10,
                        height: 10,
                        child: CircularProgressIndicator(
                          strokeWidth: 1.6,
                          color: AppColors.blue500,
                        ),
                      ),
                      SizedBox(width: 6),
                      Text(
                        'Calculando ruta…',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textTertiary,
                        ),
                      ),
                    ],
                  ),
                ),
              ),

            if (!bothKnown)
              Positioned(
                bottom: 10,
                left: 10,
                right: 10,
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.yellow50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppColors.yellow400),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.info_outline_rounded,
                          size: 14, color: AppColors.yellow600),
                      SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          'Ubicación aproximada',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: AppColors.yellow600,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

            Positioned(
              bottom: 0,
              right: 0,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                color: Colors.white.withValues(alpha: 0.75),
                child: const Text(
                  '© OpenStreetMap · OSRM',
                  style: TextStyle(fontSize: 8, color: AppColors.textMuted),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Marker _marker(LatLng pos, {required Color color, required bool isOrigin}) {
    return Marker(
      point: pos,
      width: 40,
      height: 48,
      alignment: Alignment.topCenter,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white, width: 3),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.25),
                  blurRadius: 4,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Icon(
              isOrigin
                  ? Icons.radio_button_checked_rounded
                  : Icons.location_on_rounded,
              color: Colors.white,
              size: 14,
            ),
          ),
          Container(
            width: 2,
            height: 8,
            color: color,
          ),
        ],
      ),
    );
  }
}

class _RouteData {
  final List<LatLng> points;
  final double km;
  const _RouteData(this.points, this.km);
}
