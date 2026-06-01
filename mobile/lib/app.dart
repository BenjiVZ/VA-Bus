import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';
import 'config/router.dart';
import 'config/theme.dart';
import 'providers/auth_provider.dart';
import 'services/api_client.dart';
import 'services/pagos_service.dart';
import 'services/reservas_service.dart';
import 'services/storage_service.dart';
import 'services/viajes_service.dart';

class VaBusApp extends StatelessWidget {
  const VaBusApp({super.key});

  @override
  Widget build(BuildContext context) {
    final storage = StorageService();
    final client = ApiClient(storage: storage);

    return MultiProvider(
      providers: [
        Provider<StorageService>.value(value: storage),
        Provider<ApiClient>.value(value: client),
        Provider<ViajesService>(create: (_) => ViajesService(client)),
        Provider<ReservasService>(create: (_) => ReservasService(client)),
        Provider<PagosService>(create: (_) => PagosService(client)),
        ChangeNotifierProvider<AuthProvider>(
          create: (_) => AuthProvider(storage: storage, client: client)..bootstrap(),
        ),
      ],
      child: Builder(
        builder: (ctx) {
          return MaterialApp.router(
            title: 'Aerorutas de Venezuela',
            debugShowCheckedModeBanner: false,
            theme: AppTheme.light(),
            routerConfig: buildRouter(ctx),
            localizationsDelegates: const [
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            supportedLocales: const [
              Locale('es'),
              Locale('en'),
            ],
            locale: const Locale('es'),
          );
        },
      ),
    );
  }
}
