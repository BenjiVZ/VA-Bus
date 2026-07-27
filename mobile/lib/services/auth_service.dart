import 'package:dio/dio.dart';
import '../models/usuario.dart';
import 'api_client.dart';

class AuthService {
  final ApiClient client;
  AuthService(this.client);

  Future<({String access, String refresh, Usuario? usuario})> login(
    String username,
    String password,
  ) async {
    final res = await client.dio.post('/auth/login/', data: {
      'username': username,
      'password': password,
    });
    if (res.statusCode == null || res.statusCode! >= 400) {
      throw DioException(
        requestOptions: res.requestOptions,
        response: res,
        message: 'Login fallido',
      );
    }
    final data = res.data as Map<String, dynamic>;
    return (
      access: data['access'] as String,
      refresh: data['refresh'] as String,
      usuario: null,
    );
  }

  /// Intercambia el ID token de Google por JWT del backend.
  /// El backend valida el token contra Google y crea/recupera el usuario.
  Future<({String access, String refresh})> googleLogin(String idToken) async {
    final res = await client.dio.post(
      '/auth/google-login/',
      data: {'credential': idToken},
    );
    if (res.statusCode == null || res.statusCode! >= 400) {
      throw DioException(
        requestOptions: res.requestOptions,
        response: res,
        message: 'Google login fallido',
      );
    }
    final data = res.data as Map<String, dynamic>;
    // OJO: este endpoint devuelve los JWT ANIDADOS en "tokens"
    // ({tokens: {access, refresh}, usuario, nuevo_usuario}), a diferencia de
    // /auth/login/ que los manda planos. Aceptamos ambas formas.
    final tokens = (data['tokens'] is Map ? data['tokens'] : data) as Map;
    final access = tokens['access'];
    final refresh = tokens['refresh'];
    if (access is! String || refresh is! String) {
      throw DioException(
        requestOptions: res.requestOptions,
        response: res,
        message: 'La respuesta de Google login no trajo los tokens.',
      );
    }
    return (access: access, refresh: refresh);
  }

  Future<Usuario> registro({
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
    final res = await client.dio.post('/auth/registro/', data: {
      'username': username,
      'email': email,
      'password': password,
      'password2': password2,
      'first_name': firstName,
      'last_name': lastName,
      if (cedula != null) 'cedula': cedula,
      if (telefono != null) 'telefono': telefono,
      if (fechaNacimiento != null) 'fecha_nacimiento': fechaNacimiento,
    });
    if (res.statusCode == null || res.statusCode! >= 400) {
      throw DioException(requestOptions: res.requestOptions, response: res);
    }
    return Usuario.fromJson(res.data['usuario'] as Map<String, dynamic>);
  }

  Future<Usuario> getPerfil() async {
    final res = await client.dio.get('/auth/perfil/');
    if (res.statusCode != 200) {
      throw DioException(requestOptions: res.requestOptions, response: res);
    }
    return Usuario.fromJson(res.data as Map<String, dynamic>);
  }

  Future<Usuario> updatePerfil(Map<String, dynamic> data) async {
    final res = await client.dio.put('/auth/perfil/', data: data);
    if (res.statusCode == null || res.statusCode! >= 400) {
      throw DioException(requestOptions: res.requestOptions, response: res);
    }
    return Usuario.fromJson(res.data as Map<String, dynamic>);
  }

  Future<void> verificarEmail(String email, String codigo) async {
    final res = await client.dio.post('/auth/verificar-email/', data: {
      'email': email,
      'codigo': codigo,
    });
    if (res.statusCode == null || res.statusCode! >= 400) {
      throw DioException(requestOptions: res.requestOptions, response: res);
    }
  }

  Future<void> reenviarCodigo(String email) =>
      client.dio.post('/auth/reenviar-codigo/', data: {'email': email});

  Future<void> solicitarResetPassword(String email) =>
      client.dio.post('/auth/recuperar-password/', data: {'email': email});

  Future<void> resetPassword({
    required String email,
    required String codigo,
    required String newPassword,
    required String newPassword2,
  }) async {
    final res = await client.dio.post('/auth/reset-password/', data: {
      'email': email,
      'codigo': codigo,
      'new_password': newPassword,
      'new_password2': newPassword2,
    });
    if (res.statusCode == null || res.statusCode! >= 400) {
      throw DioException(requestOptions: res.requestOptions, response: res);
    }
  }

  Future<void> cambiarPassword({
    required String currentPassword,
    required String newPassword,
    required String newPassword2,
  }) async {
    final res = await client.dio.post('/auth/cambiar-password/', data: {
      'current_password': currentPassword,
      'new_password': newPassword,
      'new_password2': newPassword2,
    });
    if (res.statusCode == null || res.statusCode! >= 400) {
      throw DioException(requestOptions: res.requestOptions, response: res);
    }
  }
}
