import 'package:flutter/foundation.dart' show kIsWeb;

/// Configuración global de la app.
///
/// Por defecto apunta al tunnel de Cloudflare del backend,
/// igual que el frontend web (ardvb.aplicacionesdamasco.com).
///
/// Para desarrollo local, pasar la URL vía --dart-define:
///   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8001/api   (emulador Android)
///   flutter run --dart-define=API_BASE_URL=http://localhost:8001/api    (web/desktop)
class AppConfig {
  /// URL base del backend Django. Sin barra final.
  static String get apiBaseUrl {
    const fromDefine = String.fromEnvironment('API_BASE_URL', defaultValue: '');
    if (fromDefine.isNotEmpty) return fromDefine;
    // Tunnel de Cloudflare — mismo que el frontend
    return 'https://ardvb.aplicacionesdamasco.com/api';
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
