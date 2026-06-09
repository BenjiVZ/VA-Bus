import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:image_picker/image_picker.dart' show XFile;

import '../models/banco.dart';
import '../models/metodo_pago.dart';
import 'api_client.dart';

class PagosService {
  final ApiClient client;
  PagosService(this.client);

  Future<List<MetodoPago>> getMetodosPago() async {
    final res = await client.dio.get('/metodos-pago/');
    final data = res.data as List;
    return data
        .whereType<Map<String, dynamic>>()
        .map(MetodoPago.fromJson)
        .toList();
  }

  Future<Map<String, dynamic>> crearComprobante({
    required String grupoPago,
    required int metodoPagoId,
    required String numeroReferencia,
    required double monto,
    required String moneda, // 'BS' | 'USD'
    required XFile imagen,
    XFile? fotoBillete,
  }) async {
    final form = FormData.fromMap({
      'grupo_pago': grupoPago,
      'metodo_pago_id': metodoPagoId,
      'numero_referencia': numeroReferencia,
      'monto': monto,
      'moneda': moneda,
      'imagen': await _asMultipart(imagen),
      if (fotoBillete != null)
        'foto_billete': await _asMultipart(fotoBillete),
    });
    final res = await client.dio.post(
      '/comprobantes/',
      data: form,
      options: Options(contentType: 'multipart/form-data'),
    );
    if (res.statusCode == null || res.statusCode! >= 400) {
      throw DioException(requestOptions: res.requestOptions, response: res);
    }
    return res.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getEstadoComprobante(String grupoPago) async {
    final res = await client.dio.get('/comprobantes/$grupoPago/');
    return res.data as Map<String, dynamic>;
  }

  // ── R4 Conecta — Cobro Inmediato (Débito con OTP) ──

  /// Lista centralizada de bancos (fuente única del backend).
  Future<List<Banco>> getBancos() async {
    final res = await client.dio.get('/r4/bancos/');
    final data = res.data as List;
    return data.whereType<Map<String, dynamic>>().map(Banco.fromJson).toList();
  }

  /// Paso 1: pide al banco que envíe un OTP al teléfono del cliente.
  /// Devuelve el cuerpo tal cual (incluye `otp_enviado`, `operacion_id`, `monto`).
  Future<Map<String, dynamic>> r4GenerarOtp({
    required String grupoPago,
    required String banco,
    required String cedula,
    required String telefono,
    required String nombre,
    required String concepto,
  }) async {
    final res = await client.dio.post('/r4/debito/generar-otp/', data: {
      'grupo_pago': grupoPago,
      'banco': banco,
      'cedula': cedula,
      'telefono': telefono,
      'nombre': nombre,
      'concepto': concepto,
    });
    return res.data as Map<String, dynamic>;
  }

  /// Paso 2: confirma el débito con el OTP (+ comprobante opcional).
  Future<Map<String, dynamic>> r4ConfirmarDebito({
    required int operacionId,
    required String otp,
    XFile? comprobante,
  }) async {
    final form = FormData.fromMap({
      'operacion_id': operacionId,
      'otp': otp,
      if (comprobante != null) 'comprobante': await _asMultipart(comprobante),
    });
    final res = await client.dio.post(
      '/r4/debito/confirmar/',
      data: form,
      options: Options(contentType: 'multipart/form-data'),
    );
    if (res.statusCode == null || res.statusCode! >= 400) {
      throw DioException(requestOptions: res.requestOptions, response: res);
    }
    return res.data as Map<String, dynamic>;
  }

  /// Estado de una operación (para polling mientras queda "en espera").
  Future<Map<String, dynamic>> r4EstadoOperacion(int operacionId) async {
    final res = await client.dio.get('/r4/debito/$operacionId/');
    return res.data as Map<String, dynamic>;
  }
}

/// Construye un MultipartFile cross-platform desde un XFile.
/// En Web `path` no es un archivo real, así que hay que leer los bytes.
/// En IO también funciona pero `fromFile` es más eficiente cuando hay path.
Future<MultipartFile> _asMultipart(XFile f) async {
  if (kIsWeb) {
    final bytes = await f.readAsBytes();
    return MultipartFile.fromBytes(bytes, filename: f.name);
  }
  return MultipartFile.fromFile(f.path, filename: f.name);
}
