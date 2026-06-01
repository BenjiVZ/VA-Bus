import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart' show kIsWeb;

import '../models/reserva.dart';
import 'api_client.dart';

class ReservasService {
  final ApiClient client;
  ReservasService(this.client);

  Future<Map<String, dynamic>> bloquearAsiento({
    required int viajeId,
    required int numeroAsiento,
    int pisoAsiento = 1,
  }) async {
    final res = await client.dio.post('/reservas/bloquear-asiento/', data: {
      'viaje_id': viajeId,
      'numero_asiento': numeroAsiento,
      'piso_asiento': pisoAsiento,
    });
    if (res.statusCode == null || res.statusCode! >= 400) {
      throw DioException(requestOptions: res.requestOptions, response: res);
    }
    return res.data as Map<String, dynamic>;
  }

  Future<void> liberarAsiento({
    required int viajeId,
    required int numeroAsiento,
    int pisoAsiento = 1,
  }) async {
    await client.dio.post('/reservas/liberar-asiento/', data: {
      'viaje_id': viajeId,
      'numero_asiento': numeroAsiento,
      'piso_asiento': pisoAsiento,
    });
  }

  /// Crea una orden con varios asientos. Devuelve el grupo_pago + lista de reservas creadas.
  Future<Map<String, dynamic>> crearReserva({
    required int viajeId,
    required List<Map<String, dynamic>> asientos,
    String nombrePasajero = '',
    String cedulaPasajero = '',
  }) async {
    final res = await client.dio.post('/reservas/', data: {
      'viaje_id': viajeId,
      'asientos': asientos,
      'nombre_pasajero': nombrePasajero,
      'cedula_pasajero': cedulaPasajero,
    });
    if (res.statusCode == null || res.statusCode! >= 400) {
      throw DioException(requestOptions: res.requestOptions, response: res);
    }
    return res.data as Map<String, dynamic>;
  }

  Future<List<Reserva>> getMisReservas() async {
    final res = await client.dio.get('/mis-reservas/');
    final body = res.data;
    final list = (body is Map && body['results'] is List)
        ? body['results'] as List
        : (body is List ? body : <dynamic>[]);
    return list.whereType<Map<String, dynamic>>().map(Reserva.fromJson).toList();
  }

  Future<Map<String, dynamic>> getTicket(String grupoPago) async {
    final res = await client.dio.get('/ticket/$grupoPago/');
    if (res.statusCode == null || res.statusCode! >= 400) {
      throw DioException(requestOptions: res.requestOptions, response: res);
    }
    return res.data as Map<String, dynamic>;
  }

  Future<void> subirDocumentosMenor({
    required int reservaId,
    required PlatformFile partida,
    required PlatformFile foto,
    required PlatformFile cedulaRep,
  }) async {
    final form = FormData.fromMap({
      'doc_partida_nacimiento': await _asMultipart(partida),
      'doc_foto_menor': await _asMultipart(foto),
      'doc_cedula_representante': await _asMultipart(cedulaRep),
    });
    final res = await client.dio.post(
      '/reservas/$reservaId/documentos-menor/',
      data: form,
      options: Options(contentType: 'multipart/form-data'),
    );
    if (res.statusCode == null || res.statusCode! >= 400) {
      throw DioException(requestOptions: res.requestOptions, response: res);
    }
  }

  Future<void> subirDocVacunacion({
    required int reservaId,
    required PlatformFile file,
  }) async {
    final form = FormData.fromMap({
      'doc_vacunacion_animal': await _asMultipart(file),
    });
    await client.dio.post(
      '/reservas/$reservaId/doc-vacunacion/',
      data: form,
      options: Options(contentType: 'multipart/form-data'),
    );
  }

  Future<void> subirDocDiscapacidad({
    required int reservaId,
    required PlatformFile file,
  }) async {
    final form = FormData.fromMap({
      'doc_discapacidad': await _asMultipart(file),
    });
    await client.dio.post(
      '/reservas/$reservaId/doc-discapacidad/',
      data: form,
      options: Options(contentType: 'multipart/form-data'),
    );
  }
}

/// Construye un MultipartFile cross-platform desde un PlatformFile.
/// En Web `path` es null y hay que usar `bytes` (file_picker los puebla
/// porque pasamos `withData: true` al picker).
Future<MultipartFile> _asMultipart(PlatformFile f) async {
  if (kIsWeb || f.path == null) {
    final bytes = f.bytes;
    if (bytes == null) {
      throw StateError(
        'PlatformFile sin bytes ni path. Asegurate de pasar withData: true al picker.',
      );
    }
    return MultipartFile.fromBytes(bytes, filename: f.name);
  }
  return MultipartFile.fromFile(f.path!, filename: f.name);
}
