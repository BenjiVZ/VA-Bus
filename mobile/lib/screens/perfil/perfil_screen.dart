import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../config/theme.dart';
import '../../providers/auth_provider.dart';
import '../shell.dart';

class PerfilScreen extends StatefulWidget {
  const PerfilScreen({super.key});

  @override
  State<PerfilScreen> createState() => _PerfilScreenState();
}

class _PerfilScreenState extends State<PerfilScreen> {
  final _firstName = TextEditingController();
  final _lastName = TextEditingController();
  final _cedula = TextEditingController();
  final _telefono = TextEditingController();
  bool _editing = false;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    final u = context.read<AuthProvider>().usuario;
    _firstName.text = u?.firstName ?? '';
    _lastName.text = u?.lastName ?? '';
    _cedula.text = u?.cedula ?? '';
    _telefono.text = u?.telefono ?? '';
  }

  @override
  void dispose() {
    for (final c in [_firstName, _lastName, _cedula, _telefono]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _guardar() async {
    setState(() => _saving = true);
    final ok = await context.read<AuthProvider>().updatePerfil({
      'first_name': _firstName.text.trim(),
      'last_name': _lastName.text.trim(),
      'cedula': _cedula.text.trim(),
      'telefono': _telefono.text.trim(),
    });
    if (!mounted) return;
    setState(() {
      _saving = false;
      if (ok) _editing = false;
    });
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(ok
          ? '✓ Perfil actualizado'
          : (context.read<AuthProvider>().lastError ?? 'Error.')),
    ));
  }

  Future<void> _confirmLogout() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('¿Cerrar sesión?'),
        content: const Text('Tendrás que iniciar sesión de nuevo para reservar.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancelar'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.red500),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Cerrar sesión'),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    await context.read<AuthProvider>().logout();
    if (!mounted) return;
    context.go('/');
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final u = auth.usuario;
    if (u == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    final inicial = u.firstName.isNotEmpty
        ? u.firstName[0].toUpperCase()
        : u.username[0].toUpperCase();

    return Scaffold(
      backgroundColor: AppColors.bgSecondary,
      body: CustomScrollView(
        slivers: [
          SliverToBoxAdapter(
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                Container(
                  height: 200,
                  decoration: const BoxDecoration(
                    gradient: AppColors.heroGradient,
                    borderRadius: BorderRadius.vertical(bottom: Radius.circular(28)),
                  ),
                  padding: EdgeInsets.fromLTRB(
                    20, MediaQuery.of(context).padding.top + 16, 20, 20,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Mi perfil',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 24,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      if (!_editing)
                        IconButton(
                          onPressed: () => setState(() => _editing = true),
                          icon: const Icon(Icons.edit_rounded, color: Colors.white),
                          style: IconButton.styleFrom(
                            backgroundColor: Colors.white.withValues(alpha: 0.15),
                          ),
                        ),
                    ],
                  ),
                ),
                Positioned(
                  left: 0, right: 0, bottom: -50,
                  child: Center(
                    child: Container(
                      width: 100, height: 100,
                      decoration: BoxDecoration(
                        gradient: AppColors.yellowGradient,
                        shape: BoxShape.circle,
                        border: Border.all(color: Colors.white, width: 4),
                        boxShadow: AppShadows.lg,
                      ),
                      alignment: Alignment.center,
                      child: Text(
                        inicial,
                        style: const TextStyle(
                          fontSize: 38,
                          color: AppColors.blue700,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          SliverToBoxAdapter(child: const SizedBox(height: 64)),
          SliverToBoxAdapter(
            child: Center(
              child: Text(
                u.fullName,
                style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textPrimary,
                ),
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: Center(
              child: Text(
                u.email,
                style: const TextStyle(color: AppColors.textTertiary),
              ),
            ),
          ),
          if (u.esVip)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Center(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                    decoration: BoxDecoration(
                      gradient: AppColors.yellowGradient,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.workspace_premium_rounded,
                            color: AppColors.blue700, size: 16),
                        const SizedBox(width: 6),
                        Text(
                          'VIP ${u.servicioVip.toUpperCase()}',
                          style: const TextStyle(
                            color: AppColors.blue700,
                            fontWeight: FontWeight.w800,
                            fontSize: 12,
                            letterSpacing: 1,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          SliverToBoxAdapter(child: const SizedBox(height: 24)),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, kFloatingNavHeight),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                _SectionCard(
                  title: 'Datos personales',
                  child: Column(
                    children: [
                      _Field(
                        label: 'Nombre',
                        controller: _firstName,
                        enabled: _editing,
                        icon: Icons.person_outline_rounded,
                      ),
                      _Field(
                        label: 'Apellido',
                        controller: _lastName,
                        enabled: _editing,
                        icon: Icons.person_outline_rounded,
                      ),
                      _Field(
                        label: 'Cédula',
                        controller: _cedula,
                        enabled: _editing,
                        icon: Icons.badge_outlined,
                      ),
                      _Field(
                        label: 'Teléfono',
                        controller: _telefono,
                        enabled: _editing,
                        icon: Icons.phone_outlined,
                        keyboardType: TextInputType.phone,
                      ),
                    ],
                  ),
                ),
                if (_editing) ...[
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: _saving
                              ? null
                              : () => setState(() => _editing = false),
                          child: const Text('Cancelar'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        flex: 2,
                        child: ElevatedButton.icon(
                          icon: _saving
                              ? const SizedBox(
                                  height: 16, width: 16,
                                  child: CircularProgressIndicator(
                                      strokeWidth: 2, color: Colors.white),
                                )
                              : const Icon(Icons.save_rounded),
                          label: Text(_saving ? 'Guardando…' : 'Guardar cambios'),
                          onPressed: _saving ? null : _guardar,
                        ),
                      ),
                    ],
                  ),
                ],
                const SizedBox(height: 16),
                _SectionCard(
                  title: 'Cuenta',
                  child: Column(
                    children: [
                      _MenuRow(
                        icon: Icons.confirmation_number_outlined,
                        title: 'Mis viajes',
                        onTap: () => context.go('/mis-reservas'),
                      ),
                      _MenuRow(
                        icon: Icons.lock_outline_rounded,
                        title: 'Cambiar contraseña',
                        onTap: () => context.push('/recuperar-password'),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),
                OutlinedButton.icon(
                  icon: const Icon(Icons.logout_rounded, color: AppColors.red500),
                  label: const Text('Cerrar sesión'),
                  onPressed: _confirmLogout,
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.red500,
                    side: const BorderSide(color: AppColors.red500, width: 1.5),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                ),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  final String title;
  final Widget child;
  const _SectionCard({required this.title, required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 4),
            child: Text(
              title.toUpperCase(),
              style: const TextStyle(
                fontSize: 11,
                letterSpacing: 1.2,
                fontWeight: FontWeight.w700,
                color: AppColors.textMuted,
              ),
            ),
          ),
          child,
        ],
      ),
    );
  }
}

class _Field extends StatelessWidget {
  final String label;
  final TextEditingController controller;
  final bool enabled;
  final IconData icon;
  final TextInputType? keyboardType;
  const _Field({
    required this.label,
    required this.controller,
    required this.enabled,
    required this.icon,
    this.keyboardType,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
      child: TextField(
        controller: controller,
        enabled: enabled,
        keyboardType: keyboardType,
        decoration: InputDecoration(
          labelText: label,
          prefixIcon: Icon(icon, size: 18),
          filled: enabled,
          fillColor: enabled ? AppColors.gray50 : Colors.transparent,
        ),
      ),
    );
  }
}

class _MenuRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final VoidCallback onTap;
  const _MenuRow({required this.icon, required this.title, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: [
            Icon(icon, color: AppColors.blue500, size: 20),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                title,
                style: const TextStyle(
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
            ),
            const Icon(Icons.chevron_right_rounded, color: AppColors.textMuted),
          ],
        ),
      ),
    );
  }
}
