import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../../config/theme.dart';
import '../../models/viaje.dart';
import '../../providers/auth_provider.dart';
import '../../services/viajes_service.dart';
import '../../utils/format.dart';
import '../../widgets/app_logo.dart';
import '../shell.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  DateTime? _fecha;
  List<Map<String, dynamic>> _oficinas = [];
  String? _origenCod;
  String? _destinoCod;
  List<Viaje> _viajesHoy = [];
  List<Viaje> _proximas = [];
  bool _loadingRutas = true;
  String? _errorMsg;

  @override
  void initState() {
    super.initState();
    _cargarDatos();
  }

  @override
  void dispose() {
    super.dispose();
  }

  Future<void> _cargarDatos() async {
    final svc = context.read<ViajesService>();
    setState(() => _errorMsg = null);
    try {
      final hoy = DateFormat('yyyy-MM-dd').format(DateTime.now());
      final results = await Future.wait([
        svc.getOficinas(),
        svc.buscarViajes(fecha: hoy),
      ]);
      if (!mounted) return;
      final viajesHoy = results[1] as List<Viaje>;
      setState(() {
        _oficinas = results[0] as List<Map<String, dynamic>>;
        _viajesHoy = viajesHoy;
        _proximas = viajesHoy.take(4).toList();
        _loadingRutas = false;
      });
    } catch (e) {
      // Imprimir a la consola del browser para depuración
      // ignore: avoid_print
      print('[home] Error cargando datos: $e');
      if (!mounted) return;
      setState(() {
        _loadingRutas = false;
        _errorMsg = e.toString();
      });
    }
  }

  Future<void> _pickFecha() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _fecha ?? DateTime.now(),
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 15)),
      builder: (c, child) => Theme(
        data: Theme.of(c).copyWith(
          colorScheme: const ColorScheme.light(
            primary: AppColors.blue500,
            onPrimary: Colors.white,
            surface: Colors.white,
            onSurface: AppColors.textPrimary,
          ),
        ),
        child: child!,
      ),
    );
    if (picked != null) setState(() => _fecha = picked);
  }

  void _setFechaRapida(DateTime f) => setState(() => _fecha = f);

  void _swapOriginDestino() {
    setState(() {
      final tmp = _origenCod;
      _origenCod = _destinoCod;
      _destinoCod = tmp;
    });
    HapticFeedback.selectionClick();
  }

  void _buscar() {
    if (_fecha == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('Elige una fecha.')));
      return;
    }
    final params = {'fecha': DateFormat('yyyy-MM-dd').format(_fecha!)};
    if (_origenCod != null && _destinoCod != null) {
      params['origen'] = _origenCod!;
      params['destino'] = _destinoCod!;
    }
    context.push('/viajes?${Uri(queryParameters: params).query}');
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final hoy = DateTime.now();
    final manana = hoy.add(const Duration(days: 1));

    return Scaffold(
      extendBodyBehindAppBar: true,
      backgroundColor: AppColors.bgSecondary,
      body: RefreshIndicator(
        onRefresh: _cargarDatos,
        color: AppColors.blue500,
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            // Top Section (Hero + Search Card + Departure Board) combinados para evitar clipping en Web
            SliverToBoxAdapter(
              child: Column(
                children: [
                  _HeroSection(usuario: auth),
                  Transform.translate(
                    offset: const Offset(0, -30),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: _SearchCard(
                        oficinas: _oficinas,
                        origenCod: _origenCod,
                        destinoCod: _destinoCod,
                        onOrigen: (v) => setState(() => _origenCod = v),
                        onDestino: (v) => setState(() => _destinoCod = v),
                        fecha: _fecha,
                        onPickFecha: _pickFecha,
                        onSwap: _swapOriginDestino,
                        onFechaRapida: _setFechaRapida,
                        onBuscar: _buscar,
                        hoy: hoy,
                        manana: manana,
                      ),
                    ),
                  ),
                  if (_proximas.isNotEmpty)
                    _DepartureBoard(viajes: _proximas),
                ],
              ),
            ),
            // Sección destinos
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Viajes de hoy',
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    if (_viajesHoy.length > 4)
                      TextButton(
                        onPressed: () => context.push('/viajes'),
                        child: const Text('Ver todos'),
                      ),
                  ],
                ),
              ),
            ),
            if (_loadingRutas)
              SliverToBoxAdapter(
                child: SizedBox(
                  height: 180,
                  child: Center(
                    child: CircularProgressIndicator(color: AppColors.blue500),
                  ),
                ),
              )
            else if (_viajesHoy.isEmpty)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: _errorMsg != null
                          ? AppColors.red50
                          : AppColors.gray50,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: _errorMsg != null
                            ? AppColors.red500
                            : AppColors.borderStandard,
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              _errorMsg != null
                                  ? Icons.warning_amber_rounded
                                  : Icons.info_outline_rounded,
                              color: _errorMsg != null
                                  ? AppColors.red500
                                  : AppColors.textTertiary,
                              size: 18,
                            ),
                            const SizedBox(width: 8),
                            Text(
                              _errorMsg != null
                                  ? 'No se pudo conectar al servidor'
                                  : 'No hay viajes para hoy',
                              style: TextStyle(
                                fontWeight: FontWeight.w700,
                                color: _errorMsg != null
                                    ? AppColors.red500
                                    : AppColors.textPrimary,
                              ),
                            ),
                          ],
                        ),
                        if (_errorMsg != null) ...[
                          const SizedBox(height: 8),
                          Text(
                            _errorMsg!,
                            style: const TextStyle(
                              fontSize: 11,
                              color: AppColors.textTertiary,
                              fontFamily: 'monospace',
                            ),
                          ),
                          const SizedBox(height: 8),
                          OutlinedButton.icon(
                            icon: const Icon(Icons.refresh_rounded, size: 16),
                            label: const Text('Reintentar'),
                            onPressed: _cargarDatos,
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              )
            else
              SliverPadding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                sliver: SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (ctx, i) => _DestinoCard(
                      ruta: _viajesHoy[i].ruta ??
                          Ruta(id: 0, origen: '', destino: '', duracionEstimada: ''),
                      onTap: () => context.push('/viajes/${_viajesHoy[i].id}/asientos'),
                    )
                        .animate()
                        .fadeIn(duration: 280.ms, delay: (i * 50).ms)
                        .slideY(begin: 0.15, end: 0, curve: Curves.easeOutCubic),
                    childCount: _viajesHoy.length > 8 ? 8 : _viajesHoy.length,
                  ),
                ),
              ),
            // ¿Por qué elegirnos?
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 24, 20, 12),
                child: Text(
                  '¿Por qué viajar con nosotros?',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
              ),
            ),
            SliverToBoxAdapter(
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Row(
                  children: const [
                    _FeatureCard(
                      icon: Icons.shield_outlined,
                      color: AppColors.blue500,
                      bgColor: AppColors.blue50,
                      title: 'Reserva segura',
                      subtitle: 'Tu asiento se aparta apenas seleccionas',
                    ),
                    _FeatureCard(
                      icon: Icons.qr_code_2_rounded,
                      color: AppColors.yellow600,
                      bgColor: AppColors.yellow50,
                      title: 'Ticket digital',
                      subtitle: 'QR único para abordar sin filas',
                    ),
                    _FeatureCard(
                      icon: Icons.support_agent_outlined,
                      color: AppColors.green500,
                      bgColor: AppColors.green50,
                      title: 'Soporte 24/7',
                      subtitle: 'WhatsApp directo con el equipo',
                    ),
                    _FeatureCard(
                      icon: Icons.workspace_premium_outlined,
                      color: AppColors.red500,
                      bgColor: AppColors.red50,
                      title: 'Programa VIP',
                      subtitle: 'Beneficios y descuentos al viajar',
                    ),
                  ],
                ),
              ),
            ),
            // Padding inferior para no quedar tapado por el nav flotante
            const SliverToBoxAdapter(child: SizedBox(height: kFloatingNavHeight)),
          ],
        ),
      ),
    );
  }
}

/* ── Hero ── */
class _HeroSection extends StatelessWidget {
  final AuthProvider usuario;
  const _HeroSection({required this.usuario});

  @override
  Widget build(BuildContext context) {
    final saludo = _saludoHora();
    final mediaQuery = MediaQuery.of(context);
    return Container(
      width: double.infinity,
      padding: EdgeInsets.fromLTRB(20, mediaQuery.padding.top + 16, 20, 44),
      decoration: const BoxDecoration(
        gradient: AppColors.heroGradient,
      ),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          // Textura sutil de puntos
          Positioned.fill(
            child: ClipRect(
              child: CustomPaint(painter: _DotsPainter()),
            ),
          ),
          // Accent amarillo arriba derecha (pequeño, sutil)
          Positioned(
            right: -30,
            top: -30,
            child: Container(
              width: 100,
              height: 100,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    AppColors.yellow400.withValues(alpha: 0.18),
                    AppColors.yellow400.withValues(alpha: 0),
                  ],
                ),
              ),
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  // Logo blanco (filtrado) sobre el navy
                  AppLogo(height: 36, color: Colors.white),
                  const Spacer(),
                  if (usuario.isAuthenticated)
                    ClipRRect(
                      borderRadius: BorderRadius.circular(20),
                      child: BackdropFilter(
                        filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: Colors.white.withValues(alpha: 0.3)),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.person_rounded, color: Colors.white, size: 14),
                              const SizedBox(width: 4),
                              Text(
                                usuario.usuario?.firstName.isEmpty == false
                                    ? usuario.usuario!.firstName
                                    : 'Hola',
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    )
                  else
                    GestureDetector(
                      onTap: () => context.push('/login'),
                      child: const Text(
                        'Iniciar sesión',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                          fontSize: 13,
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 20),
              Text(
                saludo,
                style: const TextStyle(
                  color: Colors.white70,
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                usuario.isAuthenticated
                    ? '¿A dónde viajas hoy?'
                    : '¿A dónde te llevamos?',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 26,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.5,
                  height: 1.15,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _saludoHora() {
    final h = DateTime.now().hour;
    if (h < 12) return 'Buenos días ☀️';
    if (h < 19) return 'Buenas tardes 🌤️';
    return 'Buenas noches 🌙';
  }
}

/* ── Search card ── */
class _SearchCard extends StatelessWidget {
  final List<Map<String, dynamic>> oficinas;
  final String? origenCod;
  final String? destinoCod;
  final ValueChanged<String?> onOrigen;
  final ValueChanged<String?> onDestino;
  final DateTime? fecha;
  final VoidCallback onPickFecha;
  final VoidCallback onSwap;
  final void Function(DateTime) onFechaRapida;
  final VoidCallback onBuscar;
  final DateTime hoy;
  final DateTime manana;

  const _SearchCard({
    required this.oficinas,
    required this.origenCod,
    required this.destinoCod,
    required this.onOrigen,
    required this.onDestino,
    required this.fecha,
    required this.onPickFecha,
    required this.onSwap,
    required this.onFechaRapida,
    required this.onBuscar,
    required this.hoy,
    required this.manana,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: AppShadows.lg,
        border: Border.all(color: const Color(0xFFF1F5F9)),
      ),
      child: Column(
        children: [
          _OficinaDropdown(
            oficinas: oficinas,
            value: origenCod,
            onChanged: onOrigen,
            icon: Icons.radio_button_checked_rounded,
            iconColor: AppColors.green500,
            hint: 'Origen',
          ),
          Align(
            alignment: Alignment.centerRight,
            child: IconButton(
              onPressed: onSwap,
              tooltip: 'Intercambiar',
              icon: const Icon(Icons.swap_vert_rounded, color: AppColors.blue500),
            ),
          ),
          _OficinaDropdown(
            oficinas: oficinas,
            value: destinoCod,
            onChanged: onDestino,
            icon: Icons.location_on_rounded,
            iconColor: AppColors.red500,
            hint: 'Destino',
          ),
          const SizedBox(height: 16),
          // Chips fecha rápida
          Row(
            children: [
              _DateChip(
                label: 'Hoy',
                active: _isSameDay(fecha, hoy),
                onTap: () => onFechaRapida(hoy),
              ),
              const SizedBox(width: 8),
              _DateChip(
                label: 'Mañana',
                active: _isSameDay(fecha, manana),
                onTap: () => onFechaRapida(manana),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 250),
                  curve: Curves.easeInOut,
                  decoration: BoxDecoration(
                    color: (fecha != null && !_isSameDay(fecha, hoy) && !_isSameDay(fecha, manana))
                        ? AppColors.blue50
                        : const Color(0xFFF8FAFC),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: (fecha != null && !_isSameDay(fecha, hoy) && !_isSameDay(fecha, manana))
                          ? AppColors.blue500
                          : const Color(0xFFE2E8F0),
                    ),
                    boxShadow: (fecha != null && !_isSameDay(fecha, hoy) && !_isSameDay(fecha, manana))
                        ? [
                            BoxShadow(
                              color: AppColors.blue500.withValues(alpha: 0.15),
                              blurRadius: 8,
                              offset: const Offset(0, 3),
                            )
                          ]
                        : null,
                  ),
                  child: Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: onPickFecha,
                      borderRadius: BorderRadius.circular(12),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 11),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.calendar_today_rounded,
                              size: 14,
                              color: (fecha != null && !_isSameDay(fecha, hoy) && !_isSameDay(fecha, manana))
                                  ? AppColors.blue700
                                  : AppColors.blue500,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              fecha == null || _isSameDay(fecha, hoy) || _isSameDay(fecha, manana)
                                  ? 'Otra fecha'
                                  : DateFormat('d MMM', 'es').format(fecha!),
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w700,
                                color: (fecha != null && !_isSameDay(fecha, hoy) && !_isSameDay(fecha, manana))
                                    ? AppColors.blue700
                                    : AppColors.blue500,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              icon: const Icon(Icons.search_rounded, size: 22),
              label: const Text('Buscar viajes', style: TextStyle(fontSize: 16)),
              onPressed: onBuscar,
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 18),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              ),
            ),
          ),
        ],
      ),
    );
  }

  bool _isSameDay(DateTime? a, DateTime b) =>
      a != null && a.year == b.year && a.month == b.month && a.day == b.day;
}

/* ── Desplegable de oficina (origen/destino) ── */
class _OficinaDropdown extends StatelessWidget {
  final List<Map<String, dynamic>> oficinas;
  final String? value;
  final ValueChanged<String?> onChanged;
  final IconData icon;
  final Color iconColor;
  final String hint;

  const _OficinaDropdown({
    required this.oficinas,
    required this.value,
    required this.onChanged,
    required this.icon,
    required this.iconColor,
    required this.hint,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: value,
          isExpanded: true,
          hint: Row(children: [
            Icon(icon, color: iconColor, size: 18),
            const SizedBox(width: 10),
            Text(hint, style: const TextStyle(
                color: AppColors.textMuted, fontWeight: FontWeight.w500)),
          ]),
          icon: const Icon(Icons.keyboard_arrow_down_rounded),
          items: oficinas.map((o) {
            return DropdownMenuItem<String>(
              value: (o['codofi'] ?? '') as String,
              child: Row(children: [
                Icon(icon, color: iconColor, size: 18),
                const SizedBox(width: 10),
                Expanded(child: Text(
                  (o['desofi'] ?? '') as String,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
                )),
              ]),
            );
          }).toList(),
          onChanged: onChanged,
        ),
      ),
    );
  }
}

class _LocationField extends StatefulWidget {
  final TextEditingController controller;
  final IconData icon;
  final Color iconColor;
  final String hint;
  
  const _LocationField({
    required this.controller,
    required this.icon,
    required this.iconColor,
    required this.hint,
  });

  @override
  State<_LocationField> createState() => _LocationFieldState();
}

class _LocationFieldState extends State<_LocationField> {
  final FocusNode _focusNode = FocusNode();
  bool _hasFocus = false;

  @override
  void initState() {
    super.initState();
    _focusNode.addListener(() {
      setState(() {
        _hasFocus = _focusNode.hasFocus;
      });
    });
  }

  @override
  void dispose() {
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      decoration: BoxDecoration(
        color: _hasFocus ? Colors.white : const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: _hasFocus ? AppColors.blue500 : const Color(0xFFE2E8F0),
          width: _hasFocus ? 1.8 : 1.0,
        ),
        boxShadow: _hasFocus 
            ? [
                BoxShadow(
                  color: AppColors.blue500.withValues(alpha: 0.08),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                )
              ]
            : null,
      ),
      child: TextField(
        controller: widget.controller,
        focusNode: _focusNode,
        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
        decoration: InputDecoration(
          filled: false,
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          border: InputBorder.none,
          focusedBorder: InputBorder.none,
          enabledBorder: InputBorder.none,
          hintText: widget.hint,
          hintStyle: const TextStyle(
            color: AppColors.textMuted,
            fontWeight: FontWeight.w500,
          ),
          prefixIcon: Container(
            margin: const EdgeInsets.only(right: 12, left: 4),
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: widget.iconColor.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(widget.icon, color: widget.iconColor, size: 18),
          ),
          prefixIconConstraints: const BoxConstraints(minWidth: 40, minHeight: 40),
        ),
      ),
    );
  }
}

class _DateChip extends StatelessWidget {
  final String label;
  final bool active;
  final VoidCallback onTap;
  const _DateChip({required this.label, required this.active, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 250),
      curve: Curves.easeInOut,
      decoration: BoxDecoration(
        color: active ? AppColors.blue500 : const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: active ? AppColors.blue500 : const Color(0xFFE2E8F0),
          width: 1.0,
        ),
        boxShadow: active
            ? [
                BoxShadow(
                  color: AppColors.blue500.withValues(alpha: 0.15),
                  blurRadius: 8,
                  offset: const Offset(0, 3),
                )
              ]
            : null,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 11),
            child: Text(
              label,
              style: TextStyle(
                color: active ? Colors.white : AppColors.textPrimary,
                fontWeight: FontWeight.w700,
                fontSize: 13,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/* ── Tablero de Salidas — estilo monitor de terminal ── */
class _DepartureBoard extends StatelessWidget {
  final List<Viaje> viajes;
  const _DepartureBoard({required this.viajes});

  String _hora(String hms) => horaAmPm(hms);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.gray900,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFF1E293B), width: 3), // physical frame
          boxShadow: [
            ...AppShadows.md,
            BoxShadow(
              color: AppColors.yellow400.withValues(alpha: 0.03),
              blurRadius: 30,
              spreadRadius: -5,
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(13),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header del tablero (estilo display LED)
              Container(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 10),
                decoration: const BoxDecoration(
                  color: Color(0xFF070B14),
                  border: Border(
                    bottom: BorderSide(color: Color(0x1F2E5244)),
                  ),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 8, height: 8,
                      decoration: BoxDecoration(
                        color: AppColors.yellow400,
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: AppColors.yellow400.withValues(alpha: 0.8),
                            blurRadius: 8,
                            spreadRadius: 1,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 10),
                    Text(
                      'PRÓXIMAS SALIDAS',
                      style: AppMono.style(
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        color: AppColors.yellow400,
                        letterSpacing: 2.5,
                      ),
                    ),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.05),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        '${viajes.length} programadas'.toUpperCase(),
                        style: AppMono.style(
                          fontSize: 9,
                          fontWeight: FontWeight.w600,
                          color: Colors.white.withValues(alpha: 0.5),
                          letterSpacing: 1.2,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              // Filas
              ...viajes.asMap().entries.map((e) {
                final i = e.key;
                final v = e.value;
                return _BoardRow(
                  viaje: v,
                  hora: _hora(v.horaSalida),
                  isLast: i == viajes.length - 1,
                );
              }),
            ],
          ),
        ),
      ),
    );
  }
}

class _BoardRow extends StatelessWidget {
  final Viaje viaje;
  final String hora;
  final bool isLast;
  const _BoardRow({required this.viaje, required this.hora, required this.isLast});

  @override
  Widget build(BuildContext context) {
    final agotado = viaje.asientosDisponibles <= 0;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: agotado ? null : () => context.push('/viajes/${viaje.id}/asientos'),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          decoration: BoxDecoration(
            border: isLast
                ? null
                : const Border(bottom: BorderSide(color: Color(0x0FFFFFFF))),
          ),
          child: Row(
            children: [
              // Hora monospace (peso del display LED)
              SizedBox(
                width: 60,
                child: Text(
                  hora,
                  style: AppMono.style(
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                    color: agotado
                        ? Colors.white.withValues(alpha: 0.25)
                        : AppColors.yellow400,
                    letterSpacing: -0.5,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              // Ruta
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '${viaje.ruta?.origen ?? '?'} → ${viaje.ruta?.destino ?? '?'}',
                      style: TextStyle(
                        color: agotado
                            ? Colors.white.withValues(alpha: 0.35)
                            : Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.2,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 3),
                    Row(
                      children: [
                        if (!agotado) ...[
                          Container(
                            width: 6, height: 6,
                            decoration: const BoxDecoration(
                              color: AppColors.green500,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 6),
                        ],
                        Text(
                          agotado
                              ? 'AGOTADO'
                              : '${viaje.asientosDisponibles} ${viaje.asientosDisponibles == 1 ? "ASIENTO" : "ASIENTOS"}',
                          style: AppMono.style(
                            fontSize: 9,
                            fontWeight: FontWeight.w700,
                            color: agotado
                                ? AppColors.red500
                                : Colors.white.withValues(alpha: 0.45),
                            letterSpacing: 1.2,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              // Precio
              Text(
                '\$${viaje.precioUsd.toStringAsFixed(0)}',
                style: AppMono.style(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: agotado
                      ? Colors.white.withValues(alpha: 0.25)
                      : Colors.white,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(width: 8),
              Icon(
                Icons.chevron_right_rounded,
                color: agotado
                    ? Colors.white.withValues(alpha: 0.15)
                    : AppColors.yellow400.withValues(alpha: 0.7),
                size: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/* ── Destino card ── */
class _DestinoCard extends StatelessWidget {
  final Ruta ruta;
  final VoidCallback onTap;
  const _DestinoCard({required this.ruta, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: AppShadows.sm,
          border: Border.all(color: const Color(0xFFF1F5F9)),
        ),
        child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(16),
          child: InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: onTap,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [Color(0xFFF1F5F9), Color(0xFFE2E8F0)],
                      ),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    alignment: Alignment.center,
                    child: const Icon(Icons.place_rounded, color: AppColors.blue500),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          ruta.origen,
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppColors.textTertiary,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Row(
                          children: [
                            const Icon(Icons.arrow_forward_rounded,
                                size: 14, color: AppColors.blue500),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                ruta.destino,
                                style: const TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w800,
                                  color: AppColors.textPrimary,
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                        if (ruta.duracionEstimada.isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.only(top: 6),
                            child: Row(
                              children: [
                                const Icon(Icons.schedule_rounded,
                                    size: 13, color: AppColors.textMuted),
                                const SizedBox(width: 4),
                                Text(
                                  ruta.duracionEstimada,
                                  style: const TextStyle(
                                    fontSize: 11,
                                    color: AppColors.textMuted,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),
                  ),
                  const Icon(Icons.chevron_right_rounded, color: AppColors.textMuted),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/* ── Feature horizontal card ── */
class _FeatureCard extends StatelessWidget {
  final IconData icon;
  final Color color;
  final Color bgColor;
  final String title;
  final String subtitle;
  const _FeatureCard({
    required this.icon,
    required this.color,
    required this.bgColor,
    required this.title,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 190,
      margin: const EdgeInsets.only(right: 14, bottom: 8, top: 4),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFFF1F5F9)),
        boxShadow: AppShadows.sm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 44, height: 44,
            decoration: BoxDecoration(
              color: bgColor,
              borderRadius: BorderRadius.circular(12),
            ),
            alignment: Alignment.center,
            child: Icon(icon, color: color, size: 24),
          ),
          const SizedBox(height: 14),
          Text(
            title,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w800,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            subtitle,
            style: const TextStyle(
              fontSize: 12,
              color: AppColors.textTertiary,
              height: 1.45,
            ),
          ),
        ],
      ),
    );
  }
}

/* ── Textura de puntos para el hero ── */
class _DotsPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = Colors.white.withValues(alpha: 0.06);
    const spacing = 18.0;
    const radius = 1.2;
    for (double y = 8; y < size.height; y += spacing) {
      for (double x = 8; x < size.width; x += spacing) {
        canvas.drawCircle(Offset(x, y), radius, paint);
      }
    }
  }

  @override
  bool shouldRepaint(_) => false;
}
