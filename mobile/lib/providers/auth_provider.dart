import 'package:flutter/foundation.dart';
import '../models/usuario.dart';
import '../services/api_client.dart';
import '../services/auth_service.dart';
import '../services/storage_service.dart';

enum AuthStatus { loading, authenticated, unauthenticated }

class AuthProvider extends ChangeNotifier {
  final StorageService storage;
  final ApiClient client;
  late final AuthService _auth;

  AuthStatus _status = AuthStatus.loading;
  Usuario? _usuario;
  String? _lastError;

  AuthProvider({required this.storage, required this.client}) {
    _auth = AuthService(client);
    client.onAuthLost = _onAuthLost;
  }

  AuthStatus get status => _status;
  Usuario? get usuario => _usuario;
  String? get lastError => _lastError;
  bool get isAuthenticated => _status == AuthStatus.authenticated;

  /// Llamar al arrancar la app: si hay tokens, intentar cargar el perfil.
  Future<void> bootstrap() async {
    final access = await storage.getAccessToken();
    if (access == null || access.isEmpty) {
      _status = AuthStatus.unauthenticated;
      notifyListeners();
      return;
    }
    try {
      _usuario = await _auth.getPerfil();
      _status = AuthStatus.authenticated;
    } catch (_) {
      await storage.clearTokens();
      _status = AuthStatus.unauthenticated;
    }
    notifyListeners();
  }

  Future<bool> login(String username, String password) async {
    _lastError = null;
    try {
      final res = await _auth.login(username, password);
      await storage.saveTokens(access: res.access, refresh: res.refresh);
      _usuario = await _auth.getPerfil();
      _status = AuthStatus.authenticated;
      notifyListeners();
      return true;
    } catch (e) {
      _lastError = ApiClient.extractError(e, fallback: 'Usuario o contraseña incorrectos.');
      notifyListeners();
      return false;
    }
  }

  /// Login con Google: recibe el ID token ya obtenido por GoogleSignIn
  /// y lo intercambia por JWT en el backend.
  Future<bool> loginConGoogle(String idToken) async {
    _lastError = null;
    try {
      final res = await _auth.googleLogin(idToken);
      await storage.saveTokens(access: res.access, refresh: res.refresh);
      _usuario = await _auth.getPerfil();
      _status = AuthStatus.authenticated;
      notifyListeners();
      return true;
    } catch (e) {
      _lastError =
          ApiClient.extractError(e, fallback: 'No se pudo iniciar con Google.');
      notifyListeners();
      return false;
    }
  }

  Future<bool> registro({
    required String username,
    required String email,
    required String password,
    required String password2,
    String firstName = '',
    String lastName = '',
    String? cedula,
    String? telefono,
    String? fechaNacimiento,
  }) async {
    _lastError = null;
    try {
      await _auth.registro(
        username: username,
        email: email,
        password: password,
        password2: password2,
        firstName: firstName,
        lastName: lastName,
        cedula: cedula,
        telefono: telefono,
        fechaNacimiento: fechaNacimiento,
      );
      return true;
    } catch (e) {
      _lastError = ApiClient.extractError(e, fallback: 'No se pudo registrar.');
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    await storage.clearTokens();
    _usuario = null;
    _status = AuthStatus.unauthenticated;
    notifyListeners();
  }

  Future<bool> refreshPerfil() async {
    try {
      _usuario = await _auth.getPerfil();
      notifyListeners();
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<bool> updatePerfil(Map<String, dynamic> data) async {
    _lastError = null;
    try {
      _usuario = await _auth.updatePerfil(data);
      notifyListeners();
      return true;
    } catch (e) {
      _lastError = ApiClient.extractError(e, fallback: 'No se pudo actualizar.');
      notifyListeners();
      return false;
    }
  }

  void _onAuthLost() {
    _usuario = null;
    _status = AuthStatus.unauthenticated;
    notifyListeners();
  }

  AuthService get authService => _auth;
}
