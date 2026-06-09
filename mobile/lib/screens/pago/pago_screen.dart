import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../../config/theme.dart';
import '../../models/metodo_pago.dart';
import '../../models/reserva.dart';
import '../../services/api_client.dart';
import '../../services/pagos_service.dart';
import '../../services/reservas_service.dart';
import '../../services/viajes_service.dart';

class PagoScreen extends StatefulWidget {
  final String grupoPago;
  final int viajeId;
  const PagoScreen({super.key, required this.grupoPago, required this.viajeId});

  @override
  State<PagoScreen> createState() => _PagoScreenState();
}

class _PagoScreenState extends State<PagoScreen> {
  bool _loading = true;
  String? _error;
  List<MetodoPago> _metodos = [];
  MetodoPago? _selected;

  final _ref = TextEditingController();
  final _monto = TextEditingController();
  XFile? _captura;
  XFile? _fotoBillete;
  bool _enviando = false;

  // ── Conversión a Bs en tiempo real ──
  double? _tasaBcv;       // Bs por 1 USD
  double? _precioUsd;     // precio de 1 asiento (del viaje)
  int _cantidadAsientos = 0;

  // ── Wizard de 3 pasos ──
  // 1: Elegir método
  // 2: Copiar datos bancarios
  // 3: Subir comprobante
  int _paso = 1;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  @override
  void dispose() {
    _ref.dispose();
    _monto.dispose();
    super.dispose();
  }

  Future<void> _cargar() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final pagos = context.read<PagosService>();
      final viajes = context.read<ViajesService>();
      final reservasSvc = context.read<ReservasService>();

      // Cargamos todo en paralelo. La tasa y las reservas pueden fallar
      // (sin red, sin auth, etc.) sin romper el flujo de pago.
      final results = await Future.wait([
        pagos.getMetodosPago(),
        viajes.getTasaCambio().catchError((_) => <String, dynamic>{}),
        viajes.getViaje(widget.viajeId).catchError((_) => <String, dynamic>{}),
        reservasSvc.getMisReservas().catchError((_) => <Reserva>[]),
      ]);

      if (!mounted) return;

      final tasaData = results[1] as Map<String, dynamic>;
      final viajeData = results[2] as Map<String, dynamic>;
      final misReservas = results[3] as List;

      final tasaRaw = tasaData['tasa_bcv'];
      double? tasa;
      if (tasaRaw is num) {
        tasa = tasaRaw.toDouble();
      } else if (tasaRaw is String) {
        tasa = double.tryParse(tasaRaw);
      }

      final precioRaw = viajeData['precio_usd'];
      double? precio;
      if (precioRaw is num) {
        precio = precioRaw.toDouble();
      } else if (precioRaw is String) {
        precio = double.tryParse(precioRaw);
      }

      final asientosDelGrupo = misReservas
          .where((r) => r.grupoPago == widget.grupoPago)
          .length;

      setState(() {
        _metodos = results[0] as List<MetodoPago>;
        _tasaBcv = tasa;
        _precioUsd = precio;
        _cantidadAsientos = asientosDelGrupo;
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

  /// Total a pagar en USD (asientos × precio).
  double? get _totalUsd {
    final p = _precioUsd;
    if (p == null || _cantidadAsientos == 0) return null;
    return p * _cantidadAsientos;
  }

  /// Total a pagar en Bs (totalUsd × tasaBcv). Null si falta tasa o precio.
  double? get _totalBs {
    final usd = _totalUsd;
    final tasa = _tasaBcv;
    if (usd == null || tasa == null) return null;
    return usd * tasa;
  }

  /// Texto del monto a mostrar/copiar según el método.
  /// Para método en USD muestra '$X.XX', para BS muestra 'Bs. X.XXX,XX' (es-VE).
  /// Devuelve null si no se pudo calcular (no rompe la UI).
  ({double valor, String texto})? _montoParaMetodo(MetodoPago metodo) {
    if (metodo.moneda == 'USD') {
      final usd = _totalUsd;
      if (usd == null) return null;
      return (valor: usd, texto: '\$${usd.toStringAsFixed(2)}');
    }
    final bs = _totalBs;
    if (bs == null) return null;
    final fmt = NumberFormat.currency(
      locale: 'es_VE',
      symbol: 'Bs. ',
      decimalDigits: 2,
    );
    return (valor: bs, texto: fmt.format(bs));
  }

  Future<XFile?> _pickImage() async {
    try {
      final picker = ImagePicker();
      return await picker.pickImage(
        source: ImageSource.gallery,
        imageQuality: 80,
        maxWidth: 1600,
      );
    } catch (_) {
      return null;
    }
  }

  Future<void> _enviar() async {
    if (_selected == null) {
      _toast('Selecciona un método de pago.');
      return;
    }
    if (_captura == null) {
      _toast('Sube la captura del pago.');
      return;
    }
    if (_selected!.requiereFotoBillete && _fotoBillete == null) {
      _toast('Sube la foto del billete.');
      return;
    }
    final monto = double.tryParse(_monto.text.replaceAll(',', '.'));
    if (monto == null || monto <= 0) {
      _toast('Ingresa un monto válido.');
      return;
    }

    setState(() => _enviando = true);
    try {
      await context.read<PagosService>().crearComprobante(
            grupoPago: widget.grupoPago,
            metodoPagoId: _selected!.id,
            numeroReferencia: _ref.text.trim(),
            monto: monto,
            moneda: _selected!.moneda,
            imagen: _captura!,
            fotoBillete: _fotoBillete,
          );
      if (!mounted) return;
      context.go('/reserva/confirmacion?grupo=${widget.grupoPago}');
    } catch (e) {
      if (!mounted) return;
      setState(() => _enviando = false);
      _toast(ApiClient.extractError(e));
    }
  }

  void _toast(String msg) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Pago'),
        leading: _paso > 1 && !_enviando
            ? IconButton(
                icon: const Icon(Icons.arrow_back_rounded),
                onPressed: () => setState(() => _paso -= 1),
              )
            : null,
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _buildError()
              : Column(
                  children: [
                    _StepHeader(paso: _paso),
                    Expanded(child: _buildPasoBody()),
                  ],
                ),
      bottomNavigationBar: (_loading || _error != null) ? null : _buildBottomBar(),
    );
  }

  Widget _buildError() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 48, color: AppColors.red500),
            const SizedBox(height: 8),
            Text(_error!, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            OutlinedButton(onPressed: _cargar, child: const Text('Reintentar')),
          ],
        ),
      ),
    );
  }

  Widget _buildPasoBody() {
    switch (_paso) {
      case 1:
        return _buildPaso1Metodo();
      case 2:
        return _buildPaso2Copiar();
      case 3:
        return _buildPaso3Comprobante();
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _buildPaso1Metodo() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          'Selecciona un método de pago',
          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
        ),
        const SizedBox(height: 4),
        const Text(
          'Toca el método con el que quieras pagar y luego presiona Continuar.',
          style: TextStyle(fontSize: 12, color: AppColors.textTertiary),
        ),
        const SizedBox(height: 12),
        ..._metodos.map((m) => _MetodoCard(
              metodo: m,
              selected: _selected?.id == m.id,
              onTap: () {
                // Cobro Inmediato (débito con OTP): flujo propio en otra pantalla.
                if (m.tipo == 'cobro_inmediato') {
                  context.push(
                      '/pago/cobro-inmediato?grupo=${widget.grupoPago}&viaje=${widget.viajeId}');
                  return;
                }
                setState(() => _selected = m);
                // Auto-llenar el campo monto con el total calculado
                final calc = _montoParaMetodo(m);
                if (calc != null) {
                  _monto.text = calc.valor.toStringAsFixed(2);
                }
              },
            )),
      ],
    );
  }

  Widget _buildPaso2Copiar() {
    final metodo = _selected!;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // ── Aviso azul: instrucción principal ──
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppColors.blue50,
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Row(
            children: [
              Icon(Icons.copy_all_rounded,
                  size: 18, color: AppColors.blue500),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Copia los datos y realiza el pago en tu app bancaria. Luego volvé acá y presiona "Ya pagué".',
                  style: TextStyle(
                    fontSize: 12,
                    color: AppColors.blue700,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 10),
        // ── Aviso amarillo: tiempo límite de 15 minutos ──
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppColors.yellow50,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.yellow400),
          ),
          child: const Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.access_time_rounded,
                  size: 18, color: AppColors.yellow600),
              SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      'Tenés 15 minutos para completar el pago',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w800,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    SizedBox(height: 2),
                    Text(
                      'Pasado ese tiempo, tu reserva se cancela automáticamente y los asientos quedan libres para otros usuarios.',
                      style: TextStyle(
                        fontSize: 11,
                        color: AppColors.textTertiary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 10),
        // ── Aviso gris: qué pasa si cerrás la app ──
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppColors.gray50,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.borderSubtle),
          ),
          child: const Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.info_outline_rounded,
                  size: 18, color: AppColors.blue500),
              SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '¿Cerraste o reiniciaste la app?',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w800,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    SizedBox(height: 2),
                    Text(
                      'No te preocupes. Al volver a abrirla verás un aviso naranja arriba con tu orden pendiente — tocalo y volvés directo a este pago.',
                      style: TextStyle(
                        fontSize: 11,
                        color: AppColors.textTertiary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        _SelectedMethodDetails(
          metodo: metodo,
          monto: _montoParaMetodo(metodo),
        ),
      ],
    );
  }

  Widget _buildPaso3Comprobante() {
    final metodo = _selected!;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          'Sube tu comprobante',
          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
        ),
        const SizedBox(height: 4),
        const Text(
          'Adjuntá la captura del pago y completa el monto y la referencia.',
          style: TextStyle(fontSize: 12, color: AppColors.textTertiary),
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _monto,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'[0-9.,]')),
          ],
          decoration: InputDecoration(
            labelText: 'Monto pagado (${metodo.moneda})',
            helperText: _montoParaMetodo(metodo) == null
                ? null
                : 'Se autocompletó con el total calculado.',
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _ref,
          decoration: const InputDecoration(
            labelText: 'Número de referencia',
            helperText: 'Opcional pero recomendado',
          ),
        ),
        const SizedBox(height: 16),
        _ImagePickerCard(
          title: 'Captura del pago *',
          file: _captura,
          onPick: () async {
            final f = await _pickImage();
            if (f != null) setState(() => _captura = f);
          },
          onClear: () => setState(() => _captura = null),
        ),
        if (metodo.requiereFotoBillete) ...[
          const SizedBox(height: 12),
          _ImagePickerCard(
            title: 'Foto del billete *',
            file: _fotoBillete,
            onPick: () async {
              final f = await _pickImage();
              if (f != null) setState(() => _fotoBillete = f);
            },
            onClear: () => setState(() => _fotoBillete = null),
          ),
        ],
      ],
    );
  }

  Widget _buildBottomBar() {
    return SafeArea(
      child: Container(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
        decoration: const BoxDecoration(
          color: Colors.white,
          border: Border(
            top: BorderSide(color: AppColors.borderSubtle),
          ),
        ),
        child: _buildPasoButton(),
      ),
    );
  }

  Widget _buildPasoButton() {
    switch (_paso) {
      case 1:
        final habilitado = _selected != null;
        return SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            icon: const Icon(Icons.arrow_forward_rounded),
            label: const Text(
              'Continuar',
              style: TextStyle(fontSize: 16),
            ),
            onPressed: habilitado ? () => setState(() => _paso = 2) : null,
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
              ),
            ),
          ),
        );
      case 2:
        return SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            icon: const Icon(Icons.check_rounded),
            label: const Text(
              'Ya pagué',
              style: TextStyle(fontSize: 16),
            ),
            onPressed: () => setState(() => _paso = 3),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
              ),
            ),
          ),
        );
      case 3:
        return SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            icon: _enviando
                ? const SizedBox(
                    height: 18,
                    width: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.upload_rounded),
            label: Text(
              _enviando ? 'Enviando…' : 'Enviar comprobante',
              style: const TextStyle(fontSize: 16),
            ),
            onPressed: _enviando ? null : _enviar,
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
              ),
            ),
          ),
        );
      default:
        return const SizedBox.shrink();
    }
  }
}

/// Header con indicador de progreso (3 pasos).
class _StepHeader extends StatelessWidget {
  final int paso;
  const _StepHeader({required this.paso});

  static const _labels = ['Método', 'Datos', 'Comprobante'];

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(
          bottom: BorderSide(color: AppColors.borderSubtle),
        ),
      ),
      child: Row(
        children: List.generate(_labels.length * 2 - 1, (i) {
          if (i.isOdd) {
            // Separador entre círculos
            final stepEnEsteSeparador = (i + 1) ~/ 2 + 1; // paso al que avanza
            final activo = paso >= stepEnEsteSeparador;
            return Expanded(
              child: Container(
                height: 2,
                margin: const EdgeInsets.symmetric(horizontal: 4),
                color: activo ? AppColors.blue500 : AppColors.borderStandard,
              ),
            );
          }
          final step = i ~/ 2 + 1;
          final activo = paso == step;
          final completo = paso > step;
          final color = completo
              ? AppColors.green500
              : activo
                  ? AppColors.blue500
                  : AppColors.gray300;
          return Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: color,
                ),
                alignment: Alignment.center,
                child: completo
                    ? const Icon(Icons.check_rounded,
                        size: 16, color: Colors.white)
                    : Text(
                        '$step',
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w800,
                          fontSize: 13,
                        ),
                      ),
              ),
              const SizedBox(height: 4),
              Text(
                _labels[step - 1],
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  color: activo || completo
                      ? AppColors.textPrimary
                      : AppColors.textTertiary,
                ),
              ),
            ],
          );
        }),
      ),
    );
  }
}

class _MetodoCard extends StatelessWidget {
  final MetodoPago metodo;
  final bool selected;
  final VoidCallback onTap;
  const _MetodoCard({required this.metodo, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Material(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(16),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              border: Border.all(
                color: selected ? AppColors.blue500 : AppColors.borderSubtle,
                width: selected ? 2 : 1,
              ),
              borderRadius: BorderRadius.circular(16),
              boxShadow: selected
                  ? [
                      BoxShadow(
                        color: AppColors.blue500.withValues(alpha: 0.12),
                        blurRadius: 16,
                        offset: const Offset(0, 6),
                      ),
                    ]
                  : null,
            ),
            child: Row(
              children: [
                // ── Ícono grande con fondo de color de la marca ──
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    color: _bgFor(metodo.tipo),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  alignment: Alignment.center,
                  child: Icon(
                    _iconFor(metodo.tipo),
                    color: _fgFor(metodo.tipo),
                    size: 28,
                  ),
                ),
                const SizedBox(width: 14),
                // ── Nombre + descripción + moneda ──
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Row(
                        children: [
                          Flexible(
                            child: Text(
                              metodo.nombre,
                              style: const TextStyle(
                                fontWeight: FontWeight.w800,
                                fontSize: 15,
                                color: AppColors.textPrimary,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          const SizedBox(width: 6),
                          // Moneda como mini-tag
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: metodo.moneda == 'USD'
                                  ? AppColors.green50
                                  : AppColors.blue50,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              metodo.moneda,
                              style: TextStyle(
                                color: metodo.moneda == 'USD'
                                    ? AppColors.green500
                                    : AppColors.blue500,
                                fontWeight: FontWeight.w800,
                                fontSize: 10,
                                letterSpacing: 0.5,
                              ),
                            ),
                          ),
                        ],
                      ),
                      if (metodo.descripcion.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(top: 3),
                          child: Text(
                            metodo.descripcion,
                            style: const TextStyle(
                              fontSize: 12,
                              color: AppColors.textTertiary,
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(width: 10),
                // ── Botón "Select" / "Activo" a la derecha ──
                AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  padding: const EdgeInsets.symmetric(
                      horizontal: 14, vertical: 9),
                  decoration: BoxDecoration(
                    color:
                        selected ? AppColors.blue500 : AppColors.gray50,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: selected
                          ? AppColors.blue500
                          : AppColors.borderStandard,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (selected)
                        const Padding(
                          padding: EdgeInsets.only(right: 4),
                          child: Icon(Icons.check_rounded,
                              color: Colors.white, size: 14),
                        ),
                      Text(
                        selected ? 'Activo' : 'Select',
                        style: TextStyle(
                          color: selected
                              ? Colors.white
                              : AppColors.textSecondary,
                          fontWeight: FontWeight.w700,
                          fontSize: 12,
                          letterSpacing: 0.2,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ── Colores de marca por tipo de pago ──
  Color _bgFor(String tipo) {
    switch (tipo) {
      case 'transferencia':
        return AppColors.blue50;
      case 'pago_movil':
        return AppColors.green50;
      case 'divisas':
        return AppColors.yellow50;
      case 'zinli':
      case 'zelle':
        return AppColors.blue50;
      case 'binance':
        return const Color(0xFFFFF3D6);
      default:
        return AppColors.gray100;
    }
  }

  Color _fgFor(String tipo) {
    switch (tipo) {
      case 'transferencia':
        return AppColors.blue500;
      case 'pago_movil':
        return AppColors.green500;
      case 'divisas':
        return AppColors.yellow600;
      case 'zinli':
      case 'zelle':
        return AppColors.blue500;
      case 'binance':
        return const Color(0xFFCB8F12);
      default:
        return AppColors.textSecondary;
    }
  }

  IconData _iconFor(String tipo) {
    switch (tipo) {
      case 'transferencia':
        return Icons.account_balance_rounded;
      case 'pago_movil':
        return Icons.phone_iphone_rounded;
      case 'divisas':
        return Icons.attach_money_rounded;
      case 'zinli':
      case 'zelle':
        return Icons.send_to_mobile_rounded;
      case 'binance':
        return Icons.currency_bitcoin_rounded;
      default:
        return Icons.payment_rounded;
    }
  }
}

class _SelectedMethodDetails extends StatelessWidget {
  final MetodoPago metodo;
  /// Monto a pagar (USD o Bs según la moneda del método). Si null, no se
  /// muestra el campo de Monto (ej. tasa BCV no disponible).
  final ({double valor, String texto})? monto;
  const _SelectedMethodDetails({required this.metodo, this.monto});

  void _copy(BuildContext context, String text, String etiqueta) {
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Copiado: $etiqueta')),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (metodo.datos.isEmpty && monto == null) {
      return const SizedBox.shrink();
    }
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Datos para pagar',
                style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            ...metodo.datos.map((d) => _row(
                  context,
                  etiqueta: d.etiqueta,
                  valor: d.valor,
                )),
            if (monto != null) ...[
              const Divider(height: 18),
              _row(
                context,
                etiqueta: 'Monto',
                valor: monto!.texto,
                // Lo que se copia es sólo el número (sin "Bs." ni "$"),
                // para pegar limpio en apps bancarias.
                valorParaCopiar: monto!.valor.toStringAsFixed(2),
                destacado: true,
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _row(
    BuildContext context, {
    required String etiqueta,
    required String valor,
    String? valorParaCopiar,
    bool destacado = false,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(etiqueta,
                    style: const TextStyle(
                      fontSize: 11,
                      color: AppColors.textTertiary,
                    )),
                Text(
                  valor,
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: destacado ? 16 : 14,
                    color: destacado
                        ? AppColors.blue700
                        : AppColors.textPrimary,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.copy, size: 18),
            tooltip: 'Copiar',
            onPressed: () => _copy(context, valorParaCopiar ?? valor, etiqueta),
          ),
        ],
      ),
    );
  }
}

class _ImagePickerCard extends StatelessWidget {
  final String title;
  final XFile? file;
  final VoidCallback onPick;
  final VoidCallback onClear;
  const _ImagePickerCard({
    required this.title,
    required this.file,
    required this.onPick,
    required this.onClear,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            if (file == null)
              OutlinedButton.icon(
                icon: const Icon(Icons.photo_library_outlined),
                label: const Text('Elegir imagen'),
                onPressed: onPick,
              )
            else
              Column(
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: _XFilePreview(file: file!),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          icon: const Icon(Icons.refresh),
                          label: const Text('Cambiar'),
                          onPressed: onPick,
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton(
                        icon: const Icon(Icons.delete_outline, color: AppColors.red500),
                        onPressed: onClear,
                      ),
                    ],
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

/// Preview cross-platform: lee bytes del XFile (funciona en Web e IO).
/// Image.file no funciona en Web; Image.memory sí.
class _XFilePreview extends StatelessWidget {
  final XFile file;
  const _XFilePreview({required this.file});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder(
      future: file.readAsBytes(),
      builder: (ctx, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const SizedBox(
            height: 160,
            child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
          );
        }
        if (snap.hasError || snap.data == null) {
          return const SizedBox(
            height: 160,
            child: Center(child: Icon(Icons.broken_image_outlined, size: 40)),
          );
        }
        return Image.memory(snap.data!, height: 160, fit: BoxFit.cover);
      },
    );
  }
}
