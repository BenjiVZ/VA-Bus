import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../config/theme.dart';

/// Sello oficial — reemplaza los badges genéricos para estados con peso.
///
/// Tiene rotación leve, doble borde y tipografía monospace con tracking amplio.
/// Lenguaje del sistema Aerorutas: cada confirmación es un "estampado".
///
/// Ejemplos:
///   OfficialStamp(label: 'PAGO CONFIRMADO', color: AppColors.green500)
///   OfficialStamp(label: 'EN VALIDACIÓN', color: AppColors.blue500)
///   OfficialStamp(label: 'RECHAZADO', color: AppColors.red500, tilt: -3)
class OfficialStamp extends StatelessWidget {
  final String label;
  final Color color;
  final IconData? icon;

  /// Rotación en grados. Defaults a -2 (sutil pero visible).
  final double tilt;

  /// Tamaño compacto para usar inline en cards.
  final bool compact;

  const OfficialStamp({
    super.key,
    required this.label,
    required this.color,
    this.icon,
    this.tilt = -2,
    this.compact = false,
  });

  /// Variante "PAGO CONFIRMADO" — verde, con check.
  factory OfficialStamp.confirmado({double tilt = -2, bool compact = false}) =>
      OfficialStamp(
        label: 'PAGO CONFIRMADO',
        color: AppColors.green500,
        icon: Icons.check_circle_outline_rounded,
        tilt: tilt,
        compact: compact,
      );

  /// Variante "EN VALIDACIÓN" — azul.
  factory OfficialStamp.validando({double tilt = -2, bool compact = false}) =>
      OfficialStamp(
        label: 'EN VALIDACIÓN',
        color: AppColors.blue500,
        icon: Icons.hourglass_top_rounded,
        tilt: tilt,
        compact: compact,
      );

  /// Variante "PENDIENTE" — amarillo.
  factory OfficialStamp.pendiente({double tilt = -2, bool compact = false}) =>
      OfficialStamp(
        label: 'PENDIENTE',
        color: AppColors.yellow600,
        icon: Icons.schedule_rounded,
        tilt: tilt,
        compact: compact,
      );

  /// Variante "RECHAZADO" — rojo con rotación más fuerte.
  factory OfficialStamp.rechazado({bool compact = false}) =>
      OfficialStamp(
        label: 'RECHAZADO',
        color: AppColors.red500,
        icon: Icons.block_rounded,
        tilt: -4,
        compact: compact,
      );

  @override
  Widget build(BuildContext context) {
    final hPad = compact ? 8.0 : 10.0;
    final vPad = compact ? 4.0 : 6.0;
    final fontSize = compact ? 10.0 : 11.0;
    final iconSize = compact ? 11.0 : 13.0;

    return Transform.rotate(
      angle: tilt * 3.14159 / 180,
      child: Animate(
        effects: [
          // Estampado: aparece grande, se asienta con un pequeño rebote
          ScaleEffect(
            begin: const Offset(1.6, 1.6),
            end: const Offset(1.0, 1.0),
            duration: 320.ms,
            curve: Curves.easeOutBack,
          ),
          FadeEffect(duration: 200.ms),
        ],
        child: Container(
        padding: EdgeInsets.symmetric(horizontal: hPad, vertical: vPad),
        decoration: BoxDecoration(
          color: Colors.transparent,
          border: Border.all(color: color, width: 1.5),
          borderRadius: BorderRadius.circular(4),
        ),
        child: IntrinsicWidth(
          child: Container(
            padding: EdgeInsets.symmetric(horizontal: hPad * 0.5, vertical: 1),
            decoration: BoxDecoration(
              border: Border.all(color: color.withValues(alpha: 0.55), width: 1),
              borderRadius: BorderRadius.circular(2),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (icon != null) ...[
                  Icon(icon, color: color, size: iconSize),
                  const SizedBox(width: 5),
                ],
                Text(
                  label,
                  style: AppMono.style(
                    fontSize: fontSize,
                    fontWeight: FontWeight.w800,
                    color: color,
                    letterSpacing: 1.5,
                  ),
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
