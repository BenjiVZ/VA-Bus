class Banco {
  final String codigo;
  final String nombre;

  Banco({required this.codigo, required this.nombre});

  factory Banco.fromJson(Map<String, dynamic> json) => Banco(
        codigo: (json['codigo'] ?? '') as String,
        nombre: (json['nombre'] ?? '') as String,
      );
}
