import 'package:latlong2/latlong.dart';

/// Coordenadas de ciudades de Venezuela usadas como destino/origen en Aerorutas.
/// Las claves son las strings que vienen del backend `Ruta.origen` y `Ruta.destino`.
/// El matching es case-insensitive y tolerante a variaciones (Pto. Ordaz, Puerto Ordaz, etc.).
class VenezuelaCities {
  static const Map<String, LatLng> _coords = {
    // Capital y centro
    'caracas': LatLng(10.4806, -66.9036),
    'caracas la bandera': LatLng(10.4861, -66.9131),     // Terminal La Bandera
    'caracas (la bandera)': LatLng(10.4861, -66.9131),
    'la bandera': LatLng(10.4861, -66.9131),
    'la guaira': LatLng(10.6044, -66.9347),
    'los teques': LatLng(10.3417, -67.0411),
    'guarenas': LatLng(10.4756, -66.6122),
    'guatire': LatLng(10.4719, -66.5394),

    // Centro
    'valencia': LatLng(10.1620, -67.9999),
    'maracay': LatLng(10.2469, -67.5958),
    'la victoria': LatLng(10.2333, -67.3333),
    'turmero': LatLng(10.2294, -67.4733),
    'puerto cabello': LatLng(10.4730, -68.0125),

    // Occidente / andes
    'maracaibo': LatLng(10.6427, -71.6125),
    'merida': LatLng(8.5897, -71.1561),
    'mérida': LatLng(8.5897, -71.1561),
    'san cristobal': LatLng(7.7669, -72.2257),
    'san cristóbal': LatLng(7.7669, -72.2257),
    'barinas': LatLng(8.6238, -70.2078),
    'trujillo': LatLng(9.3676, -70.4346),
    'valera': LatLng(9.3252, -70.6079),
    'el vigía': LatLng(8.6225, -71.6473),
    'el vigia': LatLng(8.6225, -71.6473),
    'san antonio': LatLng(7.8127, -72.4527),         // Tachira - frontera
    'san antonio del tachira': LatLng(7.8127, -72.4527),

    // Oficinas Aerorutas adicionales (panamericana + Zulia + Trujillo)
    'caño sancudo': LatLng(9.7833, -71.8167),        // Zulia
    'cano sancudo': LatLng(9.7833, -71.8167),
    'socopo': LatLng(8.2391, -70.8203),              // Barinas
    'socopó': LatLng(8.2391, -70.8203),
    'santa barbara': LatLng(8.9594, -71.9189),       // Santa Barbara del Zulia
    'santa bárbara': LatLng(8.9594, -71.9189),
    'arapuey': LatLng(8.9842, -71.1839),             // Merida (Zona Panamericana)
    'tucani': LatLng(9.0639, -71.2278),              // Merida
    'tucaní': LatLng(9.0639, -71.2278),
    'el pinal': LatLng(7.6500, -71.9667),            // Tachira
    'monay': LatLng(9.2667, -70.5500),               // Trujillo
    'caja seca': LatLng(9.0506, -71.0392),           // Zulia
    'el cruze': LatLng(8.7833, -70.4500),            // por confirmar (Trujillo/Lara)
    'el cruce': LatLng(8.7833, -70.4500),
    'puerto piritu': LatLng(10.0625, -64.9778),      // Anzoategui
    'puerto píritu': LatLng(10.0625, -64.9778),

    // Llanos / centro-oeste
    'barquisimeto': LatLng(10.0678, -69.3473),
    'acarigua': LatLng(9.5567, -69.1958),
    'araure': LatLng(9.5806, -69.2400),
    'guanare': LatLng(9.0427, -69.7416),
    'san fernando de apure': LatLng(7.8939, -67.4789),
    'san fernando': LatLng(7.8939, -67.4789),
    'calabozo': LatLng(8.9242, -67.4258),

    // Falcón
    'coro': LatLng(11.3984, -69.6755),
    'punto fijo': LatLng(11.7068, -70.2076),

    // Oriente
    'barcelona': LatLng(10.1394, -64.6863),
    'puerto la cruz': LatLng(10.2127, -64.6328),
    'lechería': LatLng(10.2017, -64.6711),
    'lecheria': LatLng(10.2017, -64.6711),
    'cumaná': LatLng(10.4546, -64.1735),
    'cumana': LatLng(10.4546, -64.1735),
    'maturín': LatLng(9.7480, -63.1734),
    'maturin': LatLng(9.7480, -63.1734),
    'carúpano': LatLng(10.6628, -63.2375),
    'carupano': LatLng(10.6628, -63.2375),

    // Guayana / sur
    'puerto ordaz': LatLng(8.2899, -62.7167),
    'ciudad guayana': LatLng(8.3565, -62.6516),
    'ciudad bolívar': LatLng(8.1320, -63.5497),
    'ciudad bolivar': LatLng(8.1320, -63.5497),
    'el tigre': LatLng(8.8853, -64.2533),
    'puerto ayacucho': LatLng(5.6635, -67.6294),
    'tucupita': LatLng(9.0606, -62.0506),
  };

  /// Centro aproximado de Venezuela (fallback)
  static const LatLng venezuelaCenter = LatLng(8.5, -66.0);

  /// Busca las coordenadas de una ciudad. Tolerante a mayúsculas, espacios y tildes.
  /// Devuelve [venezuelaCenter] si no se encuentra.
  static LatLng resolve(String? cityName) {
    if (cityName == null || cityName.trim().isEmpty) return venezuelaCenter;
    final normalized = _normalize(cityName);

    // Match exacto
    final direct = _coords[normalized];
    if (direct != null) return direct;

    // Match parcial: busca claves que contengan el nombre
    for (final entry in _coords.entries) {
      if (entry.key.contains(normalized) || normalized.contains(entry.key)) {
        return entry.value;
      }
    }

    return venezuelaCenter;
  }

  /// ¿Existe esta ciudad en el catálogo?
  static bool isKnown(String? cityName) {
    if (cityName == null || cityName.trim().isEmpty) return false;
    final normalized = _normalize(cityName);
    if (_coords.containsKey(normalized)) return true;
    for (final key in _coords.keys) {
      if (key.contains(normalized) || normalized.contains(key)) return true;
    }
    return false;
  }

  static String _normalize(String s) {
    return s
        .toLowerCase()
        .trim()
        // Tildes
        .replaceAll('á', 'a')
        .replaceAll('é', 'e')
        .replaceAll('í', 'i')
        .replaceAll('ó', 'o')
        .replaceAll('ú', 'u')
        .replaceAll('ñ', 'n');
  }
}
