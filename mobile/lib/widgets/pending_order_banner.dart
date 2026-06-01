import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../models/reserva.dart';
import '../providers/auth_provider.dart';
import '../services/reservas_service.dart';

/// Banner que aparece cuando el usuario tiene reservas pendientes de pago.
/// Espeja el ReservaPendienteAlert del frontend web.
///
/// Tappear el banner navega a /pago?grupo=... del primer grupo pendiente.
/// La "X" lo oculta sólo para la sesión actual (no persiste).
/// Si la ruta actual ya empieza con /pago, no se muestra.
class PendingOrderBanner extends StatefulWidget {
  const PendingOrderBanner({super.key});

  @override
  State<PendingOrderBanner> createState() => _PendingOrderBannerState();
}

class _PendingOrderBannerState extends State<PendingOrderBanner> {
  static bool _dismissedThisSession = false;

  List<_PendingGroup> _groups = [];
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    _fetch();
  }

  Future<void> _fetch() async {
    final auth = context.read<AuthProvider>();
    if (!auth.isAuthenticated) {
      if (mounted) setState(() => _loaded = true);
      return;
    }
    try {
      final svc = context.read<ReservasService>();
      final list = await svc.getMisReservas();
      final pend = list
          .where((r) => r.estado == 'pendiente' && (r.grupoPago ?? '').isNotEmpty)
          .toList();

      final grouped = <String, _PendingGroup>{};
      for (final r in pend) {
        final key = r.grupoPago!;
        final g = grouped.putIfAbsent(
          key,
          () => _PendingGroup(
            grupoPago: key,
            viajeId: r.viajeId,
            ruta: _rutaText(r),
            count: 0,
          ),
        );
        g.count += 1;
      }
      if (!mounted) return;
      setState(() {
        _groups = grouped.values.toList();
        _loaded = true;
      });
    } catch (_) {
      if (mounted) setState(() => _loaded = true);
    }
  }

  String _rutaText(Reserva r) {
    final o = r.rutaOrigen ?? '';
    final d = r.rutaDestino ?? '';
    if (o.isEmpty && d.isEmpty) return 'Reserva pendiente';
    return '$o → $d';
  }

  @override
  Widget build(BuildContext context) {
    if (!_loaded || _groups.isEmpty || _dismissedThisSession) {
      return const SizedBox.shrink();
    }
    final auth = context.watch<AuthProvider>();
    if (!auth.isAuthenticated) return const SizedBox.shrink();

    // No mostrar si ya estamos en /pago.
    final loc = GoRouterState.of(context).matchedLocation;
    if (loc.startsWith('/pago')) return const SizedBox.shrink();

    final first = _groups.first;
    final total = _groups.fold<int>(0, (a, g) => a + g.count);
    final extras = _groups.length - 1;

    return Material(
      color: Colors.transparent,
      child: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFFF59E0B), Color(0xFFD97706)],
          ),
        ),
        child: SafeArea(
          top: true,
          bottom: false,
          child: InkWell(
            onTap: () => context.push(
              '/pago?grupo=${first.grupoPago}&viaje=${first.viajeId}',
            ),
            child: Padding(
              padding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              child: Row(
                children: [
                  const Icon(Icons.schedule_rounded,
                      size: 20, color: Colors.white),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'Tienes $total asiento${total == 1 ? '' : 's'} pendiente${total == 1 ? '' : 's'} de pago',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 13,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          extras > 0
                              ? '${first.ruta} y $extras más'
                              : first.ruta,
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.92),
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 10),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.credit_card_rounded,
                            size: 14, color: Color(0xFFD97706)),
                        SizedBox(width: 4),
                        Text(
                          'Ir a pagar',
                          style: TextStyle(
                            color: Color(0xFFD97706),
                            fontSize: 12,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 4),
                  IconButton(
                    onPressed: () =>
                        setState(() => _dismissedThisSession = true),
                    icon: Icon(
                      Icons.close_rounded,
                      color: Colors.white.withValues(alpha: 0.85),
                      size: 18,
                    ),
                    padding: EdgeInsets.zero,
                    constraints:
                        const BoxConstraints(minWidth: 28, minHeight: 28),
                    tooltip: 'Ocultar',
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _PendingGroup {
  final String grupoPago;
  final int viajeId;
  final String ruta;
  int count;
  _PendingGroup({
    required this.grupoPago,
    required this.viajeId,
    required this.ruta,
    required this.count,
  });
}

