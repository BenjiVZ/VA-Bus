import 'dart:async';

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
  String? _error;

  // Datos del cliente
  final _cedula = TextEditingController();
  final _telefono = TextEditingController();
  final _nombre = TextEditingController();
  final _concepto = TextEditingController();
  final _otp = TextEditingController();

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
    _cedula.dispose();
    _telefono.dispose();
    _nombre.dispose();
    _concepto.dispose();
    _otp.dispose();
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
  Future<void> _generarOtp() async {
    final ced = _cedula.text.trim().toUpperCase();
    if (!RegExp(r'^[VEJP]\d{6,9}$').hasMatch(ced)) {
      setState(() => _error = 'Cédula inválida. Formato: V/E/J/P + 6 a 9 dígitos.');
      return;
    }
    if (!RegExp(r'^\d{11}$').hasMatch(_telefono.text.trim())) {
      setState(() => _error = 'El teléfono debe tener 11 dígitos (ej: 04141234567).');
      return;
    }
    if (_banco == null) {
      setState(() => _error = 'Selecciona tu banco.');
      return;
    }
    setState(() { _enviando = true; _error = null; });
    try {
      final data = await context.read<PagosService>().r4GenerarOtp(
            grupoPago: widget.grupoPago,
            banco: _banco!.codigo,
            cedula: ced,
            telefono: _telefono.text.trim(),
            nombre: _nombre.text.trim(),
            concepto: _concepto.text.trim(),
          );
      if (!mounted) return;
      final enviado = data['otp_enviado'] == true || data['code']?.toString() == '202';
      if (enviado) {
        setState(() {
          _operacionId = data['operacion_id'] as int?;
          _paso = 2;
          _enviando = false;
        });
      } else {
        setState(() {
          _error = (data['error'] ?? data['message'] ?? 'El banco no envió el OTP.').toString();
          _enviando = false;
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() { _error = ApiClient.extractError(e); _enviando = false; });
    }
  }

  Future<void> _confirmar() async {
    if (!RegExp(r'^\d{1,8}$').hasMatch(_otp.text.trim())) {
      setState(() => _error = 'Ingresa el OTP recibido (numérico).');
      return;
    }
    setState(() { _enviando = true; _error = null; });
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
    } else if (estado == 'en_espera') {
      setState(() { _paso = 3; _enviando = false; });
      _startPolling();
    } else {
      setState(() {
        _enviando = false;
        _error = 'El pago fue rechazado por el banco. Verifica tu saldo o tus datos.';
      });
    }
  }

  void _startPolling() {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 8), (t) async {
      if (_operacionId == null) return;
      try {
        final data = await context.read<PagosService>().r4EstadoOperacion(_operacionId!);
        final estado = data['estado']?.toString();
        if (estado == 'aceptada') {
          t.cancel();
          _irAConfirmacion();
        } else if (estado == 'rechazada') {
          t.cancel();
          if (mounted) setState(() { _paso = 2; _error = 'El pago fue rechazado por el banco.'; });
        }
      } catch (_) {/* reintentar */}
    });
  }

  void _irAConfirmacion() {
    if (!mounted) return;
    context.go('/reserva/confirmacion?grupo=${widget.grupoPago}');
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
        TextField(
          controller: _otp,
          keyboardType: TextInputType.number,
          maxLength: 8,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          decoration: const InputDecoration(labelText: 'Código OTP', hintText: '19807849', counterText: ''),
        ),
        const SizedBox(height: 12),
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
          child: Text(_enviando ? 'Procesando…' : 'Confirmar pago'),
        ),
        TextButton(
          onPressed: _enviando ? null : () => setState(() { _paso = 1; _error = null; }),
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
        children: const [
          SizedBox(width: 48, height: 48, child: CircularProgressIndicator()),
          SizedBox(height: 20),
          Text('Validando tu pago…',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          SizedBox(height: 8),
          Text(
            'El banco está procesando la operación. Tu silla queda reservada y se confirmará en cuanto el banco apruebe.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13, color: AppColors.textTertiary),
          ),
        ],
      ),
    );
  }
}
