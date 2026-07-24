import 'package:flutter/foundation.dart' show kIsWeb;

/// Configuración global de la app.
///
/// Dominio público del backend en producción (DigitalOcean + Cloudflare Tunnel).
/// El backend se sirve en el MISMO dominio bajo /api (y /ws para WebSockets).
const String kProdApiBaseUrl = 'https://aerorutasdevenezuela.net/api';

/// Resuelve la URL del backend (Django/daphne) según el entorno:
///   1. --dart-define=API_BASE_URL=...  (override explícito)
///   2. Web local (localhost / IP) -> http://HOST:5002/api
///   3. Web en producción -> https://HOST/api (mismo dominio, Cloudflare Tunnel)
///   4. App nativa (APK/iOS) -> https://aerorutasdevenezuela.net/api
///
/// Para desarrollo local en emulador Android usa --dart-define:
///   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:5002/api
class AppConfig {
  /// URL base del backend Django. Sin barra final.
  static String get apiBaseUrl {
    const fromDefine = String.fromEnvironment('API_BASE_URL', defaultValue: '');
    if (fromDefine.isNotEmpty) return fromDefine;

    if (kIsWeb) {
      final host = Uri.base.host; // p.ej. aerorutasdevenezuela.net o localhost
      final esLocal = host == 'localhost' ||
          host == '127.0.0.1' ||
          RegExp(r'^\d{1,3}(\.\d{1,3}){3}$').hasMatch(host);
      if (esLocal) {
        // Desarrollo local: mismo host, puerto 5002 (sin HTTPS).
        return 'http://$host:5002/api';
      }
      // Web de PRUEBA (se sirve por un túnel aparte, no desde el dominio del
      // backend): apunta siempre al backend real. Requiere que ese origen esté
      // en CORS_ALLOWED_ORIGINS del backend.
      return kProdApiBaseUrl;
    }

    // App nativa (APK/iOS): usa el dominio público del backend.
    return kProdApiBaseUrl;
  }

  /// Origen del backend (sin /api) para resolver URLs de archivos /media/*.
  static String get apiOrigin {
    final base = apiBaseUrl;
    return base.endsWith('/api') ? base.substring(0, base.length - 4) : base;
  }

  /// Google OAuth **Web** Client ID (el mismo con el que valida el backend
  /// Django). Con esto el botón "Continuar con Google" aparece siempre, sin
  /// tener que pasar --dart-define al compilar.
  ///
  /// ⚠️ Pegá aquí el Web Client ID (termina en `.apps.googleusercontent.com`).
  /// Es público (va embebido en la app), no es un secreto. Vacío = Google
  /// Sign-In deshabilitado (el botón se oculta).
  static const String _googleClientIdDefault =
      '941001553573-u64s6mjms1jtlk0v5agsrk5qq6bbvoat.apps.googleusercontent.com';

  /// Override opcional al compilar: --dart-define=GOOGLE_CLIENT_ID=xxx
  static const String _googleClientIdEnv =
      String.fromEnvironment('GOOGLE_CLIENT_ID');

  /// Client ID efectivo: gana el --dart-define; si no, el valor por defecto.
  static String get googleClientId =>
      _googleClientIdEnv.isNotEmpty ? _googleClientIdEnv : _googleClientIdDefault;

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
