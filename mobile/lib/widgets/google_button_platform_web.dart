import 'package:flutter/widgets.dart';
import 'package:google_sign_in_web/web_only.dart' as web;

/// Botón OFICIAL de Google (GIS) para Flutter Web.
///
/// En web, `signIn()` del plugin usa el flujo implícito de OAuth y NO devuelve
/// `idToken` (que es lo que valida nuestro backend). El único flujo soportado
/// que sí lo entrega es este botón renderizado por Google; al completarse
/// dispara `onCurrentUserChanged` con la cuenta (y su idToken).
Widget renderGoogleWebButton() => web.renderButton();
