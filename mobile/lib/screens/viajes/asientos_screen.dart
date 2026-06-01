import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../../config/theme.dart';
import '../../models/viaje.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_client.dart';
import '../../services/asientos_ws.dart';
import '../../services/reservas_service.dart';
import '../../services/viajes_service.dart';
import '../../widgets/atencion_dialog.dart';
import '../../widgets/pending_order_banner.dart';
import '../../widgets/route_map.dart';
import '../../widgets/seat_map.dart';

/// Estado por asiento — espeja seatOptions del frontend (AsientosPage.jsx).
class _SeatOpts {
  bool esMenor = false;
  bool paraOtra = false;
  bool viajaConAnimal = false;
  bool esDiscapacitado = false;
  String tipoMascota = '';
  // Asignado (sólo si paraOtra)
  String nombreAsignado = '';
  String cedulaAsignado = '';
  String cedulaTipoAsignado = 'V';
}

class _SeatFiles {
  // Menor (3 archivos)
  PlatformFile? partida;
  PlatformFile? foto;
  PlatformFile? cedulaRep;
  // Animal (1 archivo)
  PlatformFile? vacunacion;
  // Discapacidad (1 archivo)
  PlatformFile? discapacidad;
}

/// Pantalla de selección de asientos + datos del comprador + opciones/documentos por asiento.
/// Bloquea cada asiento al seleccionarlo (2 min server-side) y libera al deseleccionar.
class AsientosScreen extends StatefulWidget {
  final int viajeId;
  const AsientosScreen({super.key, required this.viajeId});

  @override
  State<AsientosScreen> createState() => _AsientosScreenState();
}

class _AsientosScreenState extends State<AsientosScreen> {
  bool _loading = true;
  String? _error;
  Viaje? _viaje;
  List<PisoConfig> _pisos = [];
  final List<SelectedSeat> _selected = [];
  bool _creando = false;

  // ── Datos del comprador ──
  final _nombreCtrl = TextEditingController();
  final _cedulaCtrl = TextEditingController();
  String _cedulaTipo = 'V';

  // ── Por asiento ──
  final Map<SelectedSeat, _SeatOpts> _seatOpts = {};
  final Map<SelectedSeat, _SeatFiles> _seatFiles = {};

  // ── WebSocket (tiempo real) ──
  AsientosWs? _ws;
  StreamSubscription? _wsSub;

  @override
  void initState() {
    super.initState();
    _cargar();
    _prefillBuyer();
    _conectarWs();
    // Re-evaluar validación cuando cambian los campos del comprador,
    // para activar/desactivar el botón Continuar en tiempo real.
    _nombreCtrl.addListener(_onFormChanged);
    _cedulaCtrl.addListener(_onFormChanged);
  }

  @override
  void dispose() {
    _wsSub?.cancel();
    _ws?.dispose();
    _nombreCtrl.removeListener(_onFormChanged);
    _cedulaCtrl.removeListener(_onFormChanged);
    _nombreCtrl.dispose();
    _cedulaCtrl.dispose();
    super.dispose();
  }

  void _onFormChanged() {
    if (mounted) setState(() {});
  }

  void _conectarWs() {
    final myId = context.read<AuthProvider>().usuario?.id;
    final ws = AsientosWs(viajeId: widget.viajeId);
    _ws = ws;
    _wsSub = ws.events.listen((evt) {
      // Si el evento lo originamos nosotros, lo ignoramos (estado local ya OK).
      if (myId != null && evt.usuarioId == myId) return;
      // Refrescamos el mapa — fuente de verdad sigue siendo el GET.
      if (mounted) _cargar();
    });
    ws.connect();
  }

  void _prefillBuyer() {
    final u = context.read<AuthProvider>().usuario;
    if (u == null) return;
    final nombre = '${u.firstName} ${u.lastName}'.trim();
    if (nombre.isNotEmpty) _nombreCtrl.text = nombre;

    final raw = u.cedula ?? '';
    final match = RegExp(r'^([VJEvje])-?(.*)$').firstMatch(raw);
    if (match != null) {
      _cedulaTipo = match.group(1)!.toUpperCase();
      _cedulaCtrl.text = match.group(2) ?? '';
    } else if (raw.isNotEmpty) {
      _cedulaCtrl.text = raw;
    }
  }

  Future<void> _cargar() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final r = await context.read<ViajesService>().getAsientos(widget.viajeId);
      if (!mounted) return;
      setState(() {
        _viaje = r.viaje;
        _pisos = r.pisos;
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

  Future<void> _onToggle(SelectedSeat seat) async {
    final auth = context.read<AuthProvider>();
    if (!auth.isAuthenticated) {
      _pedirLogin();
      return;
    }
    final svc = context.read<ReservasService>();
    final already = _selected.contains(seat);
    if (already) {
      setState(() {
        _selected.remove(seat);
        _seatOpts.remove(seat);
        _seatFiles.remove(seat);
      });
      try {
        await svc.liberarAsiento(
          viajeId: widget.viajeId,
          numeroAsiento: seat.numero,
          pisoAsiento: seat.piso,
        );
      } catch (_) {}
      return;
    }
    try {
      await svc.bloquearAsiento(
        viajeId: widget.viajeId,
        numeroAsiento: seat.numero,
        pisoAsiento: seat.piso,
      );
      if (!mounted) return;
      setState(() {
        _selected.add(seat);
        _seatOpts[seat] = _SeatOpts();
        _seatFiles[seat] = _SeatFiles();
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ApiClient.extractError(e))),
      );
      await _cargar();
    }
  }

  void _pedirLogin() {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Inicia sesión'),
        content: const Text('Necesitas una cuenta para reservar asientos.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancelar'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              context.push('/login');
            },
            child: const Text('Iniciar sesión'),
          ),
        ],
      ),
    );
  }

  Future<void> _pickFile({
    required bool allowPdf,
    required void Function(PlatformFile) onPicked,
  }) async {
    try {
      final res = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: allowPdf
            ? ['jpg', 'jpeg', 'png', 'webp', 'pdf']
            : ['jpg', 'jpeg', 'png', 'webp'],
        withData: true,
      );
      if (res == null || res.files.isEmpty) return;
      final f = res.files.first;
      if ((f.size) > 5 * 1024 * 1024) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('El archivo supera 5 MB.')),
        );
        return;
      }
      onPicked(f);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error seleccionando archivo: $e')),
      );
    }
  }

  String? _validar() {
    if (_nombreCtrl.text.trim().isEmpty) {
      return 'Ingresa el nombre completo del comprador.';
    }
    if (_cedulaCtrl.text.trim().isEmpty) {
      return 'Ingresa la cédula del comprador.';
    }
    for (final s in _selected) {
      final o = _seatOpts[s]!;
      final f = _seatFiles[s]!;
      if (o.paraOtra) {
        if (o.nombreAsignado.trim().isEmpty) {
          return 'Asiento #${s.numero}: ingresa el nombre del asignado.';
        }
        if (o.cedulaAsignado.trim().isEmpty) {
          return 'Asiento #${s.numero}: ingresa la cédula del asignado.';
        }
      }
      if (o.esMenor) {
        if (f.partida == null || f.foto == null || f.cedulaRep == null) {
          return 'Asiento #${s.numero}: faltan documentos del menor (partida, foto, cédula del representante).';
        }
      }
      if (o.viajaConAnimal) {
        if (o.tipoMascota.isEmpty) {
          return 'Asiento #${s.numero}: selecciona el tipo de mascota.';
        }
        if (f.vacunacion == null) {
          return 'Asiento #${s.numero}: falta la tarjeta de vacunación.';
        }
      }
      if (o.esDiscapacitado && f.discapacidad == null) {
        return 'Asiento #${s.numero}: falta el certificado de discapacidad.';
      }
    }
    return null;
  }

  Future<void> _continuar() async {
    if (_selected.isEmpty) return;
    final auth = context.read<AuthProvider>();
    if (!auth.isAuthenticated) {
      _pedirLogin();
      return;
    }

    final err = _validar();
    if (err != null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
      return;
    }

    // ── Modal de Atención (términos y condiciones) ──
    final viaje = _viaje;
    if (viaje != null) {
      final aceptado = await showAtencionDialog(
        context,
        info: AtencionViajeInfo(
          origen: viaje.ruta?.origen ?? '',
          destino: viaje.ruta?.destino ?? '',
          fecha: viaje.fechaSalida,
          cantidad: _selected.length,
        ),
      );
      if (aceptado != true) return; // canceló o cerró
      if (!mounted) return;
    }

    setState(() => _creando = true);
    try {
      final svc = context.read<ReservasService>();
      final asientosPayload = _selected.map((s) {
        final o = _seatOpts[s]!;
        return {
          'numero': s.numero,
          'piso': s.piso,
          'es_menor': o.esMenor,
          'para_otra': o.paraOtra,
          'viaja_con_animal': o.viajaConAnimal,
          'tipo_mascota': o.tipoMascota,
          'es_discapacitado': o.esDiscapacitado,
          'nombre_asignado': o.nombreAsignado,
          'cedula_asignado': o.cedulaAsignado.isEmpty
              ? ''
              : '${o.cedulaTipoAsignado}-${o.cedulaAsignado}',
        };
      }).toList();

      final res = await svc.crearReserva(
        viajeId: widget.viajeId,
        asientos: asientosPayload,
        nombrePasajero: _nombreCtrl.text.trim(),
        cedulaPasajero: '$_cedulaTipo-${_cedulaCtrl.text.trim()}',
      );

      // Subir docs (matchea por número+piso de asiento)
      final reservasCreadas = (res['reservas'] as List?) ?? const [];
      await _subirTodosLosDocs(svc, reservasCreadas);

      if (!mounted) return;
      final grupoPago = res['grupo_pago'] as String;
      context.go('/pago?grupo=$grupoPago&viaje=${widget.viajeId}');
    } catch (e) {
      if (!mounted) return;
      setState(() => _creando = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ApiClient.extractError(e))),
      );
    }
  }

  Future<void> _subirTodosLosDocs(
    ReservasService svc,
    List<dynamic> reservasCreadas,
  ) async {
    for (final r in reservasCreadas) {
      if (r is! Map) continue;
      final numero = (r['numero_asiento'] ?? 0) as int;
      final piso = (r['piso_asiento'] ?? 1) as int;
      final reservaId = (r['id'] ?? 0) as int;
      if (reservaId == 0) continue;

      final match = _selected.firstWhere(
        (s) => s.numero == numero && s.piso == piso,
        orElse: () => const SelectedSeat(numero: -1, piso: -1),
      );
      if (match.numero == -1) continue;
      final files = _seatFiles[match];
      final opts = _seatOpts[match];
      if (files == null || opts == null) continue;

      if (opts.esMenor &&
          files.partida != null &&
          files.foto != null &&
          files.cedulaRep != null) {
        try {
          await svc.subirDocumentosMenor(
            reservaId: reservaId,
            partida: files.partida!,
            foto: files.foto!,
            cedulaRep: files.cedulaRep!,
          );
        } catch (_) {/* no bloquear navegación */}
      }
      if (opts.viajaConAnimal && files.vacunacion != null) {
        try {
          await svc.subirDocVacunacion(
            reservaId: reservaId,
            file: files.vacunacion!,
          );
        } catch (_) {}
      }
      if (opts.esDiscapacitado && files.discapacidad != null) {
        try {
          await svc.subirDocDiscapacidad(
            reservaId: reservaId,
            file: files.discapacidad!,
          );
        } catch (_) {}
      }
    }
  }

  String _fmtFecha(String iso) {
    try {
      return DateFormat('EEE d MMM', 'es').format(DateTime.parse(iso));
    } catch (_) {
      return iso;
    }
  }

  @override
  Widget build(BuildContext context) {
    final viaje = _viaje;
    final total = viaje == null ? 0.0 : _selected.length * viaje.precioUsd;

    // Validación reactiva: si hay asientos seleccionados pero falta algo
    // (docs, datos del asignado, datos del comprador), el botón se
    // deshabilita y mostramos arriba el motivo exacto.
    final faltaCompletar = _selected.isEmpty ? null : _validar();
    final canContinue =
        _selected.isNotEmpty && !_creando && faltaCompletar == null;

    return Scaffold(
      appBar: AppBar(title: const Text('Selecciona tu asiento')),
      body: Column(
        children: [
          const PendingOrderBanner(),
          Expanded(child: _buildBody(viaje, total)),
        ],
      ),
      bottomNavigationBar: viaje == null
          ? null
          : SafeArea(
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.blue700.withOpacity(0.05),
                      blurRadius: 10,
                      offset: const Offset(0, -4),
                    ),
                  ],
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (faltaCompletar != null) ...[
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 8),
                        decoration: BoxDecoration(
                          color: AppColors.yellow50,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: AppColors.yellow400),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.warning_amber_rounded,
                                size: 16, color: AppColors.yellow600),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                faltaCompletar,
                                style: const TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.textPrimary,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 10),
                    ],
                    Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                '${_selected.length} asiento${_selected.length == 1 ? '' : 's'}',
                                style: const TextStyle(
                                  fontSize: 13,
                                  color: AppColors.textTertiary,
                                ),
                              ),
                              Text(
                                '\$${total.toStringAsFixed(2)} USD',
                                style: const TextStyle(
                                  fontSize: 24,
                                  fontWeight: FontWeight.w800,
                                  color: AppColors.blue700,
                                ),
                              ),
                            ],
                          ),
                        ),
                        ElevatedButton.icon(
                          icon: _creando
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.white,
                                  ),
                                )
                              : const Icon(Icons.arrow_forward),
                          label: Text(
                            _creando ? 'Reservando…' : 'Continuar',
                            style: const TextStyle(fontSize: 16),
                          ),
                          onPressed: canContinue ? _continuar : null,
                          style: ElevatedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 24, vertical: 16),
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(16)),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildBody(Viaje? viaje, double total) {
    return _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.error_outline,
                            size: 48, color: AppColors.red500),
                        const SizedBox(height: 12),
                        Text(_error!, textAlign: TextAlign.center),
                        const SizedBox(height: 16),
                        OutlinedButton(
                            onPressed: _cargar,
                            child: const Text('Reintentar')),
                      ],
                    ),
                  ),
                )
              : viaje == null
                  ? const SizedBox.shrink()
                  : SingleChildScrollView(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          _TripDetailCard(
                            viaje: viaje,
                            fecha: _fmtFecha(viaje.fechaSalida),
                          ),
                          const SizedBox(height: 16),
                          RouteMap(
                            origen: viaje.ruta?.origen ?? '',
                            destino: viaje.ruta?.destino ?? '',
                            height: 220,
                          ),
                          const SizedBox(height: 20),
                          _sectionHeader('Selecciona tu asiento'),
                          const SizedBox(height: 12),
                          SeatMap(
                            pisos: _pisos,
                            selectedSeats: _selected,
                            onToggleSeat: _onToggle,
                          ),
                          if (_selected.isNotEmpty) ...[
                            const SizedBox(height: 24),
                            _BuyerCard(
                              nombreCtrl: _nombreCtrl,
                              cedulaCtrl: _cedulaCtrl,
                              cedulaTipo: _cedulaTipo,
                              onTipoChanged: (v) =>
                                  setState(() => _cedulaTipo = v),
                              asignados: _selected
                                  .where(
                                      (s) => _seatOpts[s]?.paraOtra ?? false)
                                  .toList(),
                              seatOpts: _seatOpts,
                              onAsignadoChanged: () => setState(() {}),
                            ),
                            const SizedBox(height: 16),
                            _sectionHeader('Opciones por asiento'),
                            const SizedBox(height: 12),
                            ..._selected.map(
                              (s) => Padding(
                                padding: const EdgeInsets.only(bottom: 12),
                                child: _SeatOptionsCard(
                                  seat: s,
                                  opts: _seatOpts[s]!,
                                  files: _seatFiles[s]!,
                                  onChanged: () => setState(() {}),
                                  onPickFile: _pickFile,
                                ),
                              ),
                            ),
                          ],
                          const SizedBox(height: 80),
                        ],
                      ),
                    );
  }

  Widget _sectionHeader(String text) {
    return Row(
      children: [
        Container(
          width: 4,
          height: 18,
          decoration: BoxDecoration(
            color: AppColors.blue500,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 10),
        Text(
          text,
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w800,
            color: AppColors.textPrimary,
          ),
        ),
      ],
    );
  }
}

/// Card de "Datos del Comprador" + datos de cada asignado (si para_otra).
class _BuyerCard extends StatefulWidget {
  final TextEditingController nombreCtrl;
  final TextEditingController cedulaCtrl;
  final String cedulaTipo;
  final ValueChanged<String> onTipoChanged;
  final List<SelectedSeat> asignados;
  final Map<SelectedSeat, _SeatOpts> seatOpts;
  final VoidCallback onAsignadoChanged;

  const _BuyerCard({
    required this.nombreCtrl,
    required this.cedulaCtrl,
    required this.cedulaTipo,
    required this.onTipoChanged,
    required this.asignados,
    required this.seatOpts,
    required this.onAsignadoChanged,
  });

  @override
  State<_BuyerCard> createState() => _BuyerCardState();
}

class _BuyerCardState extends State<_BuyerCard> {
  // Controllers persistentes por asiento asignado.
  final Map<SelectedSeat, TextEditingController> _nombreCtrls = {};
  final Map<SelectedSeat, TextEditingController> _cedulaCtrls = {};

  TextEditingController _ctrlFor(
    Map<SelectedSeat, TextEditingController> map,
    SelectedSeat seat,
    String initial,
  ) {
    final existing = map[seat];
    if (existing != null) return existing;
    final c = TextEditingController(text: initial);
    map[seat] = c;
    return c;
  }

  @override
  void didUpdateWidget(covariant _BuyerCard old) {
    super.didUpdateWidget(old);
    // Limpiar controllers de asientos que ya no están asignados.
    final stillAsignados = widget.asignados.toSet();
    final toRemove = _nombreCtrls.keys
        .where((k) => !stillAsignados.contains(k))
        .toList();
    for (final k in toRemove) {
      _nombreCtrls.remove(k)?.dispose();
      _cedulaCtrls.remove(k)?.dispose();
    }
  }

  @override
  void dispose() {
    for (final c in _nombreCtrls.values) {
      c.dispose();
    }
    for (final c in _cedulaCtrls.values) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final nombreCtrl = widget.nombreCtrl;
    final cedulaCtrl = widget.cedulaCtrl;
    final cedulaTipo = widget.cedulaTipo;
    final onTipoChanged = widget.onTipoChanged;
    final asignados = widget.asignados;
    final seatOpts = widget.seatOpts;
    final onAsignadoChanged = widget.onAsignadoChanged;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderSubtle),
        boxShadow: AppShadows.sm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Row(
            children: [
              Icon(Icons.person_outline_rounded,
                  size: 18, color: AppColors.blue500),
              SizedBox(width: 8),
              Text(
                'Datos del Comprador',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          _LabeledField(
            label: 'Nombre Completo',
            child: TextField(
              controller: nombreCtrl,
              decoration: _decoration('Nombre y apellido'),
            ),
          ),
          const SizedBox(height: 12),
          _LabeledField(
            label: 'Cédula',
            child: Row(
              children: [
                SizedBox(
                  width: 76,
                  child: DropdownButtonFormField<String>(
                    initialValue: cedulaTipo,
                    decoration: _decoration(''),
                    items: const [
                      DropdownMenuItem(value: 'V', child: Text('V')),
                      DropdownMenuItem(value: 'J', child: Text('J')),
                      DropdownMenuItem(value: 'E', child: Text('E')),
                    ],
                    onChanged: (v) {
                      if (v != null) onTipoChanged(v);
                    },
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: cedulaCtrl,
                    keyboardType: TextInputType.number,
                    decoration: _decoration('12345678'),
                  ),
                ),
              ],
            ),
          ),
          // Datos del asignado por cada asiento marcado "para otra persona"
          for (final seat in asignados) ...[
            const SizedBox(height: 16),
            const Divider(height: 1, color: AppColors.borderSubtle),
            const SizedBox(height: 12),
            Row(
              children: [
                const Icon(Icons.person_add_alt_1_rounded,
                    size: 16, color: AppColors.blue500),
                const SizedBox(width: 6),
                Text(
                  'Persona Asignada — Asiento #${seat.numero}',
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                    color: AppColors.textPrimary,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            _LabeledField(
              label: 'Nombre del asignado',
              child: TextField(
                controller: _ctrlFor(
                    _nombreCtrls, seat, seatOpts[seat]!.nombreAsignado),
                decoration: _decoration('Nombre y apellido'),
                onChanged: (v) {
                  seatOpts[seat]!.nombreAsignado = v;
                  onAsignadoChanged();
                },
              ),
            ),
            const SizedBox(height: 10),
            _LabeledField(
              label: 'Cédula del asignado',
              child: Row(
                children: [
                  SizedBox(
                    width: 76,
                    child: DropdownButtonFormField<String>(
                      initialValue: seatOpts[seat]!.cedulaTipoAsignado,
                      decoration: _decoration(''),
                      items: const [
                        DropdownMenuItem(value: 'V', child: Text('V')),
                        DropdownMenuItem(value: 'J', child: Text('J')),
                        DropdownMenuItem(value: 'E', child: Text('E')),
                      ],
                      onChanged: (v) {
                        if (v != null) {
                          seatOpts[seat]!.cedulaTipoAsignado = v;
                          onAsignadoChanged();
                        }
                      },
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      controller: _ctrlFor(
                          _cedulaCtrls, seat, seatOpts[seat]!.cedulaAsignado),
                      keyboardType: TextInputType.number,
                      decoration: _decoration('12345678'),
                      onChanged: (v) {
                        final digits = v.replaceAll(RegExp(r'\D'), '');
                        seatOpts[seat]!.cedulaAsignado = digits;
                        if (digits != v) {
                          final c = _cedulaCtrls[seat]!;
                          c.value = TextEditingValue(
                            text: digits,
                            selection:
                                TextSelection.collapsed(offset: digits.length),
                          );
                        }
                        onAsignadoChanged();
                      },
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  InputDecoration _decoration(String hint) => InputDecoration(
        hintText: hint,
        isDense: true,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppColors.borderStandard),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppColors.borderStandard),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppColors.blue500, width: 1.5),
        ),
      );
}

class _LabeledField extends StatelessWidget {
  final String label;
  final Widget child;
  const _LabeledField({required this.label, required this.child});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w700,
            color: AppColors.textTertiary,
          ),
        ),
        const SizedBox(height: 6),
        child,
      ],
    );
  }
}

/// Card de opciones (permisos + docs) por asiento individual.
class _SeatOptionsCard extends StatelessWidget {
  final SelectedSeat seat;
  final _SeatOpts opts;
  final _SeatFiles files;
  final VoidCallback onChanged;
  final Future<void> Function({
    required bool allowPdf,
    required void Function(PlatformFile) onPicked,
  }) onPickFile;

  const _SeatOptionsCard({
    required this.seat,
    required this.opts,
    required this.files,
    required this.onChanged,
    required this.onPickFile,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderSubtle),
        boxShadow: AppShadows.sm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.blue50,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  'Asiento #${seat.numero}',
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                    color: AppColors.blue700,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '· Piso ${seat.piso}',
                style: const TextStyle(
                  fontSize: 12,
                  color: AppColors.textTertiary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: AppColors.gray50,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: AppColors.borderSubtle,
                style: BorderStyle.solid,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.shield_outlined,
                        size: 14, color: AppColors.blue500),
                    SizedBox(width: 6),
                    Text(
                      'PERMISOS PARA VIAJAR',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        color: AppColors.textTertiary,
                        letterSpacing: 1.2,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                _checkRow(
                  icon: Icons.child_care_rounded,
                  label: 'Es menor de edad',
                  value: opts.esMenor,
                  onChanged: (v) {
                    opts.esMenor = v ?? false;
                    onChanged();
                  },
                ),
                _checkRow(
                  icon: Icons.pets_rounded,
                  label: 'Viaja con animal',
                  value: opts.viajaConAnimal,
                  onChanged: (v) {
                    opts.viajaConAnimal = v ?? false;
                    onChanged();
                  },
                ),
                _checkRow(
                  icon: Icons.accessible_rounded,
                  label: 'Persona con discapacidad',
                  value: opts.esDiscapacitado,
                  onChanged: (v) {
                    opts.esDiscapacitado = v ?? false;
                    onChanged();
                  },
                ),
              ],
            ),
          ),
          // ── Sección separada: Asignación ──
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: AppColors.gray50,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppColors.borderSubtle),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.person_add_alt_1_rounded,
                        size: 14, color: AppColors.blue500),
                    SizedBox(width: 6),
                    Text(
                      'ASIGNACIÓN',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        color: AppColors.textTertiary,
                        letterSpacing: 1.2,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                _checkRow(
                  icon: Icons.person_add_alt_1_rounded,
                  label: 'Asignar a otra persona',
                  value: opts.paraOtra,
                  onChanged: (v) {
                    opts.paraOtra = v ?? false;
                    onChanged();
                  },
                ),
                if (opts.paraOtra)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: AppColors.blue50,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Row(
                        children: [
                          Icon(Icons.info_outline_rounded,
                              size: 14, color: AppColors.blue500),
                          SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              'Los datos del asignado se llenan en "Datos del Comprador".',
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
                  ),
              ],
            ),
          ),
          // ── Botón "Subir documentos" si hay alguno requerido ──
          if (_docsRequeridos(opts) > 0) ...[
            const SizedBox(height: 10),
            _DocsButton(
              total: _docsRequeridos(opts),
              subidos: _docsSubidos(opts, files),
              onTap: () async {
                await showModalBottomSheet<void>(
                  context: context,
                  isScrollControlled: true,
                  backgroundColor: Colors.transparent,
                  builder: (_) => _DocsBottomSheet(
                    seat: seat,
                    opts: opts,
                    files: files,
                    onPickFile: onPickFile,
                  ),
                );
                onChanged(); // refrescar contadores al cerrar
              },
            ),
          ],
        ],
      ),
    );
  }

  /// Cantidad total de documentos requeridos según los toggles activos.
  int _docsRequeridos(_SeatOpts opts) {
    var n = 0;
    if (opts.esMenor) n += 3;
    if (opts.viajaConAnimal) n += 1;
    if (opts.esDiscapacitado) n += 1;
    return n;
  }

  /// Cantidad de documentos ya subidos.
  int _docsSubidos(_SeatOpts opts, _SeatFiles files) {
    var n = 0;
    if (opts.esMenor) {
      if (files.partida != null) n++;
      if (files.foto != null) n++;
      if (files.cedulaRep != null) n++;
    }
    if (opts.viajaConAnimal && files.vacunacion != null) n++;
    if (opts.esDiscapacitado && files.discapacidad != null) n++;
    return n;
  }

  Widget _checkRow({
    required IconData icon,
    required String label,
    required bool value,
    required ValueChanged<bool?> onChanged,
  }) {
    return InkWell(
      onTap: () => onChanged(!value),
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          children: [
            SizedBox(
              width: 22,
              height: 22,
              child: Checkbox(
                value: value,
                onChanged: onChanged,
                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                visualDensity: VisualDensity.compact,
              ),
            ),
            const SizedBox(width: 10),
            Icon(icon, size: 16, color: AppColors.textTertiary),
            const SizedBox(width: 6),
            Expanded(
              child: Text(
                label,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

}

/// Botón "Subir documentos · 1/3" que aparece en la card del asiento
/// cuando hay algún permiso activo que requiere documentos.
class _DocsButton extends StatelessWidget {
  final int subidos;
  final int total;
  final VoidCallback onTap;

  const _DocsButton({
    required this.subidos,
    required this.total,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final completo = subidos >= total;
    final pendientes = total - subidos;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          decoration: BoxDecoration(
            color: completo ? AppColors.green50 : AppColors.yellow50,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: completo ? AppColors.green500 : AppColors.yellow400,
            ),
          ),
          child: Row(
            children: [
              Icon(
                completo
                    ? Icons.check_circle_rounded
                    : Icons.upload_file_rounded,
                size: 18,
                color: completo ? AppColors.green500 : AppColors.yellow600,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      completo
                          ? 'Documentos completos'
                          : 'Subir documentos',
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w800,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    Text(
                      completo
                          ? '$subidos de $total subidos'
                          : '$pendientes ${pendientes == 1 ? "pendiente" : "pendientes"} · toca para subir',
                      style: const TextStyle(
                        fontSize: 11,
                        color: AppColors.textTertiary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: completo ? AppColors.green500 : AppColors.yellow600,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  '$subidos/$total',
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    color: Colors.white,
                  ),
                ),
              ),
              const SizedBox(width: 4),
              Icon(
                Icons.arrow_forward_ios_rounded,
                size: 12,
                color: AppColors.textTertiary,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Bottom sheet con los documentos del asiento (menor / mascota / discapacidad).
/// Es stateful para refrescar el preview cuando se sube un archivo desde
/// dentro del sheet sin cerrarlo.
class _DocsBottomSheet extends StatefulWidget {
  final SelectedSeat seat;
  final _SeatOpts opts;
  final _SeatFiles files;
  final Future<void> Function({
    required bool allowPdf,
    required void Function(PlatformFile) onPicked,
  }) onPickFile;

  const _DocsBottomSheet({
    required this.seat,
    required this.opts,
    required this.files,
    required this.onPickFile,
  });

  @override
  State<_DocsBottomSheet> createState() => _DocsBottomSheetState();
}

class _DocsBottomSheetState extends State<_DocsBottomSheet> {
  _SeatOpts get opts => widget.opts;
  _SeatFiles get files => widget.files;

  @override
  Widget build(BuildContext context) {
    final media = MediaQuery.of(context);
    return DraggableScrollableSheet(
      initialChildSize: 0.7,
      minChildSize: 0.4,
      maxChildSize: 0.95,
      expand: false,
      builder: (_, scrollCtrl) {
        return Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            children: [
              // Grabber
              Container(
                margin: const EdgeInsets.only(top: 10, bottom: 4),
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: AppColors.gray300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              // Header
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 12, 12, 8),
                child: Row(
                  children: [
                    const Icon(Icons.folder_open_rounded,
                        size: 22, color: AppColors.blue500),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            'Documentos · Asiento #${widget.seat.numero}',
                            style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w800,
                              color: AppColors.textPrimary,
                            ),
                          ),
                          const Text(
                            'PDF o imagen (máx. 5 MB cada uno)',
                            style: TextStyle(
                              fontSize: 11,
                              color: AppColors.textTertiary,
                            ),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close_rounded),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ],
                ),
              ),
              const Divider(height: 1, color: AppColors.borderSubtle),
              Expanded(
                child: ListView(
                  controller: scrollCtrl,
                  padding: EdgeInsets.fromLTRB(
                      16, 12, 16, 16 + media.padding.bottom),
                  children: [
                    if (opts.esMenor)
                      _docsBlock(
                        title: 'Documentos del menor',
                        icon: Icons.child_care_rounded,
                        warning:
                            'Se requiere autorización del padre, madre o representante legal expedida por la autoridad competente.',
                        children: [
                          _fileTile(
                            label: 'Partida de nacimiento',
                            file: files.partida,
                            icon: Icons.description_rounded,
                            onPick: () => widget.onPickFile(
                              allowPdf: true,
                              onPicked: (f) =>
                                  setState(() => files.partida = f),
                            ),
                          ),
                          _fileTile(
                            label: 'Foto del menor',
                            file: files.foto,
                            icon: Icons.photo_camera_rounded,
                            onPick: () => widget.onPickFile(
                              allowPdf: false,
                              onPicked: (f) => setState(() => files.foto = f),
                            ),
                          ),
                          _fileTile(
                            label: 'Cédula del representante',
                            file: files.cedulaRep,
                            icon: Icons.credit_card_rounded,
                            onPick: () => widget.onPickFile(
                              allowPdf: true,
                              onPicked: (f) =>
                                  setState(() => files.cedulaRep = f),
                            ),
                          ),
                        ],
                      ),
                    if (opts.viajaConAnimal) ...[
                      const SizedBox(height: 12),
                      _docsBlock(
                        title: 'Datos de la mascota',
                        icon: Icons.pets_rounded,
                        warning:
                            'Llevar tarjeta de vacunación EN FÍSICO al abordar.',
                        children: [
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: DropdownButtonFormField<String>(
                              initialValue: opts.tipoMascota.isEmpty
                                  ? null
                                  : opts.tipoMascota,
                              decoration: InputDecoration(
                                labelText: 'Tipo de mascota',
                                isDense: true,
                                contentPadding: const EdgeInsets.symmetric(
                                    horizontal: 12, vertical: 11),
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(10),
                                  borderSide: const BorderSide(
                                      color: AppColors.borderStandard),
                                ),
                              ),
                              items: const [
                                DropdownMenuItem(
                                    value: 'perro', child: Text('🐕 Perro')),
                                DropdownMenuItem(
                                    value: 'gato', child: Text('🐈 Gato')),
                                DropdownMenuItem(
                                    value: 'ave', child: Text('🐦 Ave')),
                                DropdownMenuItem(
                                    value: 'conejo', child: Text('🐰 Conejo')),
                                DropdownMenuItem(
                                    value: 'hamster',
                                    child: Text('🐹 Hámster')),
                                DropdownMenuItem(
                                    value: 'otro', child: Text('🐾 Otro')),
                              ],
                              onChanged: (v) =>
                                  setState(() => opts.tipoMascota = v ?? ''),
                            ),
                          ),
                          _fileTile(
                            label: 'Tarjeta de vacunación',
                            file: files.vacunacion,
                            icon: Icons.description_rounded,
                            onPick: () => widget.onPickFile(
                              allowPdf: true,
                              onPicked: (f) =>
                                  setState(() => files.vacunacion = f),
                            ),
                          ),
                        ],
                      ),
                    ],
                    if (opts.esDiscapacitado) ...[
                      const SizedBox(height: 12),
                      _docsBlock(
                        title: 'Documento de discapacidad',
                        icon: Icons.accessible_rounded,
                        warning: 'Llevar documento EN FÍSICO al abordar.',
                        children: [
                          _fileTile(
                            label: 'Certificado médico / RCP',
                            file: files.discapacidad,
                            icon: Icons.description_rounded,
                            onPick: () => widget.onPickFile(
                              allowPdf: true,
                              onPicked: (f) =>
                                  setState(() => files.discapacidad = f),
                            ),
                          ),
                        ],
                      ),
                    ],
                    const SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: () => Navigator.of(context).pop(),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      child: const Text(
                        'Listo',
                        style: TextStyle(fontWeight: FontWeight.w800),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _docsBlock({
    required String title,
    required IconData icon,
    required String warning,
    required List<Widget> children,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.yellow50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.yellow400),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(icon, size: 16, color: AppColors.yellow600),
              const SizedBox(width: 6),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ...children,
          const SizedBox(height: 6),
          Row(
            children: [
              const Icon(Icons.warning_amber_rounded,
                  size: 13, color: AppColors.yellow600),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  warning,
                  style: const TextStyle(
                    fontSize: 11,
                    color: AppColors.textTertiary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _fileTile({
    required String label,
    required IconData icon,
    required PlatformFile? file,
    required VoidCallback onPick,
  }) {
    final uploaded = file != null;
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: InkWell(
        onTap: onPick,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: uploaded ? AppColors.green500 : AppColors.borderStandard,
            ),
          ),
          child: Row(
            children: [
              Icon(icon,
                  size: 18,
                  color: uploaded ? AppColors.green500 : AppColors.blue500),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      label,
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    Text(
                      uploaded ? file.name : 'PDF o imagen (máx. 5 MB)',
                      style: const TextStyle(
                        fontSize: 11,
                        color: AppColors.textTertiary,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: uploaded ? AppColors.green500 : AppColors.blue500,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  uploaded ? '✓' : 'Subir',
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    color: Colors.white,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Card de detalle del viaje — incluye ruta, fecha/hora, info enriquecida del bus.
class _TripDetailCard extends StatelessWidget {
  final Viaje viaje;
  final String fecha;

  const _TripDetailCard({required this.viaje, required this.fecha});

  @override
  Widget build(BuildContext context) {
    final bus = viaje.autobus;
    final hora = viaje.horaSalida.length >= 5
        ? viaje.horaSalida.substring(0, 5)
        : viaje.horaSalida;

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.borderSubtle),
        boxShadow: AppShadows.sm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.radio_button_checked_rounded,
                              size: 14, color: AppColors.green500),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              viaje.ruta?.origen ?? '?',
                              style: const TextStyle(
                                fontSize: 17,
                                fontWeight: FontWeight.w800,
                                color: AppColors.textPrimary,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                      const Padding(
                        padding: EdgeInsets.only(left: 6, top: 1, bottom: 1),
                        child: SizedBox(
                          width: 2,
                          height: 14,
                          child: ColoredBox(color: AppColors.borderStandard),
                        ),
                      ),
                      Row(
                        children: [
                          const Icon(Icons.location_on_rounded,
                              size: 14, color: AppColors.red500),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              viaje.ruta?.destino ?? '?',
                              style: const TextStyle(
                                fontSize: 17,
                                fontWeight: FontWeight.w800,
                                color: AppColors.textPrimary,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                if (viaje.esIdaYVuelta)
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppColors.yellow50,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.compare_arrows_rounded,
                            size: 11, color: AppColors.yellow600),
                        SizedBox(width: 4),
                        Text(
                          'IDA Y VUELTA',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                            color: AppColors.yellow600,
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          const Divider(height: 1, color: AppColors.borderSubtle),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                _miniKv(
                  icon: Icons.calendar_today_rounded,
                  label: 'FECHA',
                  value: fecha,
                ),
                Container(width: 1, height: 36, color: AppColors.borderStandard),
                _miniKv(
                  icon: Icons.access_time_rounded,
                  label: 'HORA',
                  value: hora,
                  mono: true,
                ),
                Container(width: 1, height: 36, color: AppColors.borderStandard),
                _miniKv(
                  icon: Icons.attach_money_rounded,
                  label: 'PRECIO',
                  value: viaje.precioUsd.toStringAsFixed(0),
                  mono: true,
                  prefix: '\$',
                ),
              ],
            ),
          ),
          if (bus != null)
            Container(
              padding: const EdgeInsets.all(14),
              decoration: const BoxDecoration(
                color: AppColors.gray50,
                borderRadius:
                    BorderRadius.vertical(bottom: Radius.circular(18)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: AppColors.blue50,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    alignment: Alignment.center,
                    child: const Icon(Icons.directions_bus_rounded,
                        color: AppColors.blue500, size: 24),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          bus.nombre,
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w800,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          _busSubtitle(bus),
                          style: const TextStyle(
                            fontSize: 11,
                            color: AppColors.textTertiary,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppColors.borderStandard),
                    ),
                    child: Text(
                      bus.placa,
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        color: AppColors.textPrimary,
                        letterSpacing: 1.2,
                      ),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  String _busSubtitle(Autobus bus) {
    final parts = <String>[];
    if (bus.marca != null && bus.marca!.isNotEmpty) parts.add(bus.marca!);
    if (bus.anio != null) parts.add('${bus.anio}');
    if (bus.color != null && bus.color!.isNotEmpty) parts.add(bus.color!);
    parts.add('${bus.pisos} ${bus.pisos == 1 ? "piso" : "pisos"}');
    parts.add('${bus.capacidadTotal} asientos');
    return parts.join(' · ');
  }

  Widget _miniKv({
    required IconData icon,
    required String label,
    required String value,
    bool mono = false,
    String? prefix,
  }) {
    return Expanded(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Icon(icon, size: 11, color: AppColors.textMuted),
                const SizedBox(width: 4),
                Text(
                  label,
                  style: const TextStyle(
                    fontSize: 10,
                    color: AppColors.textMuted,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.8,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            RichText(
              text: TextSpan(
                style: TextStyle(
                  fontSize: mono ? 16 : 13,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textPrimary,
                  fontFamily: mono ? 'monospace' : null,
                  letterSpacing: mono ? -0.3 : 0,
                ),
                children: [
                  if (prefix != null)
                    TextSpan(
                      text: prefix,
                      style: const TextStyle(
                        fontSize: 13,
                        color: AppColors.textTertiary,
                      ),
                    ),
                  TextSpan(text: value),
                ],
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}
