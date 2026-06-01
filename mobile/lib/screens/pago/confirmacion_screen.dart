import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../config/theme.dart';

class ConfirmacionScreen extends StatelessWidget {
  final String grupoPago;
  const ConfirmacionScreen({super.key, required this.grupoPago});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(
                width: 88,
                height: 88,
                decoration: const BoxDecoration(
                  color: AppColors.green50,
                  shape: BoxShape.circle,
                ),
                alignment: Alignment.center,
                child: const Icon(Icons.check_rounded, size: 50, color: AppColors.green500),
              ).animate(),
              const SizedBox(height: 20),
              const Text(
                '¡Comprobante enviado!',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 8),
              const Text(
                'Tu pago está en revisión. Te enviaremos un correo cuando se valide. Mientras tanto, tu asiento queda apartado.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppColors.textTertiary),
              ),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                icon: const Icon(Icons.confirmation_number_outlined),
                label: const Text('Ver mis reservas'),
                onPressed: () => context.go('/mis-reservas'),
              ),
              const SizedBox(height: 8),
              OutlinedButton(
                onPressed: () => context.go('/'),
                child: const Text('Volver al inicio'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

extension _Anim on Widget {
  Widget animate() => TweenAnimationBuilder<double>(
        tween: Tween(begin: 0.0, end: 1.0),
        duration: const Duration(milliseconds: 500),
        curve: Curves.elasticOut,
        builder: (_, t, child) => Transform.scale(scale: t, child: child),
        child: this,
      );
}
