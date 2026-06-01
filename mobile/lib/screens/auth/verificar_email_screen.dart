import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:pinput/pinput.dart';
import 'package:provider/provider.dart';
import '../../config/theme.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_client.dart';

class VerificarEmailScreen extends StatefulWidget {
  final String? initialEmail;
  const VerificarEmailScreen({super.key, this.initialEmail});

  @override
  State<VerificarEmailScreen> createState() => _VerificarEmailScreenState();
}

class _VerificarEmailScreenState extends State<VerificarEmailScreen> {
  final _email = TextEditingController();
  final _codigo = TextEditingController();
  bool _loading = false;

  // ── Themes Pinput ──
  PinTheme get _defaultPin => PinTheme(
        width: 48,
        height: 56,
        textStyle: const TextStyle(
          fontSize: 22,
          fontWeight: FontWeight.w800,
          color: AppColors.textPrimary,
        ),
        decoration: BoxDecoration(
          color: AppColors.gray50,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.borderStandard),
        ),
      );

  PinTheme get _focusedPin => _defaultPin.copyDecorationWith(
        color: Colors.white,
        border: Border.all(color: AppColors.blue500, width: 2),
        boxShadow: [
          BoxShadow(
            color: AppColors.blue500.withValues(alpha: 0.15),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      );

  PinTheme get _submittedPin => _defaultPin.copyDecorationWith(
        color: AppColors.blue50,
        border: Border.all(color: AppColors.blue500, width: 1.5),
      );

  @override
  void initState() {
    super.initState();
    if (widget.initialEmail != null) _email.text = widget.initialEmail!;
  }

  @override
  void dispose() {
    _email.dispose();
    _codigo.dispose();
    super.dispose();
  }

  Future<void> _verificar() async {
    if (_email.text.trim().isEmpty || _codigo.text.trim().length != 6) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Ingresa tu email y el código de 6 dígitos.')),
      );
      return;
    }
    setState(() => _loading = true);
    final auth = context.read<AuthProvider>();
    try {
      await auth.authService.verificarEmail(_email.text.trim(), _codigo.text.trim());
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Email verificado ✓ Inicia sesión.')),
      );
      context.go('/login');
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ApiClient.extractError(e))),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _reenviar() async {
    if (_email.text.trim().isEmpty) return;
    try {
      await context.read<AuthProvider>().authService.reenviarCodigo(_email.text.trim());
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Si el email existe, se envió un nuevo código.')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ApiClient.extractError(e))),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Verificar email')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Icon(Icons.mark_email_unread_outlined, size: 64, color: AppColors.blue500),
              const SizedBox(height: 16),
              const Text(
                'Revisa tu correo',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 6),
              const Text(
                'Te enviamos un código de 6 dígitos. Ingrésalo aquí para activar tu cuenta.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppColors.textTertiary),
              ),
              const SizedBox(height: 24),
              TextField(
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(labelText: 'Email'),
              ),
              const SizedBox(height: 20),
              Center(
                child: Pinput(
                  controller: _codigo,
                  length: 6,
                  keyboardType: TextInputType.number,
                  autofillHints: const [AutofillHints.oneTimeCode],
                  defaultPinTheme: _defaultPin,
                  focusedPinTheme: _focusedPin,
                  submittedPinTheme: _submittedPin,
                  pinputAutovalidateMode: PinputAutovalidateMode.onSubmit,
                  showCursor: true,
                  onCompleted: (_) => _verificar(),
                ),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _loading ? null : _verificar,
                child: _loading
                    ? const SizedBox(
                        height: 20, width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Text('Verificar'),
              ),
              TextButton(
                onPressed: _reenviar,
                child: const Text('Reenviar código'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
