class Reserva {
  final int id;
  final int viajeId;
  final int numeroAsiento;
  final int pisoAsiento;
  final String estado; // pendiente | apartado | confirmado | cancelado
  final String? codigoTicket;
  final String? grupoPago;
  final String nombrePasajero;
  final String cedulaPasajero;
  final bool esMenorEdad;
  final bool paraOtraPersona;
  final String nombreAsignado;
  final String cedulaAsignado;
  final bool viajaConAnimal;
  final String tipoMascota;
  final bool esDiscapacitado;
  final String? fechaExpiracion;
  // Datos del viaje (cuando vienen anidados)
  final String? rutaOrigen;
  final String? rutaDestino;
  final String? fechaSalida;
  final String? horaSalida;
  final String? autobusNombre;
  final double? precioUsd;

  Reserva({
    required this.id,
    required this.viajeId,
    required this.numeroAsiento,
    required this.pisoAsiento,
    required this.estado,
    this.codigoTicket,
    this.grupoPago,
    required this.nombrePasajero,
    required this.cedulaPasajero,
    required this.esMenorEdad,
    required this.paraOtraPersona,
    required this.nombreAsignado,
    required this.cedulaAsignado,
    required this.viajaConAnimal,
    required this.tipoMascota,
    required this.esDiscapacitado,
    this.fechaExpiracion,
    this.rutaOrigen,
    this.rutaDestino,
    this.fechaSalida,
    this.horaSalida,
    this.autobusNombre,
    this.precioUsd,
  });

  bool get esConfirmada => estado == 'confirmado';
  bool get esPendiente => estado == 'pendiente';
  bool get esApartada => estado == 'apartado';

  factory Reserva.fromJson(Map<String, dynamic> json) {
    final viaje = json['viaje'];
    // El backend (ReservaSerializer) expone los datos del viaje en
    // `viaje_info` como objeto plano. Algunos endpoints alternativos
    // (admin, detalle) los devuelven anidados en `viaje.ruta`/`viaje.autobus`,
    // así que soportamos ambos formatos.
    final viajeInfo = json['viaje_info'];
    String? origen, destino, fecha, hora, busNombre;
    double? precio;
    int? viajeIdResolved;

    if (viajeInfo is Map<String, dynamic>) {
      origen = viajeInfo['origen'] as String?;
      destino = viajeInfo['destino'] as String?;
      fecha = viajeInfo['fecha_salida']?.toString();
      hora = viajeInfo['hora_salida']?.toString();
      final bus = viajeInfo['autobus'];
      busNombre = bus is String ? bus : (bus is Map ? bus['nombre'] as String? : null);
      final p = viajeInfo['precio_usd'];
      if (p is num) {
        precio = p.toDouble();
      } else if (p is String) {
        precio = double.tryParse(p);
      }
      viajeIdResolved = viajeInfo['id'] as int?;
    } else if (viaje is Map<String, dynamic>) {
      final ruta = viaje['ruta'];
      if (ruta is Map<String, dynamic>) {
        origen = ruta['origen'] as String?;
        destino = ruta['destino'] as String?;
      }
      final bus = viaje['autobus'];
      if (bus is Map<String, dynamic>) {
        busNombre = bus['nombre'] as String?;
      }
      fecha = viaje['fecha_salida']?.toString();
      hora = viaje['hora_salida']?.toString();
      final p = viaje['precio_usd'];
      if (p is num) {
        precio = p.toDouble();
      } else if (p is String) {
        precio = double.tryParse(p);
      }
      viajeIdResolved = viaje['id'] as int?;
    }

    // viaje puede ser un int plano (FK directo del ModelSerializer).
    final viajeIdFromFk = viaje is int ? viaje : null;

    return Reserva(
      id: json['id'] as int,
      viajeId: (json['viaje_id'] ?? viajeIdResolved ?? viajeIdFromFk ?? 0) as int,
      numeroAsiento: (json['numero_asiento'] ?? 0) as int,
      pisoAsiento: (json['piso_asiento'] ?? 1) as int,
      estado: (json['estado'] ?? 'pendiente') as String,
      codigoTicket: json['codigo_ticket'] as String?,
      grupoPago: json['grupo_pago']?.toString(),
      nombrePasajero: (json['nombre_pasajero'] ?? '') as String,
      cedulaPasajero: (json['cedula_pasajero'] ?? '') as String,
      esMenorEdad: (json['es_menor_edad'] ?? false) as bool,
      paraOtraPersona: (json['para_otra_persona'] ?? false) as bool,
      nombreAsignado: (json['nombre_asignado'] ?? '') as String,
      cedulaAsignado: (json['cedula_asignado'] ?? '') as String,
      viajaConAnimal: (json['viaja_con_animal'] ?? false) as bool,
      tipoMascota: (json['tipo_mascota'] ?? '') as String,
      esDiscapacitado: (json['es_discapacitado'] ?? false) as bool,
      fechaExpiracion: json['fecha_expiracion'] as String?,
      rutaOrigen: origen,
      rutaDestino: destino,
      fechaSalida: fecha,
      horaSalida: hora,
      autobusNombre: busNombre,
      precioUsd: precio,
    );
  }
}
