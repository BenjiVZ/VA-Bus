double _toDouble(dynamic v) {
  if (v == null) return 0.0;
  if (v is num) return v.toDouble();
  if (v is String) return double.tryParse(v) ?? 0.0;
  return 0.0;
}

class Ruta {
  final int id;
  final String origen;
  final String destino;
  final String duracionEstimada;

  Ruta({
    required this.id,
    required this.origen,
    required this.destino,
    required this.duracionEstimada,
  });

  factory Ruta.fromJson(Map<String, dynamic> json) => Ruta(
        id: (json['id'] ?? 0) as int,
        origen: (json['origen'] ?? '') as String,
        destino: (json['destino'] ?? '') as String,
        duracionEstimada: (json['duracion_estimada'] ?? '') as String,
      );
}

class Autobus {
  final int id;
  final String nombre;
  final String placa;
  final String? marca;
  final String? color;
  final int? anio;
  final int pisos;
  final int capacidadTotal;

  Autobus({
    required this.id,
    required this.nombre,
    required this.placa,
    this.marca,
    this.color,
    this.anio,
    required this.pisos,
    required this.capacidadTotal,
  });

  factory Autobus.fromJson(Map<String, dynamic> json) => Autobus(
        id: (json['id'] ?? 0) as int,
        nombre: (json['nombre'] ?? '') as String,
        placa: (json['placa'] ?? '') as String,
        marca: json['marca'] as String?,
        color: json['color'] as String?,
        anio: json['anio'] as int?,
        pisos: (json['pisos'] ?? 1) as int,
        capacidadTotal: (json['capacidad_total'] ?? 0) as int,
      );
}

class Viaje {
  final String id;
  final Ruta? ruta;
  final Autobus? autobus;
  final String tipoViaje; // 'ida' | 'ida_vuelta'
  final String fechaSalida; // YYYY-MM-DD
  final String horaSalida;  // HH:MM:SS
  final String? fechaVuelta;
  final String? horaVuelta;
  final double precioUsd;
  final int asientosDisponibles;
  final int? capacidadTotal;

  Viaje({
    required this.id,
    this.ruta,
    this.autobus,
    required this.tipoViaje,
    required this.fechaSalida,
    required this.horaSalida,
    this.fechaVuelta,
    this.horaVuelta,
    required this.precioUsd,
    required this.asientosDisponibles,
    this.capacidadTotal,
  });

  bool get esIdaYVuelta => tipoViaje == 'ida_vuelta';

  factory Viaje.fromJson(Map<String, dynamic> json) {
    final rutaJson = json['ruta'];
    final busJson = json['autobus'];
    return Viaje(
      id: (json['id'] ?? '').toString(),
      ruta: rutaJson is Map<String, dynamic> ? Ruta.fromJson(rutaJson) : null,
      autobus: busJson is Map<String, dynamic> ? Autobus.fromJson(busJson) : null,
      tipoViaje: (json['tipo_viaje'] ?? 'ida') as String,
      fechaSalida: (json['fecha_salida'] ?? '') as String,
      horaSalida: (json['hora_salida'] ?? '') as String,
      fechaVuelta: json['fecha_vuelta'] as String?,
      horaVuelta: json['hora_vuelta'] as String?,
      precioUsd: _toDouble(json['precio_usd']),
      asientosDisponibles: (json['asientos_disponibles'] ?? 0) as int,
      capacidadTotal: json['capacidad_total'] as int?,
    );
  }
}

class PisoConfig {
  final int numeroPiso;
  final int filas;
  final int columnas;
  final List<List<Map<String, dynamic>>> layout;
  final int capacidad;

  PisoConfig({
    required this.numeroPiso,
    required this.filas,
    required this.columnas,
    required this.layout,
    required this.capacidad,
  });

  factory PisoConfig.fromJson(Map<String, dynamic> json) {
    final raw = (json['layout'] ?? []) as List;
    final layout = raw.map((row) {
      final r = row as List;
      return r.map((cell) {
        if (cell is Map) {
          return cell.map((k, v) => MapEntry(k.toString(), v));
        }
        return <String, dynamic>{'type': 'empty'};
      }).toList();
    }).toList();

    return PisoConfig(
      numeroPiso: (json['numero_piso'] ?? 1) as int,
      filas: (json['filas'] ?? 0) as int,
      columnas: (json['columnas'] ?? 5) as int,
      layout: layout,
      capacidad: (json['capacidad'] ?? 0) as int,
    );
  }
}
