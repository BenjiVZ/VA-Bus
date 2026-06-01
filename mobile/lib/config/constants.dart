import 'package:flutter/foundation.dart' show kIsWeb;

/// Configuración global de la app.
///
/// Resuelve la URL del backend (Django/daphne, puerto 5002) según el entorno:
///   1. --dart-define=API_BASE_URL=...  (override explícito)
///   2. Web en *.masterslogic.com  -> https://5002.masterslogic.com/api
///   3. Web local (p.ej. localhost:5003) -> http://<host>:5002/api
///   4. App nativa (APK/iOS) -> dominio público 5002.masterslogic.com
///
/// Para desarrollo local en emulador Android usa --dart-define:
///   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:5002/api
class AppConfig {
  /// URL base del backend Django. Sin barra final.
  static String get apiBaseUrl {
    const fromDefine = String.fromEnvironment('API_BASE_URL', defaultValue: '');
    if (fromDefine.isNotEmpty) return fromDefine;

    if (kIsWeb) {
      final host = Uri.base.host; // p.ej. 5003.masterslogic.com o localhost
      if (host.endsWith('.masterslogic.com')) {
        return 'https://5002.masterslogic.com/api';
      }
      // Web local / IP de red: mismo host, puerto 5002.
      return 'http://$host:5002/api';
    }

    // App nativa: usa el dominio público del backend.
    return 'https://5002.masterslogic.com/api';
  }

  /// Origen del backend (sin /api) para resolver URLs de archivos /media/*.
  static String get apiOrigin {
    final base = apiBaseUrl;
    return base.endsWith('/api') ? base.substring(0, base.length - 4) : base;
  }

  /// Google OAuth Client ID — déjalo vacío para deshabilitar Google Sign-In.
  static const String googleClientId = String.fromEnvironment('GOOGLE_CLIENT_ID');

  static const String appName = 'Aerorutas de Venezuela';
  static const String appShortName = 'Aerorutas';
}

/// Resuelve una ruta relativa del backend (/media/*) a URL absoluta.
String resolveApiFileUrl(String? path) {
  if (path == null || path.isEmpty) return '';
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  final normalized = path.startsWith('/') ? path : '/$path';
  return '${AppConfig.apiOrigin}$normalized';
}
