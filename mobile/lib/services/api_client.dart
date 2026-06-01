import 'package:dio/dio.dart';
import '../config/constants.dart';
import 'storage_service.dart';

typedef OnAuthLost = void Function();

/// Cliente HTTP centralizado.
/// Espeja el comportamiento de frontend/src/services/api.js:
/// - Inyecta Authorization: Bearer <access>
/// - Si la respuesta es 401, intenta refrescar el token una vez
/// - Si el refresh falla, llama a [onAuthLost] (el AuthProvider hará logout)
class ApiClient {
  final Dio dio;
  final StorageService storage;
  OnAuthLost? onAuthLost;

  ApiClient({required this.storage, this.onAuthLost})
      : dio = Dio(BaseOptions(
          baseUrl: AppConfig.apiBaseUrl,
          connectTimeout: const Duration(seconds: 20),
          receiveTimeout: const Duration(seconds: 30),
          headers: {'Content-Type': 'application/json'},
          validateStatus: (s) => s != null && s < 500,
        )) {
    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await storage.getAccessToken();
        if (token != null && token.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onResponse: (response, handler) async {
        // Intercept 401 manualmente — `validateStatus` deja pasar <500.
        if (response.statusCode == 401 &&
            response.requestOptions.extra['_retried'] != true) {
          final refreshed = await _tryRefresh();
          if (refreshed) {
            response.requestOptions.extra['_retried'] = true;
            try {
              final retried = await dio.fetch(response.requestOptions);
              return handler.resolve(retried);
            } catch (_) {
              // cae al else
            }
          }
          await storage.clearTokens();
          onAuthLost?.call();
        }
        handler.next(response);
      },
      onError: (err, handler) async {
        if (err.response?.statusCode == 401 &&
            err.requestOptions.extra['_retried'] != true) {
          final refreshed = await _tryRefresh();
          if (refreshed) {
            err.requestOptions.extra['_retried'] = true;
            try {
              final retried = await dio.fetch(err.requestOptions);
              return handler.resolve(retried);
            } catch (_) {}
          }
          await storage.clearTokens();
          onAuthLost?.call();
        }
        handler.next(err);
      },
    ));
  }

  Future<bool> _tryRefresh() async {
    final refresh = await storage.getRefreshToken();
    if (refresh == null || refresh.isEmpty) return false;
    try {
      final res = await Dio(BaseOptions(baseUrl: AppConfig.apiBaseUrl)).post(
        '/auth/refresh/',
        data: {'refresh': refresh},
      );
      final newAccess = res.data['access'] as String?;
      if (newAccess != null) {
        await storage.saveAccessToken(newAccess);
        return true;
      }
    } catch (_) {}
    return false;
  }

  /// Extrae un mensaje legible de error desde la respuesta del backend.
  static String extractError(Object e, {String fallback = 'Error desconocido.'}) {
    if (e is DioException) {
      final data = e.response?.data;
      if (data is Map) {
        if (data['error'] is String) return data['error'] as String;
        if (data['detail'] is String) return data['detail'] as String;
        if (data['mensaje'] is String) return data['mensaje'] as String;
        final detalles = data['detalles'];
        if (detalles is List && detalles.isNotEmpty) return detalles.join('\n');
        if (detalles is Map) {
          return detalles.values.expand((v) => v is List ? v : [v]).join('\n');
        }
      }
      if (e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.receiveTimeout) {
        return 'La conexión tardó demasiado. Verifica tu internet.';
      }
      if (e.type == DioExceptionType.connectionError) {
        return 'No se pudo conectar al servidor.';
      }
      return e.message ?? fallback;
    }
    return fallback;
  }
}
