import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../screens/auth/login_screen.dart';
import '../screens/auth/recuperar_password_screen.dart';
import '../screens/auth/register_screen.dart';
import '../screens/auth/verificar_email_screen.dart';
import '../screens/home/home_screen.dart';
import '../screens/pago/confirmacion_screen.dart';
import '../screens/pago/pago_screen.dart';
import '../screens/perfil/perfil_screen.dart';
import '../screens/reservas/mis_reservas_screen.dart';
import '../screens/reservas/ticket_screen.dart';
import '../screens/shell.dart';
import '../screens/viajes/asientos_screen.dart';
import '../screens/viajes/viajes_list_screen.dart';

final _rootKey = GlobalKey<NavigatorState>();
final _shellKey = GlobalKey<NavigatorState>();

GoRouter buildRouter(BuildContext context) {
  const protected = <String>{'/mis-reservas', '/perfil'};

  return GoRouter(
    initialLocation: '/',
    navigatorKey: _rootKey,
    refreshListenable: context.read<AuthProvider>(),
    redirect: (ctx, state) {
      final auth = ctx.read<AuthProvider>();
      if (auth.status == AuthStatus.loading) return null;
      final loc = state.matchedLocation;
      final isProtected = protected.any((p) => loc.startsWith(p));
      if (isProtected && !auth.isAuthenticated) return '/login';
      return null;
    },
    routes: [
      // Rutas fuera de la shell (sin bottom nav)
      GoRoute(path: '/login', parentNavigatorKey: _rootKey, builder: (_, _) => const LoginScreen()),
      GoRoute(path: '/registro', parentNavigatorKey: _rootKey, builder: (_, _) => const RegisterScreen()),
      GoRoute(
        path: '/verificar-email',
        parentNavigatorKey: _rootKey,
        builder: (_, s) => VerificarEmailScreen(initialEmail: s.uri.queryParameters['email']),
      ),
      GoRoute(
        path: '/recuperar-password',
        parentNavigatorKey: _rootKey,
        builder: (_, _) => const RecuperarPasswordScreen(),
      ),
      GoRoute(
        path: '/pago',
        parentNavigatorKey: _rootKey,
        builder: (_, s) => PagoScreen(
          grupoPago: s.uri.queryParameters['grupo']!,
          viajeId: int.parse(s.uri.queryParameters['viaje'] ?? '0'),
        ),
      ),
      GoRoute(
        path: '/reserva/confirmacion',
        parentNavigatorKey: _rootKey,
        builder: (_, s) => ConfirmacionScreen(grupoPago: s.uri.queryParameters['grupo']!),
      ),
      GoRoute(
        path: '/ticket/:grupo',
        parentNavigatorKey: _rootKey,
        builder: (_, s) => TicketScreen(grupoPago: s.pathParameters['grupo']!),
      ),

      // Rutas dentro de la shell (con bottom nav)
      ShellRoute(
        navigatorKey: _shellKey,
        builder: (_, _, child) => MainShell(child: child),
        routes: [
          GoRoute(path: '/', builder: (_, _) => const HomeScreen()),
          GoRoute(
            path: '/viajes',
            builder: (_, s) => ViajesListScreen(
              origen: s.uri.queryParameters['origen'],
              destino: s.uri.queryParameters['destino'],
              fecha: s.uri.queryParameters['fecha'],
            ),
            routes: [
              GoRoute(
                path: ':id/asientos',
                parentNavigatorKey: _rootKey,
                builder: (_, s) => AsientosScreen(
                  viajeId: int.parse(s.pathParameters['id']!),
                ),
              ),
            ],
          ),
          GoRoute(path: '/mis-reservas', builder: (_, _) => const MisReservasScreen()),
          GoRoute(path: '/perfil', builder: (_, _) => const PerfilScreen()),
        ],
      ),
    ],
  );
}
