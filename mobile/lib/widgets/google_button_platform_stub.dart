import 'package:flutter/widgets.dart';

/// Stub para plataformas NO web (Android/iOS): nunca se usa, porque el widget
/// solo llama a esto cuando kIsWeb es true. Existe para que el import
/// condicional compile en todas las plataformas.
Widget renderGoogleWebButton() => const SizedBox.shrink();
