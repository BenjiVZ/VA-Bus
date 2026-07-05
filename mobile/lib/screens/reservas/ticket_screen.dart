import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../../config/constants.dart';
import '../../config/theme.dart';
import '../../services/api_client.dart';
import '../../services/reservas_service.dart';
import '../../utils/format.dart';

class TicketScreen extends StatefulWidget {
  final String grupoPago;
  const TicketScreen({super.key, required this.grupoPago});

  @override
  State<TicketScreen> createState() => _TicketScreenState();
}

class _TicketScreenState extends State<TicketScreen> {
  bool _loading = true;
  String? _error;
  Map<String, dynamic>? _data;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final d = await context.read<ReservasService>().getTicket(widget.grupoPago);
      if (!mounted) return;
      setState(() {
        _data = d;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = ApiClient.extractError(e);
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.blue700,
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          onPressed: () => context.canPop() ? context.pop() : context.go('/mis-reservas'),
          icon: const Icon(Icons.arrow_back_rounded, color: Colors.white),
          style: IconButton.styleFrom(
            backgroundColor: Colors.white.withValues(alpha: 0.15),
          ),
        ),
        title: const Text(
          'Tu ticket',
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: Colors.white))
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(32),
                    child: Text(_error!,
                        style: const TextStyle(color: Colors.white),
                        textAlign: TextAlign.center),
                  ),
                )
              : _data == null
                  ? const SizedBox.shrink()
                  : _ticketView(),
    );
  }

  Widget _ticketView() {
    final d = _data!;
    final viaje = (d['viaje'] ?? {}) as Map<String, dynamic>;
    final tickets = (d['tickets'] ?? []) as List;
    final empresa = (d['empresa'] ?? 'Aerorutas') as String;
    final origen = (viaje['origen'] ?? '') as String;
    final destino = (viaje['destino'] ?? '') as String;
    final fecha = (viaje['fecha_salida'] ?? '') as String;
    final hora = (viaje['hora_salida'] ?? '') as String;
    final autobus = (viaje['autobus'] ?? '') as String;
    final esIdaVuelta = viaje['tipo_viaje'] == 'ida_vuelta';

    return ListView(
      padding: EdgeInsets.fromLTRB(20, MediaQuery.of(context).padding.top + 70, 20, 24),
      children: [
        // Confirmación
        Center(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: BoxDecoration(
              color: AppColors.green500.withValues(alpha: 0.18),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.green500.withValues(alpha: 0.4)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: const [
                Icon(Icons.check_circle_rounded, color: Color(0xFF6FE7AC), size: 18),
                SizedBox(width: 6),
                Text(
                  'PAGO CONFIRMADO',
                  style: TextStyle(
                    color: Color(0xFF6FE7AC),
                    fontWeight: FontWeight.w800,
                    fontSize: 12,
                    letterSpacing: 1,
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        Center(
          child: Text(
            empresa.toUpperCase(),
            style: const TextStyle(
              color: Colors.white60,
              fontSize: 11,
              letterSpacing: 2,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        const SizedBox(height: 6),
        Center(
          child: Text(
            '$origen ${esIdaVuelta ? '⇄' : '→'} $destino',
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 22,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.5,
            ),
          ),
        ),
        const SizedBox(height: 24),
        for (final t in tickets)
          _BoardingPass(
            ticket: t as Map<String, dynamic>,
            origen: origen,
            destino: destino,
            fecha: fecha,
            hora: hora,
            autobus: autobus,
            esIdaVuelta: esIdaVuelta,
          ),
      ],
    );
  }
}

/* ══════════════════════════════════════════════
   Boarding pass — estilo tarjeta de embarque
   con muescas semicirculares en los lados.
   ══════════════════════════════════════════════ */
class _BoardingPass extends StatelessWidget {
  final Map<String, dynamic> ticket;
  final String origen;
  final String destino;
  final String fecha;
  final String hora;
  final String autobus;
  final bool esIdaVuelta;

  const _BoardingPass({
    required this.ticket,
    required this.origen,
    required this.destino,
    required this.fecha,
    required this.hora,
    required this.autobus,
    required this.esIdaVuelta,
  });

  @override
  Widget build(BuildContext context) {
    final codigo = (ticket['codigo_ticket'] ?? '') as String;
    final asiento = ticket['numero_asiento'];
    final piso = ticket['piso_asiento'];
    final nombre = (ticket['nombre_pasajero'] ?? '') as String;
    final cedula = (ticket['cedula_pasajero'] ?? '') as String;
    final paraOtra = (ticket['para_otra_persona'] ?? false) as bool;
    final asignado = (ticket['nombre_asignado'] ?? '') as String;
    final qrUrl = '${AppConfig.apiOrigin}/verificar/$codigo';

    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: ClipPath(
        clipper: _BoardingPassClipper(),
        child: Container(
          decoration: BoxDecoration(
            color: Colors.white,
            boxShadow: AppShadows.lg,
          ),
          child: Column(
            children: [
              // Top: gradiente con info principal
              Container(
                padding: const EdgeInsets.all(20),
                decoration: const BoxDecoration(
                  gradient: AppColors.heroGradient,
                ),
                child: Column(
                  children: [
                    // Ruta XL
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'DESDE',
                                style: TextStyle(
                                  color: Colors.white60,
                                  fontSize: 10,
                                  letterSpacing: 1.5,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                origen,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 20,
                                  fontWeight: FontWeight.w800,
                                  height: 1.1,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6),
                          child: Icon(
                            esIdaVuelta ? Icons.compare_arrows_rounded : Icons.flight_takeoff_rounded,
                            color: AppColors.yellow400,
                            size: 24,
                          ),
                        ),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              const Text(
                                'HACIA',
                                style: TextStyle(
                                  color: Colors.white60,
                                  fontSize: 10,
                                  letterSpacing: 1.5,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                destino,
                                textAlign: TextAlign.right,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 20,
                                  fontWeight: FontWeight.w800,
                                  height: 1.1,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
                    Container(height: 1, color: Colors.white24),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        Expanded(child: _miniField('FECHA', _fmtFecha(fecha))),
                        Expanded(child: _miniField('HORA', _hora(hora))),
                        Expanded(child: _miniField('ASIENTO', '#$asiento')),
                      ],
                    ),
                  ],
                ),
              ),
              // Línea perforada
              const _DashedDivider(),
              // QR + datos pasajero
              Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: AppColors.borderStandard, width: 2),
                          ),
                          child: QrImageView(
                            data: qrUrl,
                            version: QrVersions.auto,
                            size: 100,
                            backgroundColor: Colors.white,
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'PASAJERO',
                                style: TextStyle(
                                  fontSize: 10,
                                  letterSpacing: 1.5,
                                  fontWeight: FontWeight.w700,
                                  color: AppColors.textMuted,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                paraOtra && asignado.isNotEmpty ? asignado : nombre,
                                style: const TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w800,
                                  color: AppColors.textPrimary,
                                  height: 1.2,
                                ),
                              ),
                              if (cedula.isNotEmpty) ...[
                                const SizedBox(height: 4),
                                Text(
                                  'C.I. $cedula',
                                  style: const TextStyle(
                                    fontSize: 12,
                                    color: AppColors.textTertiary,
                                  ),
                                ),
                              ],
                              const SizedBox(height: 8),
                              if (autobus.isNotEmpty)
                                Row(
                                  children: [
                                    const Icon(Icons.directions_bus_rounded,
                                        size: 14, color: AppColors.blue500),
                                    const SizedBox(width: 4),
                                    Expanded(
                                      child: Text(
                                        autobus,
                                        style: const TextStyle(
                                          fontSize: 12,
                                          fontWeight: FontWeight.w600,
                                          color: AppColors.blue500,
                                        ),
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                  ],
                                ),
                              Padding(
                                padding: const EdgeInsets.only(top: 4),
                                child: Text(
                                  'Piso $piso',
                                  style: const TextStyle(
                                    fontSize: 11,
                                    color: AppColors.textMuted,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      decoration: BoxDecoration(
                        color: AppColors.gray50,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: AppColors.borderSubtle),
                      ),
                      child: Column(
                        children: [
                          const Text(
                            'CÓDIGO DE TICKET',
                            style: TextStyle(
                              fontSize: 9,
                              letterSpacing: 1.5,
                              fontWeight: FontWeight.w700,
                              color: AppColors.textMuted,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            codigo,
                            style: const TextStyle(
                              fontFamily: 'Courier',
                              fontSize: 22,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 6,
                              color: AppColors.blue700,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),
                    const Text(
                      'Muestra este QR al abordar',
                      style: TextStyle(
                        fontSize: 11,
                        color: AppColors.textMuted,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _miniField(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style: const TextStyle(
              color: Colors.white60,
              fontSize: 9,
              letterSpacing: 1.5,
              fontWeight: FontWeight.w700,
            )),
        const SizedBox(height: 3),
        Text(value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.w800,
            )),
      ],
    );
  }

  String _fmtFecha(String iso) {
    try {
      final d = DateTime.parse(iso);
      return '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}';
    } catch (_) {
      return iso;
    }
  }

  String _hora(String hms) => horaAmPm(hms);
}

/// Clipper que recorta las muescas semicirculares en los costados
class _BoardingPassClipper extends CustomClipper<Path> {
  final double notchRadius;
  final double notchOffset;

  _BoardingPassClipper({this.notchRadius = 12, this.notchOffset = 188});

  @override
  Path getClip(Size size) {
    const corner = 20.0;
    final path = Path();
    path.moveTo(corner, 0);
    path.lineTo(size.width - corner, 0);
    path.arcToPoint(Offset(size.width, corner), radius: const Radius.circular(corner));
    path.lineTo(size.width, notchOffset - notchRadius);
    path.arcToPoint(
      Offset(size.width, notchOffset + notchRadius),
      radius: Radius.circular(notchRadius),
      clockwise: false,
    );
    path.lineTo(size.width, size.height - corner);
    path.arcToPoint(Offset(size.width - corner, size.height), radius: const Radius.circular(corner));
    path.lineTo(corner, size.height);
    path.arcToPoint(Offset(0, size.height - corner), radius: const Radius.circular(corner));
    path.lineTo(0, notchOffset + notchRadius);
    path.arcToPoint(
      Offset(0, notchOffset - notchRadius),
      radius: Radius.circular(notchRadius),
      clockwise: false,
    );
    path.lineTo(0, corner);
    path.arcToPoint(Offset(corner, 0), radius: const Radius.circular(corner));
    path.close();
    return path;
  }

  @override
  bool shouldReclip(_) => false;
}

class _DashedDivider extends StatelessWidget {
  const _DashedDivider();

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (_, c) {
        const dashWidth = 6.0;
        const dashSpace = 4.0;
        final count = (c.maxWidth / (dashWidth + dashSpace)).floor();
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: List.generate(
              count,
              (_) => Container(
                width: dashWidth, height: 1.5,
                color: AppColors.borderStandard,
              ),
            ),
          ),
        );
      },
    );
  }
}
