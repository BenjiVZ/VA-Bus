// Utilidades de formato compartidas por toda la app.

/// Convierte una hora en formato 24h ("HH:MM" o "HH:MM:SS") a formato de
/// 12 horas con meridiano: "8:00 a. m." / "2:30 p. m.".
///
/// Devuelve '—' si la entrada es nula o vacía, y la entrada original tal cual
/// si no tiene el formato esperado (defensivo, nunca lanza).
String horaAmPm(String? hms) {
  if (hms == null || hms.isEmpty) return '—';
  final parts = hms.split(':');
  if (parts.length < 2) return hms;
  final h = int.tryParse(parts[0]);
  final m = int.tryParse(parts[1]);
  if (h == null || m == null || h < 0 || h > 23 || m < 0 || m > 59) return hms;

  final periodo = h < 12 ? 'a. m.' : 'p. m.';
  var h12 = h % 12;
  if (h12 == 0) h12 = 12; // 00 y 12 → 12
  final mm = m.toString().padLeft(2, '0');
  return '$h12:$mm $periodo';
}
