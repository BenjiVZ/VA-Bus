import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:provider/provider.dart';

import '../config/constants.dart';
import '../config/theme.dart';
import '../providers/auth_provider.dart';

/// Botón "Continuar con Google" que abre el flujo nativo de Google Sign-In,
/// obtiene el ID token y lo intercambia por JWT en el backend.
///
/// Si `AppConfig.googleClientId` está vacío, el widget se oculta (no muestra
/// el botón roto). Pasá el Client ID con:
///   flutter run --dart-define=GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
///
/// Comportamiento por plataforma:
/// - Web: usa `clientId` directo (el botón abre un popup de Google).
/// - Android: lee el Client ID auto-configurado vía el SHA-1 + package name
///   en Google Console. `serverClientId` es el Web Client ID con el que el
///   backend valida (debe ser el mismo que está en el .env del Django).
/// - iOS: lee el `REVERSED_CLIENT_ID` del Info.plist (configurado abajo).
class GoogleSignInButton extends StatefulWidget {
  /// Callback cuando el login termina (ok = true si autenticó).
  final void Function(bool ok) onComplete;

  const GoogleSignInButton({super.key, required this.onComplete});

  @override
  State<GoogleSignInButton> createState() => _GoogleSignInButtonState();
}

class _GoogleSignInButtonState extends State<GoogleSignInButton> {
  bool _loading = false;
  GoogleSignIn? _signIn;

  @override
  void initState() {
    super.initState();
    final clientId = AppConfig.googleClientId;
    if (clientId.isEmpty) return;
    _signIn = GoogleSignIn(
      // En Web hay que pasarlo en `clientId`. En Android/iOS NO hay que
      // pasarlo (la plataforma lo resuelve sola) pero sí en `serverClientId`
      // para que el ID token devuelto sea válido para nuestro backend.
      clientId: kIsWeb ? clientId : null,
      serverClientId: kIsWeb ? null : clientId,
      scopes: const ['email', 'profile'],
    );
  }

  Future<void> _onPressed() async {
    final signIn = _signIn;
    if (signIn == null) return;
    setState(() => _loading = true);
    try {
      final account = await signIn.signIn();
      if (account == null) {
        // Usuario canceló el diálogo.
        return;
      }
      final auth = await account.authentication;
      final idToken = auth.idToken;
      if (idToken == null || idToken.isEmpty) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'No se obtuvo el ID token de Google. '
              'Revisá la configuración de OAuth.',
            ),
          ),
        );
        return;
      }
      if (!mounted) return;
      final ok = await context.read<AuthProvider>().loginConGoogle(idToken);
      if (!mounted) return;
      widget.onComplete(ok);
      if (!ok) {
        final err = context.read<AuthProvider>().lastError ??
            'No se pudo iniciar con Google.';
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error de Google Sign-In: $e')),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    // Si no hay client ID configurado, no mostramos el botón.
    if (_signIn == null) return const SizedBox.shrink();

    return OutlinedButton(
      onPressed: _loading ? null : _onPressed,
      style: OutlinedButton.styleFrom(
        padding: const EdgeInsets.symmetric(vertical: 14),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
        ),
        side: const BorderSide(color: Color(0xFFDADCE0)),
        foregroundColor: const Color(0xFF3C4043),
        backgroundColor: Colors.white,
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _loading
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: AppColors.blue500,
                  ),
                )
              : const _GoogleGlyph(size: 18),
          const SizedBox(width: 10),
          const Text(
            'Continuar con Google',
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: Color(0xFF3C4043),
            ),
          ),
        ],
      ),
    );
  }
}

/// "G" multicolor de Google dibujada con CustomPaint — evita necesitar
/// un asset PNG/SVG del logo (que tiene su propia política de uso).
class _GoogleGlyph extends StatelessWidget {
  final double size;
  const _GoogleGlyph({required this.size});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(painter: _GoogleGlyphPainter()),
    );
  }
}

class _GoogleGlyphPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final c = Offset(size.width / 2, size.height / 2);
    final r = size.width / 2;
    final paint = Paint()..style = PaintingStyle.fill;

    // Cuadrantes coloreados aproximando la "G" de Google.
    // Top-right: rojo
    paint.color = const Color(0xFFEA4335);
    canvas.drawArc(Rect.fromCircle(center: c, radius: r), -1.5708, 1.5708, true, paint);
    // Bottom-right: amarillo
    paint.color = const Color(0xFFFBBC05);
    canvas.drawArc(Rect.fromCircle(center: c, radius: r), 0, 1.5708, true, paint);
    // Bottom-left: verde
    paint.color = const Color(0xFF34A853);
    canvas.drawArc(Rect.fromCircle(center: c, radius: r), 1.5708, 1.5708, true, paint);
    // Top-left: azul
    paint.color = const Color(0xFF4285F4);
    canvas.drawArc(Rect.fromCircle(center: c, radius: r), 3.1416, 1.5708, true, paint);

    // Círculo blanco interno (hueco de la G)
    paint.color = Colors.white;
    canvas.drawCircle(c, r * 0.42, paint);

    // "Barra" derecha que forma la G — rectángulo blanco a la derecha
    paint.color = Colors.white;
    canvas.drawRect(
      Rect.fromLTWH(c.dx, c.dy - r * 0.12, r, r * 0.24),
      paint,
    );
  }

  @override
  bool shouldRepaint(_) => false;
}
