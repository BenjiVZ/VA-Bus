import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

/// Logo de Aerorutas — usa el SVG oficial de frontend/public/logo.svg.
///
/// Variantes:
///   - [AppLogo()] — logo SVG completo (con texto)
///   - [AppLogo.icon()] — solo el pájaro/ícono redondo (PNG)
class AppLogo extends StatelessWidget {
  final double height;
  final Color? color;

  const AppLogo({super.key, this.height = 40, this.color});

  /// Constructor para mostrar solo el ícono circular (PNG con el pájaro).
  /// Útil para avatares y botones pequeños.
  factory AppLogo.icon({Key? key, double size = 40}) {
    return _AppLogoIcon(key: key, size: size);
  }

  @override
  Widget build(BuildContext context) {
    return SvgPicture.asset(
      'assets/logo/logo.svg',
      height: height,
      colorFilter: color == null ? null : ColorFilter.mode(color!, BlendMode.srcIn),
    );
  }
}

class _AppLogoIcon extends AppLogo {
  final double size;
  const _AppLogoIcon({super.key, required this.size}) : super(height: size);

  @override
  Widget build(BuildContext context) {
    return Image.asset(
      'assets/logo/logo-redondo.png',
      width: size,
      height: size,
      fit: BoxFit.cover,
    );
  }
}
