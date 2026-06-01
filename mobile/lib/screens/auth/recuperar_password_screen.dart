import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_client.dart';

class RecuperarPasswordScreen extends StatefulWidget {
  const RecuperarPasswordScreen({super.key});

  @override
  State<RecuperarPasswordScreen> createState() => _RecuperarPasswordScreenState();
}

class _RecuperarPasswordScreenState extends State<RecuperarPasswordScreen> {
  final _email = TextEditingController();
  final _codigo = TextEditingController();
  final _pass1 = TextEditingController();
  final _pass2 = TextEditingController();
  int _step = 0; // 0 = pedir email, 1 = código+nueva pass
  bool _loading = false;

  @override
  void dispose() {
    _email.dispose();
    _codigo.dispose();
    _pass1.dispose();
    _pass2.dispose();
    super.dispose();
  }

  Future<void> _solicitar() async {
    if (_email.text.trim().isEmpty) return;
    setState(() => _loading = true);
    try {
      await context.read<AuthProvider>().authService.solicitarResetPassword(_email.text.trim());
      if (!mounted) return;
      setState(() {
        _step = 1;
        _loading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Revisa tu email. Si está registrado recibirás un código.')),
      );
    } catch (e) {
      setState(() => _loading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ApiClient.extractError(e))),
      );
    }
  }

  Future<void> _restablecer() async {
    if (_codigo.text.trim().length != 6) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Código inválido.')),
      );
      return;
    }
    if (_pass1.text.length < 6) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Mínimo 6 caracteres.')),
      );
      return;
    }
    if (_pass1.text != _pass2.text) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Las contraseñas no coinciden.')),
      );
      return;
    }
    setState(() => _loading = true);
    try {
      await context.read<AuthProvider>().authService.resetPassword(
            email: _email.text.trim(),
            codigo: _codigo.text.trim(),
            newPassword: _pass1.text,
            newPassword2: _pass2.text,
          );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Contraseña restablecida. Inicia sesión.')),
      );
      context.go('/login');
    } catch (e) {
      setState(() => _loading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ApiClient.extractError(e))),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Recuperar contraseña')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_step == 0) ...[
                const Text(
                  'Ingresa tu email para recibir un código de recuperación.',
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _email,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(labelText: 'Email'),
                ),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: _loading ? null : _solicitar,
                  child: _loading
                      ? const SizedBox(
                          height: 20, width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Text('Enviar código'),
                ),
              ] else ...[
                Text('Email: ${_email.text}', style: const TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 12),
                TextField(
                  controller: _codigo,
                  keyboardType: TextInputType.number,
                  maxLength: 6,
                  decoration: const InputDecoration(
                    labelText: 'Código de 6 dígitos',
                    counterText: '',
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _pass1,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'Nueva contraseña'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _pass2,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'Repetir contraseña'),
                ),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: _loading ? null : _restablecer,
                  child: _loading
                      ? const SizedBox(
                          height: 20, width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Text('Restablecer'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
