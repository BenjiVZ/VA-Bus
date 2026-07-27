import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/foundation.dart' show debugPrint, kIsWeb;
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:provider/provider.dart';

import '../config/constants.dart';
import '../config/theme.dart';
import '../providers/auth_provider.dart';
// En Web se usa el botón OFICIAL de Google (renderButton); en Android/iOS un
// stub vacío. El import condicional evita romper la compilación nativa.
import 'google_button_platform_stub.dart'
    if (dart.library.js_interop) 'google_button_platform_web.dart'
    as platform_btn;

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
  StreamSubscription<GoogleSignInAccount?>? _webSub;

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
    if (kIsWeb) {
      // En Web el botón lo renderiza Google (GIS). Cuando el usuario completa
      // el flujo, el plugin emite la cuenta por este stream (con idToken).
      _webSub = _signIn!.onCurrentUserChanged.listen(_onCuentaWeb);
    }
  }

  @override
  void dispose() {
    _webSub?.cancel();
    super.dispose();
  }

  Future<void> _onCuentaWeb(GoogleSignInAccount? account) async {
    if (account == null) return;
    setState(() => _loading = true);
    try {
      final auth = await account.authentication;
      await _canjearIdToken(auth.idToken);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  /// Intercambia el ID token de Google por el JWT del backend y notifica.
  Future<void> _canjearIdToken(String? idToken) async {
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
      debugPrint('[google] canje de idToken fallido: $err');
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(err),
        duration: const Duration(seconds: 8), // da tiempo a leer la causa
      ));
    }
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
      await _canjearIdToken(auth.idToken);
    } catch (e) {
      debugPrint('[google] signIn() falló: $e');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error de Google Sign-In: $e'),
          duration: const Duration(seconds: 8),
        ),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    // Si no hay client ID configurado, no mostramos el botón.
    if (_signIn == null) return const SizedBox.shrink();

    // Web: botón oficial de Google (único flujo que entrega idToken en GIS).
    if (kIsWeb) {
      return SizedBox(
        height: 44,
        child: Center(
          child: _loading
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: AppColors.blue500,
                  ),
                )
              : platform_btn.renderGoogleWebButton(),
        ),
      );
    }

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
  static const _azul = Color(0xFF4285F4);
  static const _verde = Color(0xFF34A853);
  static const _amarillo = Color(0xFFFBBC05);
  static const _rojo = Color(0xFFEA4335);

  static double _rad(double grados) => grados * math.pi / 180;

  @override
  void paint(Canvas canvas, Size size) {
    final s = size.shortestSide;
    final grosor = s * 0.26;              // ancho del trazo de la "G"
    final r = (s - grosor) / 2;           // radio al centro del trazo
    final c = Offset(size.width / 2, size.height / 2);
    final rect = Rect.fromCircle(center: c, radius: r);

    // La "G" es un anillo de 4 tramos de color (0° = derecha, positivo = horario).
    final trazo = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = grosor
      ..strokeCap = StrokeCap.butt;

    trazo.color = _azul;                                   // derecha (con la barra)
    canvas.drawArc(rect, _rad(-40), _rad(60), false, trazo);
    trazo.color = _verde;                                  // abajo
    canvas.drawArc(rect, _rad(20), _rad(90), false, trazo);
    trazo.color = _amarillo;                               // izquierda
    canvas.drawArc(rect, _rad(110), _rad(90), false, trazo);
    trazo.color = _rojo;                                   // arriba
    canvas.drawArc(rect, _rad(200), _rad(112), false, trazo);

    // Barra horizontal azul: del centro hacia la derecha (el "brazo" de la G).
    final barra = Paint()
      ..style = PaintingStyle.fill
      ..color = _azul;
    canvas.drawRect(
      Rect.fromLTRB(
        c.dx - grosor * 0.05,
        c.dy - grosor / 2,
        c.dx + r + grosor / 2,
        c.dy + grosor / 2,
      ),
      barra,
    );
  }

  @override
  bool shouldRepaint(_) => false;
}
