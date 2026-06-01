import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../../config/theme.dart';
import '../../models/reserva.dart';
import '../../services/api_client.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../services/reservas_service.dart';
import '../../widgets/official_stamp.dart';
import '../../widgets/skeleton_card.dart';
import '../shell.dart';

class MisReservasScreen extends StatefulWidget {
  const MisReservasScreen({super.key});

  @override
  State<MisReservasScreen> createState() => _MisReservasScreenState();
}

class _MisReservasScreenState extends State<MisReservasScreen> {
  bool _loading = true;
  String? _error;
  List<Reserva> _reservas = [];
  String _filtro = 'todos'; // todos | proximos | pasados

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
      final r = await context.read<ReservasService>().getMisReservas();
      if (!mounted) return;
      setState(() {
        _reservas = r;
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

  Map<String, List<Reserva>> get _gruposFiltrados {
    final ahora = DateTime.now();
    final filtered = _reservas.where((r) {
      if (_filtro == 'todos') return true;
      try {
        final fecha = DateTime.parse(r.fechaSalida ?? '');
        final esProx = fecha.isAfter(ahora.subtract(const Duration(days: 1)));
        return _filtro == 'proximos' ? esProx : !esProx;
      } catch (_) {
        return _filtro == 'proximos';
      }
    });
    final out = <String, List<Reserva>>{};
    for (final r in filtered) {
      final key = r.grupoPago ?? 'sin_grupo_${r.id}';
      (out[key] ??= []).add(r);
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgSecondary,
      body: CustomScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          SliverToBoxAdapter(
            child: Container(
              padding: EdgeInsets.fromLTRB(
                20, MediaQuery.of(context).padding.top + 16, 20, 20,
              ),
              decoration: const BoxDecoration(
                gradient: AppColors.heroGradient,
                borderRadius: BorderRadius.vertical(bottom: Radius.circular(28)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Mis viajes',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 24,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.3,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${_reservas.length} ${_reservas.length == 1 ? 'reserva' : 'reservas'} en total',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.7),
                      fontSize: 13,
                    ),
                  ),
                  if (_reservas.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    SizedBox(
                      height: 36,
                      child: Row(
                        children: [
                          _segmentButton('todos', 'Todos'),
                          const SizedBox(width: 8),
                          _segmentButton('proximos', 'Próximos'),
                          const SizedBox(width: 8),
                          _segmentButton('pasados', 'Pasados'),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
          if (_loading)
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, kFloatingNavHeight),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate(
                  (_, _) => const SkeletonCard(height: 160),
                  childCount: 3,
                ),
              ),
            )
          else if (_error != null)
            SliverFillRemaining(child: Center(child: Text(_error!)))
          else if (_reservas.isEmpty)
            const SliverFillRemaining(child: _EmptyView())
          else
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, kFloatingNavHeight),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate(
                  (_, i) {
                    final entry = _gruposFiltrados.entries.elementAt(i);
                    return _GrupoCard(grupoPago: entry.key, reservas: entry.value)
                        .animate()
                        .fadeIn(duration: 320.ms, delay: (i * 80).ms)
                        .slideY(begin: 0.15, end: 0, curve: Curves.easeOutCubic);
                  },
                  childCount: _gruposFiltrados.length,
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _segmentButton(String value, String label) {
    final active = _filtro == value;
    return Material(
      color: active ? Colors.white : Colors.white.withValues(alpha: 0.15),
      borderRadius: BorderRadius.circular(20),
      child: InkWell(
        onTap: () => setState(() => _filtro = value),
        borderRadius: BorderRadius.circular(20),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Text(
            label,
            style: TextStyle(
              color: active ? AppColors.blue700 : Colors.white,
              fontWeight: FontWeight.w700,
              fontSize: 12,
            ),
          ),
        ),
      ),
    );
  }
}

class _GrupoCard extends StatelessWidget {
  final String grupoPago;
  final List<Reserva> reservas;
  const _GrupoCard({required this.grupoPago, required this.reservas});

  @override
  Widget build(BuildContext context) {
    final first = reservas.first;
    final isGroup = !grupoPago.startsWith('sin_grupo_');
    final estado = first.estado;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Material(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        child: InkWell(
          borderRadius: BorderRadius.circular(18),
          onTap: (isGroup && first.esConfirmada)
              ? () => context.push('/ticket/$grupoPago')
              : null,
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: AppColors.borderSubtle),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // ── Countdown banner (estilo MyBus) ──
                _CountdownBanner(
                  fechaIso: first.fechaSalida,
                  horaHms: first.horaSalida,
                  estado: estado,
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        '${first.rutaOrigen ?? '?'} → ${first.rutaDestino ?? '?'}',
                        style: const TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w800,
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ),
                    _EstadoChip(estado: estado),
                  ],
                ),
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppColors.gray50,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: _kvBlock(
                          icon: Icons.calendar_today_rounded,
                          label: 'Fecha',
                          value: _fechaCorta(first.fechaSalida),
                        ),
                      ),
                      Container(width: 1, height: 32, color: AppColors.borderStandard),
                      Expanded(
                        child: _kvBlock(
                          icon: Icons.access_time_rounded,
                          label: 'Hora',
                          value: _hora(first.horaSalida),
                        ),
                      ),
                      Container(width: 1, height: 32, color: AppColors.borderStandard),
                      Expanded(
                        child: _kvBlock(
                          icon: Icons.event_seat_rounded,
                          label: 'Asientos',
                          value: reservas.map((r) => '#${r.numeroAsiento}').join(', '),
                        ),
                      ),
                    ],
                  ),
                ),
                if (first.esConfirmada && isGroup) ...[
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    decoration: BoxDecoration(
                      color: AppColors.blue50,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Row(
                      children: const [
                        Icon(Icons.qr_code_2_rounded, color: AppColors.blue500, size: 20),
                        SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'Toca para ver tu ticket QR',
                            style: TextStyle(
                              color: AppColors.blue500,
                              fontWeight: FontWeight.w700,
                              fontSize: 13,
                            ),
                          ),
                        ),
                        Icon(Icons.arrow_forward_rounded,
                            color: AppColors.blue500, size: 18),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _kvBlock({required IconData icon, required String label, required String value}) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 11, color: AppColors.textMuted),
              const SizedBox(width: 3),
              Text(
                label,
                style: const TextStyle(
                  fontSize: 10,
                  color: AppColors.textMuted,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 3),
          Text(
            value,
            style: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  String _fechaCorta(String? iso) {
    if (iso == null) return '—';
    try {
      return DateFormat('d MMM', 'es').format(DateTime.parse(iso));
    } catch (_) {
      return iso;
    }
  }

  String _hora(String? hms) {
    if (hms == null || hms.isEmpty) return '—';
    return hms.length >= 5 ? hms.substring(0, 5) : hms;
  }
}

class _EstadoChip extends StatelessWidget {
  final String estado;
  const _EstadoChip({required this.estado});

  @override
  Widget build(BuildContext context) {
    switch (estado) {
      case 'confirmado':
        return OfficialStamp.confirmado(compact: true);
      case 'apartado':
        return OfficialStamp.validando(compact: true);
      case 'pendiente':
        return OfficialStamp.pendiente(compact: true);
      case 'cancelado':
        return OfficialStamp.rechazado(compact: true);
      default:
        return OfficialStamp(
          label: estado.toUpperCase(),
          color: AppColors.textTertiary,
          compact: true,
        );
    }
  }
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
            Stack(
              alignment: Alignment.center,
              children: [
                Container(
                  width: 120, height: 120,
                  decoration: BoxDecoration(
                    color: AppColors.blue50,
                    shape: BoxShape.circle,
                  ),
                ),
                Container(
                  width: 90, height: 90,
                  decoration: BoxDecoration(
                    color: AppColors.blue100,
                    shape: BoxShape.circle,
                  ),
                ),
                const Icon(Icons.confirmation_number_outlined,
                    size: 56, color: AppColors.blue500),
              ],
            ),
            const SizedBox(height: 24),
            const Text(
              'Aún no tienes viajes',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 6),
            const Text(
              'Reserva tu primer pasaje y aparecerá aquí.',
              textAlign: TextAlign.center,
              style: TextStyle(color: AppColors.textTertiary),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              icon: const Icon(Icons.search_rounded),
              label: const Text('Buscar viajes'),
              onPressed: () => context.go('/'),
            ),
          ],
        ),
      ),
    );
  }
}

/// Banner countdown estilo "MyBus" — número grande monospace con tiempo
/// hasta la salida o desde que pasó el viaje.
class _CountdownBanner extends StatelessWidget {
  final String? fechaIso;
  final String? horaHms;
  final String estado;

  const _CountdownBanner({
    required this.fechaIso,
    required this.horaHms,
    required this.estado,
  });

  @override
  Widget build(BuildContext context) {
    if (estado == 'cancelado') return const SizedBox.shrink();

    final salida = _parseSalida();
    if (salida == null) return const SizedBox.shrink();

    final now = DateTime.now();
    final diff = salida.difference(now);
    final isPast = diff.isNegative;
    final isUrgent = !isPast && diff.inHours < 2;

    // Colores y label según contexto
    final Color bg;
    final Color fg;
    final Color labelFg;
    final String label;

    if (isPast) {
      bg = AppColors.gray100;
      fg = AppColors.textSecondary;
      labelFg = AppColors.textMuted;
      label = diff.abs().inDays >= 1 ? 'VIAJE COMPLETADO' : 'YA SALIÓ';
    } else if (isUrgent) {
      bg = AppColors.red50;
      fg = AppColors.red500;
      labelFg = AppColors.red500;
      label = '¡SALE PRONTO!';
    } else if (estado == 'confirmado') {
      bg = AppColors.green50;
      fg = AppColors.green500;
      labelFg = AppColors.green500;
      label = 'SALE EN';
    } else {
      bg = AppColors.blue50;
      fg = AppColors.blue500;
      labelFg = AppColors.blue500;
      label = 'SALE EN';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Icon(
            isPast ? Icons.history_rounded
                  : isUrgent ? Icons.notifications_active_rounded
                  : Icons.schedule_rounded,
            color: fg, size: 22,
          ),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                label,
                style: AppMono.style(
                  fontSize: 9,
                  fontWeight: FontWeight.w800,
                  color: labelFg,
                  letterSpacing: 1.5,
                ),
              ),
              Text(
                _formatDuration(diff),
                style: AppMono.style(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  color: fg,
                  letterSpacing: -0.5,
                ),
              ),
            ],
          ),
          const Spacer(),
          // Pequeño tag con la fecha exacta a la derecha
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.7),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(
              _shortDate(salida),
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w700,
                color: fg,
                letterSpacing: 0.3,
              ),
            ),
          ),
        ],
      ),
    );
  }

  DateTime? _parseSalida() {
    if (fechaIso == null || fechaIso!.isEmpty) return null;
    try {
      final fecha = DateTime.parse(fechaIso!);
      if (horaHms != null && horaHms!.length >= 5) {
        final parts = horaHms!.split(':');
        final h = int.tryParse(parts[0]) ?? 0;
        final m = int.tryParse(parts[1]) ?? 0;
        return DateTime(fecha.year, fecha.month, fecha.day, h, m);
      }
      return fecha;
    } catch (_) {
      return null;
    }
  }

  String _formatDuration(Duration d) {
    final abs = d.abs();
    final days = abs.inDays;
    final hours = abs.inHours % 24;
    final mins = abs.inMinutes % 60;

    if (days >= 7) {
      final weeks = days ~/ 7;
      return '${weeks}sem';
    }
    if (days >= 1) {
      return '${days}d ${hours}h';
    }
    if (hours >= 1) {
      return '${hours}h ${mins}m';
    }
    if (mins >= 1) {
      return '${mins}m';
    }
    return d.isNegative ? 'Recién' : 'Ya';
  }

  String _shortDate(DateTime d) {
    const meses = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC'];
    final hh = d.hour.toString().padLeft(2, '0');
    final mm = d.minute.toString().padLeft(2, '0');
    return '${d.day} ${meses[d.month - 1]} · $hh:$mm';
  }
}
