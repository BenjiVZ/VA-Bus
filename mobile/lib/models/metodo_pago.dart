class DatoMetodoPago {
  final String etiqueta;
  final String valor;

  DatoMetodoPago({required this.etiqueta, required this.valor});

  factory DatoMetodoPago.fromJson(Map<String, dynamic> json) => DatoMetodoPago(
        etiqueta: (json['etiqueta'] ?? '') as String,
        valor: (json['valor'] ?? '') as String,
      );
}

class MetodoPago {
  final int id;
  final String nombre;
  final String tipo;
  final String moneda; // BS | USD
  final String descripcion;
  final bool requiereFotoBillete;
  final List<DatoMetodoPago> datos;

  MetodoPago({
    required this.id,
    required this.nombre,
    required this.tipo,
    required this.moneda,
    required this.descripcion,
    required this.requiereFotoBillete,
    required this.datos,
  });

  factory MetodoPago.fromJson(Map<String, dynamic> json) {
    final datosRaw = (json['datos'] ?? []) as List;
    return MetodoPago(
      id: json['id'] as int,
      nombre: (json['nombre'] ?? '') as String,
      tipo: (json['tipo'] ?? '') as String,
      moneda: (json['moneda'] ?? 'BS') as String,
      descripcion: (json['descripcion'] ?? '') as String,
      requiereFotoBillete: (json['requiere_foto_billete'] ?? false) as bool,
      datos: datosRaw
          .whereType<Map<String, dynamic>>()
          .map(DatoMetodoPago.fromJson)
          .toList(),
    );
  }
}
