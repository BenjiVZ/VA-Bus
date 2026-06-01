import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../../config/theme.dart';
import '../../models/viaje.dart';
import '../../services/api_client.dart';
import '../../services/viajes_service.dart';
import '../../widgets/skeleton_card.dart';
import '../shell.dart';

class ViajesListScreen extends StatefulWidget {
  final String? origen;
  final String? destino;
  final String? fecha;
  const ViajesListScreen({super.key, this.origen, this.destino, this.fecha});

  @override
  State<ViajesListScreen> createState() => _ViajesListScreenState();
}

class _ViajesListScreenState extends State<ViajesListScreen> {
  bool _loading = true;
  List<Viaje> _viajes = [];
  String? _error;

  @override
  void initState() {
    super.initState();
    _buscar();
  }

  Future<void> _buscar() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final viajes = await context.read<ViajesService>().buscarViajes(
            origen: widget.origen,
            destino: widget.destino,
            fecha: widget.fecha,
          );
      if (!mounted) return;
      setState(() {
        _viajes = viajes;
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

  String _formatFecha(String iso) {
    try {
      return DateFormat('EEE d MMM', 'es').format(DateTime.parse(iso));
    } catch (_) {
      return iso;
    }
  }

  @override
  Widget build(BuildContext context) {
    final hasFilters = widget.origen != null || widget.destino != null || widget.fecha != null;

    return Scaffold(
      backgroundColor: AppColors.bgSecondary,
      body: CustomScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          // Header con gradiente
          SliverToBoxAdapter(
            child: Container(
              padding: EdgeInsets.fromLTRB(
                20, MediaQuery.of(context).padding.top + 16, 20, 24,
              ),
              decoration: const BoxDecoration(
                gradient: AppColors.heroGradient,
                borderRadius: BorderRadius.vertical(
                  bottom: Radius.circular(28),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      IconButton(
                        onPressed: () => context.canPop() ? context.pop() : context.go('/'),
                        icon: const Icon(Icons.arrow_back_rounded, color: Colors.white),
                        style: IconButton.styleFrom(
                          backgroundColor: Colors.white.withValues(alpha: 0.15),
                        ),
                      ),
                      const SizedBox(width: 12),
                      const Text(
                        'Viajes disponibles',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                  if (hasFilters) ...[
                    const SizedBox(height: 18),
                    Wrap(
                      spacing: 8, runSpacing: 8,
                      children: [
                        if (widget.origen != null)
                          _filterChip(Icons.radio_button_checked_rounded, widget.origen!),
                        if (widget.destino != null)
                          _filterChip(Icons.location_on_rounded, widget.destino!),
                        if (widget.fecha != null)
                          _filterChip(Icons.calendar_today_rounded, _formatFecha(widget.fecha!)),
                      ],
                    ),
                  ],
                ],
              ),
            ),
          ),
          // Resumen + lista
          if (_loading)
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 20, 16, kFloatingNavHeight),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate(
                  (_, _) => const SkeletonCard(height: 180),
                  childCount: 4,
                ),
              ),
            )
          else if (_error != null)
            SliverFillRemaining(
              child: _ErrorView(message: _error!, onRetry: _buscar),
            )
          else if (_viajes.isEmpty)
            const SliverFillRemaining(child: _EmptyView())
          else ...[
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 20, 20, 12),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '${_viajes.length} ${_viajes.length == 1 ? 'viaje encontrado' : 'viajes encontrados'}',
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 15,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppColors.green50,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Row(
                        children: [
                          Container(
                            width: 6, height: 6,
                            decoration: const BoxDecoration(
                              color: AppColors.green500,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 6),
                          const Text(
                            'En vivo',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: AppColors.green500,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, kFloatingNavHeight),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate(
                  (ctx, i) => _ViajeCard(
                    viaje: _viajes[i],
                    fecha: _formatFecha(_viajes[i].fechaSalida),
                  )
                      .animate()
                      .fadeIn(duration: 320.ms, delay: (i * 70).ms)
                      .slideY(begin: 0.15, end: 0, curve: Curves.easeOutCubic),
                  childCount: _viajes.length,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _filterChip(IconData icon, String label) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.18),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.white.withValues(alpha: 0.2)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: Colors.white),
            const SizedBox(width: 6),
            Text(label,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                )),
          ],
        ),
      );
}

/* ── Trip card rediseñada: timeline vertical + precio destacado ── */
/* ── Trip card rediseñada: timeline vertical + precio destacado ── */
class _ViajeCard extends StatelessWidget {
  final Viaje viaje;
  final String fecha;
  const _ViajeCard({required this.viaje, required this.fecha});

  String _hora(String hms) => hms.length >= 5 ? hms.substring(0, 5) : hms;

  @override
  Widget build(BuildContext context) {
    final disponibles = viaje.asientosDisponibles;
    final agotado = disponibles <= 0;
    final pocos = !agotado && disponibles <= 5;
    final hora = _hora(viaje.horaSalida);

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          boxShadow: AppShadows.md,
          border: Border.all(color: const Color(0xFFF1F5F9)),
        ),
        child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(20),
          child: InkWell(
            borderRadius: BorderRadius.circular(20),
            onTap: agotado ? null : () => context.push('/viajes/${viaje.id}/asientos'),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Top: ruta + ida y vuelta badge
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppColors.blue50,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.calendar_today_rounded,
                                size: 11, color: AppColors.blue500),
                            const SizedBox(width: 4),
                            Text(fecha,
                                style: const TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w700,
                                  color: AppColors.blue500,
                                )),
                          ],
                        ),
                      ),
                      const SizedBox(width: 6),
                      if (viaje.esIdaYVuelta)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: AppColors.yellow50,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.compare_arrows_rounded,
                                  size: 11, color: AppColors.yellow600),
                              SizedBox(width: 4),
                              Text('IDA Y VUELTA',
                                  style: TextStyle(
                                    fontSize: 10,
                                    fontWeight: FontWeight.w800,
                                    color: AppColors.yellow600,
                                  )),
                            ],
                          ),
                        ),
                      const Spacer(),
                      Text(hora, style: AppMono.hour(color: AppColors.blue500)),
                    ],
                  ),
                ),
                // Timeline horizontal con puntos
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                  child: Row(
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            viaje.ruta?.origen ?? '?',
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w800,
                              color: AppColors.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 2),
                          const Text(
                            'Origen',
                            style: TextStyle(
                              fontSize: 11,
                              color: AppColors.textMuted,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                      Expanded(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 14),
                          child: Row(
                            children: [
                              Container(
                                width: 10, height: 10,
                                decoration: BoxDecoration(
                                  color: Colors.white,
                                  shape: BoxShape.circle,
                                  border: Border.all(color: AppColors.green500, width: 2.5),
                                  boxShadow: [
                                    BoxShadow(
                                      color: AppColors.green500.withValues(alpha: 0.15),
                                      blurRadius: 4,
                                      spreadRadius: 2,
                                    ),
                                  ],
                                ),
                              ),
                              Expanded(
                                child: CustomPaint(
                                  size: const Size(double.infinity, 1),
                                  painter: _DashedLinePainter(),
                                ),
                              ),
                              Container(
                                padding: const EdgeInsets.all(6),
                                decoration: BoxDecoration(
                                  color: AppColors.blue50,
                                  shape: BoxShape.circle,
                                  border: Border.all(color: const Color(0xFFC8D4E8), width: 1),
                                ),
                                child: const Icon(Icons.directions_bus_rounded,
                                    size: 14, color: AppColors.blue500),
                              ),
                              Expanded(
                                child: CustomPaint(
                                  size: const Size(double.infinity, 1),
                                  painter: _DashedLinePainter(),
                                ),
                              ),
                              Container(
                                width: 10, height: 10,
                                decoration: BoxDecoration(
                                  color: Colors.white,
                                  shape: BoxShape.circle,
                                  border: Border.all(color: AppColors.red500, width: 2.5),
                                  boxShadow: [
                                    BoxShadow(
                                      color: AppColors.red500.withValues(alpha: 0.15),
                                      blurRadius: 4,
                                      spreadRadius: 2,
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(
                            viaje.ruta?.destino ?? '?',
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w800,
                              color: AppColors.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 2),
                          const Text(
                            'Destino',
                            style: TextStyle(
                              fontSize: 11,
                              color: AppColors.textMuted,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const Divider(height: 1, color: AppColors.borderSubtle),
                // Footer: bus + asientos + precio
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                  child: Row(
                    children: [
                      const Icon(Icons.directions_bus_rounded,
                          size: 14, color: AppColors.textMuted),
                      const SizedBox(width: 4),
                      Flexible(
                        child: Text(
                          viaje.autobus?.nombre ?? '',
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppColors.textTertiary,
                            fontWeight: FontWeight.w500,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: agotado
                              ? AppColors.red50
                              : pocos
                                  ? AppColors.yellow50
                                  : AppColors.green50,
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          agotado
                              ? 'Agotado'
                              : pocos
                                  ? '¡Solo $disponibles!'
                                  : '$disponibles disponibles',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            color: agotado
                                ? AppColors.red500
                                : pocos
                                    ? AppColors.yellow600
                                    : AppColors.green500,
                          ),
                        ),
                      ),
                      const Spacer(),
                      RichText(
                        text: TextSpan(
                          children: [
                            TextSpan(
                              text: '\$',
                              style: AppMono.style(
                                fontSize: 14,
                                fontWeight: FontWeight.w700,
                                color: AppColors.blue500,
                              ),
                            ),
                            TextSpan(
                              text: viaje.precioUsd.toStringAsFixed(2),
                              style: AppMono.style(
                                fontSize: 22,
                                fontWeight: FontWeight.w800,
                                color: AppColors.blue500,
                                letterSpacing: -0.5,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _DashedLinePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFFCBD5E1) // clean slate border
      ..strokeWidth = 1.2;
    const dashWidth = 3.5;
    const dashSpace = 2.5;
    double startX = 0;
    while (startX < size.width) {
      canvas.drawLine(
        Offset(startX, 0),
        Offset(startX + dashWidth, 0),
        paint,
      );
      startX += dashWidth + dashSpace;
    }
  }

  @override
  bool shouldRepaint(_) => false;
}

class _EmptyView extends StatelessWidget {
  const _EmptyView();
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 100, height: 100,
              decoration: const BoxDecoration(
                color: AppColors.blue50,
                shape: BoxShape.circle,
              ),
              alignment: Alignment.center,
              child: const Icon(Icons.search_off_rounded,
                  size: 48, color: AppColors.blue500),
            ),
            const SizedBox(height: 20),
            const Text(
              'No encontramos viajes',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 6),
            const Text(
              'Intenta con otras fechas u otros destinos.',
              style: TextStyle(color: AppColors.textTertiary),
            ),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              icon: const Icon(Icons.tune_rounded),
              label: const Text('Cambiar búsqueda'),
              onPressed: () => context.canPop() ? context.pop() : context.go('/'),
            ),
          ],
        ),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorView({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 100, height: 100,
              decoration: const BoxDecoration(
                color: AppColors.red50,
                shape: BoxShape.circle,
              ),
              alignment: Alignment.center,
              child: const Icon(Icons.wifi_off_rounded,
                  size: 48, color: AppColors.red500),
            ),
            const SizedBox(height: 20),
            const Text(
              'Algo salió mal',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 6),
            Text(message,
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppColors.textTertiary)),
            const SizedBox(height: 20),
            OutlinedButton.icon(
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Reintentar'),
              onPressed: onRetry,
            ),
          ],
        ),
      ),
    );
  }
}

