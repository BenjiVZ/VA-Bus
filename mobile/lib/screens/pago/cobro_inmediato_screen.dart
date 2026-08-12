import 'dart:async';

import 'package:dio/dio.dart' show DioException;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../../config/theme.dart';
import '../../models/banco.dart';
import '../../models/reserva.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_client.dart';
import '../../services/pagos_service.dart';
import '../../services/reservas_service.dart';
import '../../services/viajes_service.dart';

/// Flujo de "Cobro Inmediato" (Débito con OTP de R4 Conecta).
///   Paso 1: confirmar datos del cliente + banco + concepto -> Generar OTP
///   Paso 2: ingresar OTP (+ comprobante opcional) -> Confirmar débito
///   Paso 3: "en espera" (AC00) con polling hasta que el banco apruebe
class CobroInmediatoScreen extends StatefulWidget {
  final String grupoPago;
  final int viajeId;
  const CobroInmediatoScreen({super.key, required this.grupoPago, required this.viajeId});

  @override
  State<CobroInmediatoScreen> createState() => _CobroInmediatoScreenState();
}

class _CobroInmediatoScreenState extends State<CobroInmediatoScreen> {
  int _paso = 1;
  bool _loading = true;
  bool _enviando = false;
  bool _reenviando = false;
  String? _error;
  String? _aviso;

  // Datos del cliente
  final _cedula = TextEditingController();
  final _telefono = TextEditingController();
  final _nombre = TextEditingController();
  final _concepto = TextEditingController();
  final _otp = TextEditingController();
  final _focoOtp = FocusNode();

  // Bancos
  List<Banco> _bancos = [];
  Banco? _banco;

  // Monto (para mostrar)
  double? _tasaBcv;
  double? _precioUsd;
  int _cantidadAsientos = 0;

  // Operación
  int? _operacionId;
  XFile? _comprobante;
  Timer? _pollTimer;

  // Reenvío del OTP: el banco cobra/limita cada SMS, así que hay una espera
  // obligatoria entre un envío y el siguiente.
  static const _esperaReenvio = 60;
  int _restanteReenvio = 0;
  Timer? _cooldown;

  // Veces que el banco no aceptó el código: cambia el botón a "Reintentar".
  int _intentos = 0;

  @override
  void initState() {
    super.initState();
    final u = context.read<AuthProvider>().usuario;
    _cedula.text = u?.cedula ?? '';
    _telefono.text = u?.telefono ?? '';
    _nombre.text = u?.fullName ?? '';
    _cargar();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _cooldown?.cancel();
    _cedula.dispose();
    _telefono.dispose();
    _nombre.dispose();
    _concepto.dispose();
    _otp.dispose();
    _focoOtp.dispose();
    super.dispose();
  }

  double? get _totalBs {
    final p = _precioUsd, t = _tasaBcv;
    if (p == null || t == null || _cantidadAsientos == 0) return null;
    return p * _cantidadAsientos * t;
  }

  Future<void> _cargar() async {
    try {
      final pagos = context.read<PagosService>();
      final viajes = context.read<ViajesService>();
      final reservasSvc = context.read<ReservasService>();
      final results = await Future.wait([
        pagos.getBancos().catchError((_) => <Banco>[]),
        viajes.getTasaCambio().catchError((_) => <String, dynamic>{}),
        viajes.getViaje(widget.viajeId).catchError((_) => <String, dynamic>{}),
        reservasSvc.getMisReservas().catchError((_) => <Reserva>[]),
      ]);
      if (!mounted) return;
      final tasaData = results[1] as Map<String, dynamic>;
      final viajeData = results[2] as Map<String, dynamic>;
      final misReservas = results[3] as List;
      setState(() {
        _bancos = results[0] as List<Banco>;
        _tasaBcv = _toDouble(tasaData['tasa_bcv']);
        _precioUsd = _toDouble(viajeData['precio_usd']);
        _cantidadAsientos =
            misReservas.where((r) => r.grupoPago == widget.grupoPago).length;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = ApiClient.extractError(e);
        _loading = false;
      });
    }
  }

  static double? _toDouble(dynamic v) {
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v);
    return null;
  }

  // ── Selección de banco con buscador ──
  Future<void> _pickBanco() async {
    final seleccion = await showModalBottomSheet<Banco>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) {
        String filtro = '';
        return StatefulBuilder(builder: (ctx, setSheet) {
          final lista = _bancos.where((b) =>
              '${b.codigo} ${b.nombre}'.toLowerCase().contains(filtro.toLowerCase())).toList();
          return Padding(
            padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
            child: SizedBox(
              height: MediaQuery.of(ctx).size.height * 0.7,
              child: Column(
                children: [
                  const SizedBox(height: 12),
                  const Text('Selecciona tu banco', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                  Padding(
                    padding: const EdgeInsets.all(12),
                    child: TextField(
                      autofocus: true,
                      decoration: const InputDecoration(
                        hintText: 'Buscar por nombre o código…',
                        prefixIcon: Icon(Icons.search),
                      ),
                      onChanged: (v) => setSheet(() => filtro = v),
                    ),
                  ),
                  Expanded(
                    child: ListView.builder(
                      itemCount: lista.length,
                      itemBuilder: (_, i) {
                        final b = lista[i];
                        return ListTile(
                          title: Text(b.nombre),
                          leading: Text(b.codigo, style: const TextStyle(fontWeight: FontWeight.w700)),
                          onTap: () => Navigator.pop(ctx, b),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
          );
        });
      },
    );
    if (seleccion != null) setState(() => _banco = seleccion);
  }

  Future<void> _pickComprobante() async {
    final f = await ImagePicker().pickImage(
      source: ImageSource.gallery, imageQuality: 80, maxWidth: 1600);
    if (f != null) setState(() => _comprobante = f);
  }

  // ── Acciones ──
  Future<void> _generarOtp() => _pedirOtp();

  /// Pide otro SMS al banco. Genera una operación nueva (el OTP anterior queda
  /// sin usar) y limpia el campo para que nadie teclee el código viejo.
  Future<void> _reenviarOtp() => _pedirOtp(reenvio: true);

  Future<void> _pedirOtp({bool reenvio = false}) async {
    // El banco/validador esperan la cédula como letra + dígitos, SIN guion ni
    // espacios (ej: "V30719983"). El perfil la guarda como "V-30719983", así
    // que hay que limpiarla antes de validar y enviar (igual que la web).
    final ced = _cedula.text.trim().toUpperCase().replaceAll(RegExp(r'[^A-Z0-9]'), '');
    if (!RegExp(r'^[VEJP]\d{6,9}$').hasMatch(ced)) {
      setState(() => _error = 'Cédula inválida. Formato: V/E/J/P + 6 a 9 dígitos.');
      return;
    }
    final tel = _telefono.text.trim().replaceAll(RegExp(r'\D'), '');
    if (!RegExp(r'^\d{11}$').hasMatch(tel)) {
      setState(() => _error = 'El teléfono debe tener 11 dígitos (ej: 04141234567).');
      return;
    }
    if (_banco == null) {
      setState(() => _error = 'Selecciona tu banco.');
      return;
    }
    setState(() {
      if (reenvio) { _reenviando = true; } else { _enviando = true; }
      _error = null;
      _aviso = null;
    });
    try {
      final data = await context.read<PagosService>().r4GenerarOtp(
            grupoPago: widget.grupoPago,
            banco: _banco!.codigo,
            cedula: ced,
            telefono: tel,
            nombre: _nombre.text.trim(),
            concepto: _concepto.text.trim(),
          );
      if (!mounted) return;
      final enviado = data['otp_enviado'] == true || data['code']?.toString() == '202';
      if (enviado) {
        if (reenvio) _otp.clear();
        setState(() {
          _operacionId = data['operacion_id'] as int?;
          _paso = 2;
          _enviando = false;
          _reenviando = false;
          _aviso = reenvio ? 'Te enviamos un código nuevo. Usa el último que recibas.' : null;
        });
        _iniciarEsperaReenvio();
      } else {
        setState(() {
          _error = (data['error'] ?? data['message'] ?? 'El banco no envió el OTP.').toString();
          _enviando = false;
          _reenviando = false;
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _mensajeError(e);
        _enviando = false;
        _reenviando = false;
      });
      // El límite de envíos es temporal: dejar reintentar cuando pase la espera.
      if (reenvio) _iniciarEsperaReenvio();
    }
  }

  /// El 429 del backend viene en inglés ("Request was throttled…"); traducirlo.
  String _mensajeError(Object e) {
    if (e is DioException && e.response?.statusCode == 429) {
      return 'Pediste demasiados códigos seguidos. Espera un minuto e intenta otra vez.';
    }
    return ApiClient.extractError(e);
  }

  void _iniciarEsperaReenvio() {
    _cooldown?.cancel();
    setState(() => _restanteReenvio = _esperaReenvio);
    _cooldown = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted) { t.cancel(); return; }
      setState(() => _restanteReenvio--);
      if (_restanteReenvio <= 0) t.cancel();
    });
  }

  Future<void> _confirmar() async {
    if (!RegExp(r'^\d{1,8}$').hasMatch(_otp.text.trim())) {
      setState(() => _error = 'Ingresa el OTP recibido (numérico).');
      return;
    }
    setState(() { _enviando = true; _error = null; _aviso = null; });
    try {
      final data = await context.read<PagosService>().r4ConfirmarDebito(
            operacionId: _operacionId!,
            otp: _otp.text.trim(),
            comprobante: _comprobante,
          );
      if (!mounted) return;
      _aplicarEstado(data['estado']?.toString() ?? '');
    } catch (e) {
      if (!mounted) return;
      setState(() { _error = ApiClient.extractError(e); _enviando = false; });
    }
  }

  void _aplicarEstado(String estado) {
    if (estado == 'aceptada') {
      _irAConfirmacion();
      // 'procesando' NO es un rechazo: el débito sigue en curso, hay que
      // esperar igual que con 'en_espera'.
    } else if (estado == 'en_espera' || estado == 'procesando') {
      setState(() { _paso = 3; _enviando = false; });
      _startPolling();
    } else {
      _pedirCorregirOtp('El banco no aceptó el pago. Si escribiste mal el '
          'código, corrígelo y reintenta; si no, revisa tu saldo.');
    }
  }

  /// El banco no aceptó: dejar el campo vacío y con el teclado listo para
  /// reescribir el código. Antes había que borrarlo a mano, y no quedaba claro
  /// que se podía reintentar sin rehacer todo el flujo.
  ///
  /// El mismo OTP sigue sirviendo: el backend deja reconfirmar una operación
  /// que quedó 'rechazada' o en 'error'.
  void _pedirCorregirOtp(String mensaje) {
    if (!mounted) return;
    _otp.clear();
    _pollTimer?.cancel();
    setState(() {
      _paso = 2;
      _enviando = false;
      _aviso = null;
      _error = mensaje;
      _intentos++;
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _focoOtp.requestFocus();
    });
  }

  /// Cuánto se le sondea al banco con el usuario mirando la pantalla: 3 veces
  /// cada 8 s (~24 s). Si para entonces no resolvió, NO se deja al usuario
  /// girando: el asiento ya quedó apartado en el servidor y el boleto sigue su
  /// curso, así que se le manda a "Mis viajes" con el sello EN VALIDACIÓN.
  static const _maxSondeos = 3;
  static const _cadaSondeo = Duration(seconds: 8);
  int _sondeos = 0;

  void _startPolling() {
    _pollTimer?.cancel();
    _sondeos = 0;
    _sondear(); // primer intento ya: muchos AC00 se resuelven al preguntarle al banco
    _pollTimer = Timer.periodic(_cadaSondeo, (_) => _sondear());
  }

  Future<void> _sondear() async {
    if (_operacionId == null) return;
    try {
      final data = await context.read<PagosService>().r4EstadoOperacion(_operacionId!);
      if (!mounted) return;
      final estado = data['estado']?.toString();
      if (estado == 'aceptada') {
        _pollTimer?.cancel();
        _irAConfirmacion();
        return;
      }
      // 'rechazada' y 'error' son terminales: el banco no los cambia solo.
      if (estado == 'rechazada' || estado == 'error') {
        final msg = data['message']?.toString() ?? '';
        _pedirCorregirOtp(estado == 'rechazada'
            ? 'El banco no aceptó el pago. Si escribiste mal el código, '
                'corrígelo y reintenta; si no, revisa tu saldo.'
            : (msg.isNotEmpty ? msg : 'El banco reportó un error con la operación.'));
        return;
      }
    } catch (_) {/* reintentar en el próximo tick */}

    // Sigue 'en_espera'/'procesando': soltar al usuario al llegar al tope.
    if (++_sondeos > _maxSondeos) {
      _pollTimer?.cancel();
      _irAMisReservas();
    }
  }

  void _irAConfirmacion() {
    if (!mounted) return;
    context.go('/reserva/confirmacion?grupo=${widget.grupoPago}');
  }

  /// Saca al usuario de la espera. El pago no se pierde: el asiento quedó
  /// apartado y la reserva aparece como EN VALIDACIÓN hasta que el banco
  /// responda, momento en el que pasa sola a CONFIRMADO.
  void _irAMisReservas() {
    if (!mounted) return;
    _pollTimer?.cancel();
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        duration: Duration(seconds: 8),
        content: Text('Tu pago quedó en validación. El asiento está apartado y '
            'el boleto se confirma solo apenas el banco responda.'),
      ),
    );
    context.go('/mis-reservas');
  }

  // ── UI ──
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Cobro Inmediato')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : SafeArea(child: _body()),
    );
  }

  Widget _body() {
    switch (_paso) {
      case 2:
        return _pasoOtp();
      case 3:
        return _pasoEspera();
      default:
        return _pasoDatos();
    }
  }

  Widget _errorBox() {
    if (_error == null) return const SizedBox.shrink();
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.red500.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.red500.withValues(alpha: 0.4)),
      ),
      child: Text(_error!, style: const TextStyle(color: AppColors.red500)),
    );
  }

  Widget _avisoBox() {
    if (_aviso == null) return const SizedBox.shrink();
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.green500.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.green500.withValues(alpha: 0.4)),
      ),
      child: Row(
        children: [
          const Icon(Icons.mark_email_read_outlined,
              size: 18, color: AppColors.green500),
          const SizedBox(width: 8),
          Expanded(
            child: Text(_aviso!, style: const TextStyle(color: AppColors.green500)),
          ),
        ],
      ),
    );
  }

  Widget _pasoDatos() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text('Confirma tus datos',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
        const SizedBox(height: 4),
        const Text('Recibirás un código (OTP) en tu teléfono para autorizar el débito.',
            style: TextStyle(fontSize: 13, color: AppColors.textTertiary)),
        const SizedBox(height: 16),
        _errorBox(),
        TextField(
          controller: _cedula,
          decoration: const InputDecoration(labelText: 'Cédula', hintText: 'V12345678'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _telefono,
          keyboardType: TextInputType.phone,
          maxLength: 11,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          decoration: const InputDecoration(labelText: 'Teléfono', hintText: '04141234567', counterText: ''),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _nombre,
          decoration: const InputDecoration(labelText: 'Nombre'),
        ),
        const SizedBox(height: 12),
        // Selector de banco
        InkWell(
          onTap: _pickBanco,
          child: InputDecorator(
            decoration: const InputDecoration(labelText: 'Banco'),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    _banco == null ? 'Selecciona tu banco…' : '${_banco!.codigo} — ${_banco!.nombre}',
                    style: TextStyle(color: _banco == null ? AppColors.textTertiary : AppColors.textPrimary),
                  ),
                ),
                const Icon(Icons.arrow_drop_down),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _concepto,
          maxLength: 30,
          decoration: const InputDecoration(labelText: 'Concepto (opcional)', hintText: 'Pago de pasaje', counterText: ''),
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: AppColors.blue500.withValues(alpha: 0.06),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Monto a debitar', style: TextStyle(fontWeight: FontWeight.w600)),
              Text(
                _totalBs != null ? 'Bs. ${_totalBs!.toStringAsFixed(2)}' : 'Calculando…',
                style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.blue700),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),
        FilledButton(
          onPressed: _enviando ? null : _generarOtp,
          child: Text(_enviando ? 'Enviando OTP…' : 'Generar OTP'),
        ),
      ],
    );
  }

  Widget _pasoOtp() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text('Ingresa el código OTP',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
        const SizedBox(height: 4),
        Text('Enviamos un código a tu teléfono ${_telefono.text}. Ingrésalo para autorizar el débito.',
            style: const TextStyle(fontSize: 13, color: AppColors.textTertiary)),
        const SizedBox(height: 16),
        _errorBox(),
        _avisoBox(),
        TextField(
          controller: _otp,
          focusNode: _focoOtp,
          autofocus: true,
          keyboardType: TextInputType.number,
          maxLength: 8,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          // setState en cada tecla: quita el error viejo (si no, parece que el
          // rechazo sigue vigente mientras se reescribe) y refresca la X.
          onChanged: (_) => setState(() => _error = null),
          decoration: InputDecoration(
            labelText: 'Código OTP',
            hintText: '19807849',
            counterText: '',
            suffixIcon: _otp.text.isEmpty
                ? null
                : IconButton(
                    tooltip: 'Borrar',
                    icon: const Icon(Icons.close_rounded, size: 20),
                    onPressed: () => setState(_otp.clear),
                  ),
          ),
        ),
        // Reenviar: solo cuando pasó la espera y no hay otra petición en curso.
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            icon: Icon(
              _restanteReenvio > 0 ? Icons.timer_outlined : Icons.sms_outlined,
              size: 18,
            ),
            label: Text(
              _reenviando
                  ? 'Reenviando…'
                  : _restanteReenvio > 0
                      ? 'Reenviar código en ${_restanteReenvio}s'
                      : '¿No te llegó? Reenviar código',
              style: const TextStyle(fontSize: 13),
            ),
            onPressed: (_reenviando || _enviando || _restanteReenvio > 0)
                ? null
                : _reenviarOtp,
          ),
        ),
        const SizedBox(height: 4),
        // Comprobante opcional
        InkWell(
          onTap: _pickComprobante,
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.borderStandard),
            ),
            child: Column(
              children: [
                Icon(_comprobante == null ? Icons.image_outlined : Icons.check_circle,
                    color: _comprobante == null ? AppColors.textTertiary : AppColors.green500, size: 30),
                const SizedBox(height: 6),
                Text(_comprobante == null ? 'Adjuntar comprobante (opcional)' : 'Comprobante adjunto: ${_comprobante!.name}',
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 12, color: AppColors.textTertiary)),
              ],
            ),
          ),
        ),
        const SizedBox(height: 20),
        FilledButton(
          onPressed: _enviando ? null : _confirmar,
          child: Text(_enviando
              ? 'Procesando…'
              : _intentos > 0
                  ? 'Reintentar pago'
                  : 'Confirmar pago'),
        ),
        TextButton(
          onPressed: _enviando
              ? null
              : () => setState(() { _paso = 1; _error = null; _aviso = null; }),
          child: const Text('Volver'),
        ),
      ],
    );
  }

  Widget _pasoEspera() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const SizedBox(width: 48, height: 48, child: CircularProgressIndicator()),
          const SizedBox(height: 20),
          const Text('Validando tu pago…',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          const Text(
            'El banco está procesando la operación. Tu asiento ya quedó apartado: '
            'no lo pierdes aunque el banco tarde.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13, color: AppColors.textTertiary),
          ),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.blue500.withValues(alpha: 0.06),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Row(
              children: [
                Icon(Icons.info_outline_rounded, size: 18, color: AppColors.blue700),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'No hace falta esperar aquí. En "Mis viajes" verás el boleto '
                    'EN VALIDACIÓN y pasará a CONFIRMADO solo.',
                    style: TextStyle(fontSize: 12.5, color: AppColors.blue700),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          TextButton.icon(
            icon: const Icon(Icons.confirmation_number_outlined, size: 18),
            label: const Text('Ir a Mis viajes'),
            onPressed: _irAMisReservas,
          ),
        ],
      ),
    );
  }
}
