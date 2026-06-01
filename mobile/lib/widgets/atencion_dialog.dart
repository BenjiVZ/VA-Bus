import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../config/theme.dart';

/// Resumen del viaje que se muestra en el header del modal.
class AtencionViajeInfo {
  final String origen;
  final String destino;
  final String fecha; // formato 'YYYY-MM-DD' (igual que en el backend)
  final int cantidad;

  const AtencionViajeInfo({
    required this.origen,
    required this.destino,
    required this.fecha,
    required this.cantidad,
  });
}

/// Modal de "¡Atención!" — equivale al AtencionModal.jsx del frontend web.
///
/// Devuelve `true` si el usuario aceptó los términos y tocó "Continuar".
/// Devuelve `null` o `false` si cerró el modal sin aceptar.
///
/// Uso:
///   final ok = await showAtencionDialog(context, info: AtencionViajeInfo(...));
///   if (ok == true) { /* avanzar */ }
Future<bool?> showAtencionDialog(
  BuildContext context, {
  required AtencionViajeInfo info,
}) {
  return showDialog<bool>(
    context: context,
    barrierColor: Colors.black.withValues(alpha: 0.55),
    builder: (_) => _AtencionDialog(info: info),
  );
}

class _AtencionDialog extends StatefulWidget {
  final AtencionViajeInfo info;
  const _AtencionDialog({required this.info});

  @override
  State<_AtencionDialog> createState() => _AtencionDialogState();
}

class _AtencionDialogState extends State<_AtencionDialog> {
  bool _accepted = false;

  String _fmtFecha(String iso) {
    try {
      return DateFormat('d MMM yyyy', 'es').format(DateTime.parse(iso));
    } catch (_) {
      return iso;
    }
  }

  @override
  Widget build(BuildContext context) {
    final info = widget.info;
    final media = MediaQuery.of(context);
    final maxH = media.size.height * 0.9;

    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
      child: ConstrainedBox(
        constraints: BoxConstraints(maxHeight: maxH, maxWidth: 520),
        child: Stack(
          clipBehavior: Clip.none,
          children: [
            // ── Card principal ──
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(24),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.25),
                    blurRadius: 30,
                    offset: const Offset(0, 12),
                  ),
                ],
              ),
              clipBehavior: Clip.hardEdge,
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Header + ícono "!" montado sobre su borde inferior
                    Stack(
                      clipBehavior: Clip.none,
                      alignment: Alignment.bottomCenter,
                      children: [
                        _Header(info: info, fechaFmt: _fmtFecha(info.fecha)),
                        Positioned(
                          bottom: -28, // mitad del ícono sobresale del header
                          child: _AlertIcon(),
                        ),
                      ],
                    ),
                    // Espacio reservado para la mitad inferior del ícono,
                    // así el título nunca se solapa.
                    const SizedBox(height: 32),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
                      child: Column(
                        children: [
                          const Text(
                            '¡Atención!',
                            style: TextStyle(
                              fontSize: 22,
                              fontWeight: FontWeight.w800,
                              color: AppColors.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 8),
                          const Text.rich(
                            TextSpan(
                              text: 'Todos los pasajeros deben presentarse ',
                              style: TextStyle(
                                fontSize: 13,
                                color: AppColors.textSecondary,
                                height: 1.45,
                              ),
                              children: [
                                TextSpan(
                                  text: 'al menos 1 hora antes',
                                  style: TextStyle(
                                    fontWeight: FontWeight.w800,
                                    color: AppColors.textPrimary,
                                  ),
                                ),
                                TextSpan(text: ' del viaje por taquilla con:'),
                              ],
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 18),
                          const _Requirement(
                            icon: Icons.verified_user_rounded,
                            iconBg: AppColors.blue50,
                            iconColor: AppColors.blue500,
                            title: 'Venezolano:',
                            body:
                                '- Cédula de identidad original o pasaporte.',
                          ),
                          const SizedBox(height: 10),
                          const _Requirement(
                            icon: Icons.child_care_rounded,
                            iconBg: AppColors.yellow50,
                            iconColor: AppColors.yellow600,
                            title: 'Menores de edad:',
                            body:
                                '- Documentación y permisos de viaje del CPNNA.',
                          ),
                          const SizedBox(height: 10),
                          const _Requirement(
                            icon: Icons.public_rounded,
                            iconBg: AppColors.green50,
                            iconColor: AppColors.green500,
                            title: 'Extranjero:',
                            body:
                                '- Pasaporte sellado con entrada al país y vigencia de 90 días.',
                          ),
                          const SizedBox(height: 18),
                          // ── Caja "¡Importante!" ──
                          Container(
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: AppColors.gray50,
                              borderRadius: BorderRadius.circular(12),
                              border:
                                  Border.all(color: AppColors.borderSubtle),
                            ),
                            child: const Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Icon(Icons.warning_amber_rounded,
                                        size: 16,
                                        color: AppColors.yellow600),
                                    SizedBox(width: 6),
                                    Text(
                                      '¡Importante!',
                                      style: TextStyle(
                                        fontSize: 13,
                                        fontWeight: FontWeight.w800,
                                        color: AppColors.textPrimary,
                                      ),
                                    ),
                                  ],
                                ),
                                SizedBox(height: 8),
                                _Bullet(
                                  'La tasa de salida no está incluida en el costo del boleto. El costo de este pago dependerá del terminal de salida.',
                                ),
                                _Bullet(
                                  'Los boletos de tercera edad pueden tener un recargo adicional.',
                                ),
                                _Bullet(
                                  'Una vez confirmada la compra, los cambios están sujetos a disponibilidad.',
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 14),
                          // ── Checkbox de aceptación ──
                          InkWell(
                            onTap: () =>
                                setState(() => _accepted = !_accepted),
                            borderRadius: BorderRadius.circular(8),
                            child: Padding(
                              padding: const EdgeInsets.symmetric(vertical: 4),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  SizedBox(
                                    width: 22,
                                    height: 22,
                                    child: Checkbox(
                                      value: _accepted,
                                      onChanged: (v) => setState(
                                          () => _accepted = v ?? false),
                                      materialTapTargetSize:
                                          MaterialTapTargetSize.shrinkWrap,
                                      visualDensity: VisualDensity.compact,
                                    ),
                                  ),
                                  const SizedBox(width: 10),
                                  const Expanded(
                                    child: Text.rich(
                                      TextSpan(
                                        text: 'He leído y acepto los términos y condiciones de transporte de ',
                                        style: TextStyle(
                                          fontSize: 12,
                                          color: AppColors.textSecondary,
                                          height: 1.4,
                                        ),
                                        children: [
                                          TextSpan(
                                            text: 'Aerorutas de Venezuela',
                                            style: TextStyle(
                                              fontWeight: FontWeight.w800,
                                              color: AppColors.textPrimary,
                                            ),
                                          ),
                                          TextSpan(text: '.'),
                                        ],
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(height: 14),
                          // ── CTA ──
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton.icon(
                              icon: const Icon(Icons.credit_card_rounded),
                              label: const Text(
                                'Continuar con la Reserva',
                                style: TextStyle(
                                    fontSize: 15, fontWeight: FontWeight.w800),
                              ),
                              onPressed: _accepted
                                  ? () => Navigator.of(context).pop(true)
                                  : null,
                              style: ElevatedButton.styleFrom(
                                padding:
                                    const EdgeInsets.symmetric(vertical: 16),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(14),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            // ── Botón cerrar (flotante arriba derecha) ──
            Positioned(
              right: 12,
              top: 12,
              child: Material(
                color: Colors.white.withValues(alpha: 0.18),
                shape: const CircleBorder(),
                child: InkWell(
                  customBorder: const CircleBorder(),
                  onTap: () => Navigator.of(context).pop(false),
                  child: const Padding(
                    padding: EdgeInsets.all(6),
                    child: Icon(Icons.close_rounded,
                        size: 20, color: Colors.white),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Ícono ! amarillo con halo, usado como pivote entre header y body.
class _AlertIcon extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 56,
      height: 56,
      decoration: BoxDecoration(
        color: AppColors.yellow400,
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white, width: 4),
        boxShadow: [
          BoxShadow(
            color: AppColors.yellow400.withValues(alpha: 0.5),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      alignment: Alignment.center,
      child: const Text(
        '!',
        style: TextStyle(
          color: Colors.white,
          fontSize: 28,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  final AtencionViajeInfo info;
  final String fechaFmt;
  const _Header({required this.info, required this.fechaFmt});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
      decoration: const BoxDecoration(
        gradient: AppColors.heroGradient,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Ruta origen → destino
          Row(
            children: [
              const Icon(Icons.radio_button_checked_rounded,
                  size: 14, color: Colors.white),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  info.origen,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Container(
                width: 14,
                height: 1,
                color: Colors.white.withValues(alpha: 0.5),
              ),
              const SizedBox(width: 6),
              const Icon(Icons.location_on_rounded,
                  size: 14, color: Colors.white),
              const SizedBox(width: 6),
              Flexible(
                child: Text(
                  info.destino,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          // Meta: fecha + cantidad de boletos
          Row(
            children: [
              const Icon(Icons.calendar_today_rounded,
                  size: 12, color: Colors.white70),
              const SizedBox(width: 4),
              Text(
                fechaFmt,
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.85),
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(width: 12),
              const Icon(Icons.confirmation_number_rounded,
                  size: 12, color: Colors.white70),
              const SizedBox(width: 4),
              Text(
                '${info.cantidad} ${info.cantidad == 1 ? "Boleto" : "Boletos"}',
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.85),
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _Requirement extends StatelessWidget {
  final IconData icon;
  final Color iconBg;
  final Color iconColor;
  final String title;
  final String body;
  const _Requirement({
    required this.icon,
    required this.iconBg,
    required this.iconColor,
    required this.title,
    required this.body,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: iconBg,
            borderRadius: BorderRadius.circular(10),
          ),
          alignment: Alignment.center,
          child: Icon(icon, size: 18, color: iconColor),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                body,
                style: const TextStyle(
                  fontSize: 12,
                  color: AppColors.textTertiary,
                  height: 1.4,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _Bullet extends StatelessWidget {
  final String text;
  const _Bullet(this.text);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 6, right: 8),
            child: Icon(Icons.circle, size: 5, color: AppColors.textTertiary),
          ),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(
                fontSize: 11.5,
                color: AppColors.textSecondary,
                height: 1.45,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
