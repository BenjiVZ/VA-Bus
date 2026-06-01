import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../config/theme.dart';

/// Card skeleton para estados de carga.
///
/// Usa el ShimmerEffect de flutter_animate (chainable, repeat infinito).
/// Pinta una "card fantasma" con la altura aproximada del contenido real.
///
/// Ejemplo de uso:
///   Column(
///     children: List.generate(4, (i) => const SkeletonCard()),
///   )
class SkeletonCard extends StatelessWidget {
  final double height;
  final EdgeInsets margin;
  final BorderRadius borderRadius;

  const SkeletonCard({
    super.key,
    this.height = 140,
    this.margin = const EdgeInsets.only(bottom: 12),
    this.borderRadius = const BorderRadius.all(Radius.circular(18)),
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      margin: margin,
      decoration: BoxDecoration(
        color: AppColors.gray100,
        borderRadius: borderRadius,
        border: Border.all(color: AppColors.borderSubtle),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            // Línea título
            _bar(width: 200, height: 14),
            // Línea subtítulo
            _bar(width: 140, height: 10),
            // Línea inferior
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _bar(width: 80, height: 12),
                _bar(width: 60, height: 18),
              ],
            ),
          ],
        ),
      ),
    )
        .animate(onPlay: (c) => c.repeat())
        .shimmer(
          duration: 1400.ms,
          color: AppColors.gray50,
          angle: 0.4,
        );
  }

  Widget _bar({required double width, required double height}) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: AppColors.gray200,
        borderRadius: BorderRadius.circular(height / 2),
      ),
    );
  }
}
