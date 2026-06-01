class Usuario {
  final int id;
  final String username;
  final String email;
  final String firstName;
  final String lastName;
  final String? cedula;
  final String? telefono;
  final String? fechaNacimiento;
  final bool emailVerificado;
  final bool isStaff;
  final bool esVip;
  final String servicioVip;

  Usuario({
    required this.id,
    required this.username,
    required this.email,
    required this.firstName,
    required this.lastName,
    this.cedula,
    this.telefono,
    this.fechaNacimiento,
    required this.emailVerificado,
    required this.isStaff,
    required this.esVip,
    required this.servicioVip,
  });

  String get fullName {
    final name = '$firstName $lastName'.trim();
    return name.isEmpty ? username : name;
  }

  factory Usuario.fromJson(Map<String, dynamic> json) {
    return Usuario(
      id: json['id'] as int,
      username: (json['username'] ?? '') as String,
      email: (json['email'] ?? '') as String,
      firstName: (json['first_name'] ?? '') as String,
      lastName: (json['last_name'] ?? '') as String,
      cedula: json['cedula'] as String?,
      telefono: json['telefono'] as String?,
      fechaNacimiento: json['fecha_nacimiento'] as String?,
      emailVerificado: (json['email_verificado'] ?? false) as bool,
      isStaff: (json['is_staff'] ?? false) as bool,
      esVip: (json['es_vip'] ?? false) as bool,
      servicioVip: (json['servicio_vip'] ?? 'ninguno') as String,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'username': username,
        'email': email,
        'first_name': firstName,
        'last_name': lastName,
        'cedula': cedula,
        'telefono': telefono,
        'fecha_nacimiento': fechaNacimiento,
        'email_verificado': emailVerificado,
        'is_staff': isStaff,
        'es_vip': esVip,
        'servicio_vip': servicioVip,
      };
}
