import '../models/viaje.dart';
import 'api_client.dart';

class ViajesService {
  final ApiClient client;
  ViajesService(this.client);

  Future<List<Ruta>> getRutas() async {
    final res = await client.dio.get('/rutas/');
    final data = res.data as List;
    return data
        .whereType<Map<String, dynamic>>()
        .map(Ruta.fromJson)
        .toList();
  }

  Future<Map<String, dynamic>> getStats() async {
    final res = await client.dio.get('/stats/');
    return (res.data as Map<String, dynamic>);
  }

  /// Oficinas en vivo de Aerorutas: [{codofi, desofi, siglas}, ...]
  Future<List<Map<String, dynamic>>> getOficinas() async {
    final res = await client.dio.get('/aerorutas/oficinas/');
    return (res.data as List).whereType<Map<String, dynamic>>().toList();
  }

  Future<List<Viaje>> buscarViajes({String? origen, String? destino, String? fecha}) async {
    final params = <String, dynamic>{};
    if (origen != null && origen.isNotEmpty) params['origen'] = origen;
    if (destino != null && destino.isNotEmpty) params['destino'] = destino;
    if (fecha != null && fecha.isNotEmpty) params['fecha'] = fecha;
    final res = await client.dio.get('/aerorutas/viajes/', queryParameters: params);
    final body = res.data;
    final list = (body is Map && body['results'] is List)
        ? body['results'] as List
        : (body is List ? body : <dynamic>[]);
    return list.whereType<Map<String, dynamic>>().map(Viaje.fromJson).toList();
  }

  Future<Map<String, dynamic>> getViaje(int id) async {
    final res = await client.dio.get('/viajes/$id/');
    return res.data as Map<String, dynamic>;
  }

  /// Devuelve viaje + pisos_config con disponibilidad por celda.
  Future<({Viaje viaje, List<PisoConfig> pisos})> getAsientos(String viajeId) async {
    final res = await client.dio.get('/aerorutas/viajes/$viajeId/asientos/');
    final data = res.data as Map<String, dynamic>;
    final viaje = Viaje.fromJson(data['viaje'] as Map<String, dynamic>);
    final pisosRaw = (data['pisos_config'] ?? []) as List;
    final pisos = pisosRaw
        .whereType<Map<String, dynamic>>()
        .map(PisoConfig.fromJson)
        .toList();
    return (viaje: viaje, pisos: pisos);
  }

  Future<Map<String, dynamic>> getTasaCambio() async {
    final res = await client.dio.get('/tasa-cambio/');
    return res.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getConfiguracion() async {
    final res = await client.dio.get('/configuracion/');
    return res.data as Map<String, dynamic>;
  }
}
