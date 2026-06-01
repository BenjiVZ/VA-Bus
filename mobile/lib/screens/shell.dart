import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../config/theme.dart';
import '../providers/auth_provider.dart';
import '../widgets/pending_order_banner.dart';

/// Altura visual total del nav (overhang + pill + margin inferior + safe area buffer).
/// Las páginas scrollables deben agregar este valor como bottom padding para
/// que el último item no quede tapado por el nav flotante.
const double kFloatingNavHeight = 140;

/// Shell con bottom navigation flotante en forma de isla con muesca animada.
///
/// La pill tiene un CUTOUT semicircular donde está el botón activo — el círculo
/// flota arriba "anidado" en esa muesca, como en muchas apps modernas con FAB
/// notched bottom bar. La muesca se desliza al cambiar de pestaña.
class MainShell extends StatelessWidget {
  final Widget child;
  const MainShell({super.key, required this.child});

  static const _tabs = [
    _TabSpec(path: '/', icon: Icons.home_outlined, activeIcon: Icons.home_rounded, label: 'Inicio'),
    _TabSpec(path: '/viajes', icon: Icons.search_outlined, activeIcon: Icons.search_rounded, label: 'Buscar'),
    _TabSpec(path: '/mis-reservas', icon: Icons.confirmation_number_outlined, activeIcon: Icons.confirmation_number_rounded, label: 'Mis viajes', requiresAuth: true),
    _TabSpec(path: '/perfil', icon: Icons.person_outline_rounded, activeIcon: Icons.person_rounded, label: 'Perfil', requiresAuth: true),
  ];

  int _currentIndex(String location) {
    if (location.startsWith('/viajes') || location.startsWith('/asientos')) return 1;
    if (location.startsWith('/mis-reservas') || location.startsWith('/ticket') || location.startsWith('/reserva')) return 2;
    if (location.startsWith('/perfil')) return 3;
    return 0;
  }

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    final currentIndex = _currentIndex(location);
    final auth = context.watch<AuthProvider>();

    return Scaffold(
      extendBody: true,
      body: Column(
        children: [
          const PendingOrderBanner(),
          Expanded(child: child),
        ],
      ),
      bottomNavigationBar: _FloatingNav(
        tabs: _tabs,
        activeIndex: currentIndex,
        onTap: (i) {
          final tab = _tabs[i];
          if (tab.requiresAuth && !auth.isAuthenticated) {
            context.push('/login');
            return;
          }
          if (location != tab.path) context.go(tab.path);
        },
      ),
    );
  }
}

class _TabSpec {
  final String path;
  final IconData icon;
  final IconData activeIcon;
  final String label;
  final bool requiresAuth;
  const _TabSpec({
    required this.path,
    required this.icon,
    required this.activeIcon,
    required this.label,
    this.requiresAuth = false,
  });
}

/// Nav flotante con muesca animada que sigue el círculo activo.
class _FloatingNav extends StatefulWidget {
  final List<_TabSpec> tabs;
  final int activeIndex;
  final ValueChanged<int> onTap;

  const _FloatingNav({
    required this.tabs,
    required this.activeIndex,
    required this.onTap,
  });

  @override
  State<_FloatingNav> createState() => _FloatingNavState();
}

class _FloatingNavState extends State<_FloatingNav>
    with SingleTickerProviderStateMixin {
  static const double _barHeight = 64;
  static const double _circleSize = 60;
  static const double _notchRadius = 38; // ligeramente mayor que el radio del círculo
  static const double _haloSize = 92;
  static const double _hMargin = 24;
  static const double _bottomMargin = 22;
  static const double _topOverhang = 42;

  late final AnimationController _controller;
  late Animation<double> _slide;
  late double _currentIndex;

  @override
  void initState() {
    super.initState();
    _currentIndex = widget.activeIndex.toDouble();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 380),
    );
    _slide = AlwaysStoppedAnimation(_currentIndex);
  }

  @override
  void didUpdateWidget(covariant _FloatingNav old) {
    super.didUpdateWidget(old);
    if (old.activeIndex != widget.activeIndex) {
      final from = _slide.value;
      _slide = Tween<double>(begin: from, end: widget.activeIndex.toDouble())
          .animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic));
      _controller
        ..reset()
        ..forward();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final tabs = widget.tabs;
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(_hMargin, 0, _hMargin, _bottomMargin),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final barWidth = constraints.maxWidth;
            final slotWidth = barWidth / tabs.length;

            return AnimatedBuilder(
              animation: _slide,
              builder: (context, _) {
                final indexFrac = _slide.value;
                final circleCenterX = slotWidth * indexFrac + slotWidth / 2;
                final circleLeft = circleCenterX - _circleSize / 2;
                final haloLeft = circleCenterX - _haloSize / 2;

                return SizedBox(
                  height: _barHeight + _topOverhang,
                  child: Stack(
                    clipBehavior: Clip.none,
                    children: [
                      // ── Halo / glow detrás del círculo ──
                      Positioned(
                        left: haloLeft,
                        top: _topOverhang - (_haloSize - _circleSize) / 2 - 14,
                        child: IgnorePointer(
                          ignoring: true,
                          child: Container(
                            width: _haloSize,
                            height: _haloSize,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              gradient: RadialGradient(
                                colors: [
                                  AppColors.blue500.withValues(alpha: 0.30),
                                  AppColors.blue500.withValues(alpha: 0),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),

                      // ── Pill blanca con muesca animada ──
                      Positioned(
                        left: 0, right: 0, bottom: 0,
                        child: Container(
                          height: _barHeight,
                          decoration: ShapeDecoration(
                            color: Colors.white,
                            shape: _NotchedPillShape(
                              notchCenterX: circleCenterX,
                              notchRadius: _notchRadius,
                              pillRadius: _barHeight / 2,
                            ),
                            shadows: [
                              BoxShadow(
                                color: AppColors.blue700.withValues(alpha: 0.18),
                                blurRadius: 40,
                                offset: const Offset(0, 18),
                              ),
                              BoxShadow(
                                color: AppColors.blue700.withValues(alpha: 0.10),
                                blurRadius: 16,
                                offset: const Offset(0, 8),
                              ),
                              BoxShadow(
                                color: AppColors.blue700.withValues(alpha: 0.05),
                                blurRadius: 4,
                                offset: const Offset(0, 2),
                              ),
                            ],
                          ),
                          child: Row(
                            children: List.generate(tabs.length, (i) {
                              final tab = tabs[i];
                              // El "activo" para ocultar el icono usa el frac:
                              // ocultamos el más cercano al fraccional
                              final dist = (indexFrac - i).abs();
                              final hideOpacity = (1 - dist).clamp(0.0, 1.0);
                              return Expanded(
                                child: Material(
                                  color: Colors.transparent,
                                  child: InkWell(
                                    onTap: () => widget.onTap(i),
                                    borderRadius: BorderRadius.circular(_barHeight / 2),
                                    child: Center(
                                      child: Opacity(
                                        opacity: 1.0 - hideOpacity,
                                        child: Icon(
                                          tab.icon,
                                          color: AppColors.gray500,
                                          size: 26,
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                              );
                            }),
                          ),
                        ),
                      ),

                      // ── Círculo flotante (navy del theme) ──
                      Positioned(
                        left: circleLeft,
                        top: _topOverhang - _circleSize / 2 + 4,
                        child: IgnorePointer(
                          ignoring: true,
                          child: Container(
                            width: _circleSize,
                            height: _circleSize,
                            decoration: BoxDecoration(
                              gradient: const LinearGradient(
                                begin: Alignment.topCenter,
                                end: Alignment.bottomCenter,
                                colors: [
                                  Color(0xFF2D5A9E), // mismo tope del heroGradient
                                  AppColors.blue500,
                                  AppColors.blue700,
                                ],
                                stops: [0.0, 0.55, 1.0],
                              ),
                              shape: BoxShape.circle,
                              boxShadow: [
                                BoxShadow(
                                  color: AppColors.blue500.withValues(alpha: 0.5),
                                  blurRadius: 16,
                                  offset: const Offset(0, 8),
                                ),
                                BoxShadow(
                                  color: AppColors.blue700.withValues(alpha: 0.3),
                                  blurRadius: 6,
                                  offset: const Offset(0, 2),
                                ),
                              ],
                            ),
                            child: AnimatedSwitcher(
                              duration: const Duration(milliseconds: 240),
                              transitionBuilder: (child, anim) => ScaleTransition(
                                scale: Tween<double>(begin: 0.6, end: 1.0).animate(anim),
                                child: FadeTransition(opacity: anim, child: child),
                              ),
                              child: Icon(
                                tabs[widget.activeIndex].activeIcon,
                                key: ValueKey(widget.activeIndex),
                                color: Colors.white,
                                size: 26,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}

/// ShapeBorder que dibuja una pill con una muesca semicircular en el borde
/// superior, posicionada en [notchCenterX]. La muesca usa el mismo radius
/// del círculo flotante (con un pequeño padding) para que se "anide" bien.
class _NotchedPillShape extends ShapeBorder {
  final double notchCenterX;
  final double notchRadius;
  final double pillRadius;

  const _NotchedPillShape({
    required this.notchCenterX,
    required this.notchRadius,
    required this.pillRadius,
  });

  @override
  EdgeInsetsGeometry get dimensions => EdgeInsets.zero;

  @override
  Path getInnerPath(Rect rect, {TextDirection? textDirection}) =>
      getOuterPath(rect, textDirection: textDirection);

  @override
  Path getOuterPath(Rect rect, {TextDirection? textDirection}) {
    final path = Path();
    final r = pillRadius;
    final nR = notchRadius;
    final cx = rect.left + notchCenterX;

    // top-left corner
    path.moveTo(rect.left + r, rect.top);
    // top edge: from corner to start of notch
    path.lineTo(cx - nR, rect.top);
    // semicircular notch (arco hacia adentro)
    path.arcToPoint(
      Offset(cx + nR, rect.top),
      radius: Radius.circular(nR),
      clockwise: false,
    );
    // top edge: from notch end to top-right corner
    path.lineTo(rect.right - r, rect.top);
    // top-right corner
    path.arcToPoint(
      Offset(rect.right, rect.top + r),
      radius: Radius.circular(r),
    );
    // right edge
    path.lineTo(rect.right, rect.bottom - r);
    // bottom-right corner
    path.arcToPoint(
      Offset(rect.right - r, rect.bottom),
      radius: Radius.circular(r),
    );
    // bottom edge
    path.lineTo(rect.left + r, rect.bottom);
    // bottom-left corner
    path.arcToPoint(
      Offset(rect.left, rect.bottom - r),
      radius: Radius.circular(r),
    );
    // left edge
    path.lineTo(rect.left, rect.top + r);
    // top-left corner
    path.arcToPoint(
      Offset(rect.left + r, rect.top),
      radius: Radius.circular(r),
    );

    path.close();
    return path;
  }

  @override
  void paint(Canvas canvas, Rect rect, {TextDirection? textDirection}) {}

  @override
  ShapeBorder scale(double t) => this;
}
