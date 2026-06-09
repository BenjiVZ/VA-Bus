import 'package:flutter/material.dart';
import '../config/theme.dart';
import '../models/viaje.dart';

/// Representa el estado visual de un asiento — espeja SeatMap.jsx.
enum SeatState { available, selected, occupied }

class SelectedSeat {
  final int numero;
  final int piso;
  const SelectedSeat({required this.numero, required this.piso});

  @override
  bool operator ==(Object other) =>
      other is SelectedSeat && other.numero == numero && other.piso == piso;

  @override
  int get hashCode => Object.hash(numero, piso);
}

/// Mapa de asientos con tabs por piso. Lee el layout JSON de PisoConfig
/// y muestra celdas de tipo: seat, door, stairs, driver, aisle, empty.
class SeatMap extends StatefulWidget {
  final List<PisoConfig> pisos;
  final List<SelectedSeat> selectedSeats;
  final void Function(SelectedSeat) onToggleSeat;

  const SeatMap({
    super.key,
    required this.pisos,
    required this.selectedSeats,
    required this.onToggleSeat,
  });

  @override
  State<SeatMap> createState() => _SeatMapState();
}

class _SeatMapState extends State<SeatMap> {
  late int _activePiso;

  @override
  void initState() {
    super.initState();
    _activePiso = widget.pisos.isNotEmpty ? widget.pisos.first.numeroPiso : 1;
  }

  PisoConfig? get _config =>
      widget.pisos.where((p) => p.numeroPiso == _activePiso).cast<PisoConfig?>().firstOrNull;

  SeatState _stateFor(int numero) {
    final isSelected = widget.selectedSeats
        .any((s) => s.numero == numero && s.piso == _activePiso);
    return isSelected ? SeatState.selected : SeatState.available;
  }

  @override
  Widget build(BuildContext context) {
    final config = _config;
    if (config == null || config.layout.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(24),
        child: Center(
          child: Text(
            'No hay layout configurado para este autobús.',
            style: TextStyle(color: AppColors.textTertiary),
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (widget.pisos.length > 1) _floorTabs(),
        const SizedBox(height: 12),
        _busOutline(config),
        const SizedBox(height: 16),
        _legend(),
      ],
    );
  }

  Widget _floorTabs() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: widget.pisos.map((p) {
          final active = p.numeroPiso == _activePiso;
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: ChoiceChip(
              label: Text('Piso ${p.numeroPiso}'),
              selected: active,
              onSelected: (_) => setState(() => _activePiso = p.numeroPiso),
              selectedColor: AppColors.blue500,
              labelStyle: TextStyle(
                color: active ? Colors.white : AppColors.textPrimary,
                fontWeight: FontWeight.w600,
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _busOutline(PisoConfig config) {
    final cols = config.columnas > 0 ? config.columnas : 5;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: AppColors.borderStandard, width: 2),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(vertical: 6),
            decoration: BoxDecoration(
              color: AppColors.gray50,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.airline_seat_recline_normal,
                    size: 14, color: AppColors.textTertiary),
                SizedBox(width: 6),
                Text(
                  'FRENTE DEL AUTOBÚS',
                  style: TextStyle(
                    fontSize: 10,
                    letterSpacing: 1.5,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textTertiary,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: cols,
              mainAxisSpacing: 8,
              crossAxisSpacing: 8,
              childAspectRatio: 0.88,
            ),
            itemCount: config.layout.fold<int>(0, (sum, row) => sum + row.length),
            itemBuilder: (_, idx) {
              // Convertir índice plano → (fila, col)
              int acum = 0;
              int rIdx = 0;
              int cIdx = 0;
              for (int r = 0; r < config.layout.length; r++) {
                final row = config.layout[r];
                if (idx < acum + row.length) {
                  rIdx = r;
                  cIdx = idx - acum;
                  break;
                }
                acum += row.length;
              }
              final cell = config.layout[rIdx][cIdx];
              return _buildCell(cell);
            },
          ),
        ],
      ),
    );
  }

  Widget _buildCell(Map<String, dynamic> cell) {
    final type = (cell['type'] ?? 'empty') as String;
    final number = cell['number'] as int?;
    final disponible = cell['disponible'] != false; // null = true

    if (type == 'seat' && number != null) {
      final state = !disponible ? SeatState.occupied : _stateFor(number);
      return _SeatIcon(
        number: number,
        state: state,
        onTap: state == SeatState.occupied
            ? null
            : () => widget.onToggleSeat(
                SelectedSeat(numero: number, piso: _activePiso)),
      );
    }
    if (type == 'door') {
      return _LayoutIcon(icon: Icons.meeting_room_outlined, color: AppColors.red500);
    }
    if (type == 'stairs') {
      return _LayoutIcon(icon: Icons.stairs_outlined, color: AppColors.green500);
    }
    if (type == 'driver') {
      return _LayoutIcon(icon: Icons.airline_seat_recline_extra, color: AppColors.blue500);
    }
    if (type == 'aisle') {
      return const SizedBox.shrink();
    }
    return const SizedBox.shrink();
  }

  Widget _legend() {
    return Wrap(
      spacing: 12,
      runSpacing: 8,
      alignment: WrapAlignment.center,
      children: const [
        _LegendItem(state: SeatState.available, label: 'Disponible'),
        _LegendItem(state: SeatState.selected, label: 'Seleccionado'),
        _LegendItem(state: SeatState.occupied, label: 'Ocupado'),
      ],
    );
  }
}

class _SeatIcon extends StatelessWidget {
  final int number;
  final SeatState state;
  final VoidCallback? onTap;
  const _SeatIcon({required this.number, required this.state, this.onTap});

  @override
  Widget build(BuildContext context) {
    final palette = _palette(state);
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: CustomPaint(
        painter: _SeatPainter(palette),
        child: Align(
          // Número centrado sobre el respaldo (igual que el SVG web, y≈28/52).
          alignment: const Alignment(0, 0.08),
          child: FittedBox(
            fit: BoxFit.scaleDown,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 2),
              child: Text(
                number > 0 ? '$number' : '',
                style: TextStyle(
                  color: palette.text,
                  fontWeight: FontWeight.w700,
                  fontSize: 13,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  _SeatPalette _palette(SeatState s) {
    switch (s) {
      case SeatState.available:
        return _SeatPalette(
          fill: Colors.white,
          border: AppColors.gray300,
          text: AppColors.gray700,
          headrest: AppColors.gray200,
        );
      case SeatState.selected:
        return _SeatPalette(
          fill: AppColors.blue500,
          border: AppColors.blue700,
          text: Colors.white,
          headrest: AppColors.blue700,
        );
      case SeatState.occupied:
        return _SeatPalette(
          fill: AppColors.yellow50,
          border: AppColors.yellow500,
          text: AppColors.yellow600,
          headrest: AppColors.yellow400,
        );
    }
  }
}

class _SeatPalette {
  final Color fill;
  final Color border;
  final Color text;
  final Color headrest;
  _SeatPalette({
    required this.fill,
    required this.border,
    required this.text,
    required this.headrest,
  });
}

/// Dibuja un asiento con forma de butaca replicando el SVG del frontend web
/// (SeatMap.jsx): reposacabezas, respaldo, cojín y reposabrazos.
/// Usa el mismo sistema de coordenadas del SVG (viewBox 48x52) escalado.
class _SeatPainter extends CustomPainter {
  final _SeatPalette p;
  _SeatPainter(this.p);

  @override
  void paint(Canvas canvas, Size size) {
    final sx = size.width / 48.0;
    final sy = size.height / 52.0;

    RRect rr(double x, double y, double w, double h, double radius) =>
        RRect.fromRectAndRadius(
          Rect.fromLTWH(x * sx, y * sy, w * sx, h * sy),
          Radius.circular(radius * sx),
        );

    final fill = Paint()
      ..style = PaintingStyle.fill
      ..color = p.fill;
    final headrest = Paint()
      ..style = PaintingStyle.fill
      ..color = p.headrest;
    final stroke = Paint()
      ..style = PaintingStyle.stroke
      ..color = p.border
      ..strokeWidth = 1.5 * sx;

    // Orden de pintado igual al SVG: reposacabezas, respaldo, cojín, reposabrazos.
    final head = rr(8, 0, 32, 10, 5); // reposacabezas
    canvas.drawRRect(head, headrest);
    canvas.drawRRect(head, stroke);

    final back = rr(4, 8, 40, 30, 4); // respaldo
    canvas.drawRRect(back, fill);
    canvas.drawRRect(back, stroke);

    final cushion = rr(2, 36, 44, 14, 4); // cojín
    canvas.drawRRect(cushion, fill);
    canvas.drawRRect(cushion, stroke);

    final armL = rr(0, 28, 5, 16, 2.5); // reposabrazos izquierdo
    final armR = rr(43, 28, 5, 16, 2.5); // reposabrazos derecho
    for (final arm in [armL, armR]) {
      canvas.drawRRect(arm, headrest);
      canvas.drawRRect(arm, stroke);
    }
  }

  @override
  bool shouldRepaint(covariant _SeatPainter old) =>
      old.p.fill != p.fill ||
      old.p.border != p.border ||
      old.p.headrest != p.headrest;
}

class _LayoutIcon extends StatelessWidget {
  final IconData icon;
  final Color color;
  const _LayoutIcon({required this.icon, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.3), width: 1.5),
      ),
      alignment: Alignment.center,
      child: Icon(icon, color: color, size: 20),
    );
  }
}

class _LegendItem extends StatelessWidget {
  final SeatState state;
  final String label;
  const _LegendItem({required this.state, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: 36,
          height: 36,
          child: _SeatIcon(number: 0, state: state, onTap: null),
        ),
        const SizedBox(width: 6),
        Text(label, style: const TextStyle(fontSize: 12, color: AppColors.textTertiary)),
      ],
    );
  }
}

extension<T> on Iterable<T> {
  T? get firstOrNull => isEmpty ? null : first;
}
