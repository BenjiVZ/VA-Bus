import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

/// Paleta Aerorutas de Venezuela — extraída de frontend/src/styles/base.css.
class AppColors {
  // Navy (primario)
  static const Color blue50 = Color(0xFFE8EDF5);
  static const Color blue100 = Color(0xFFC8D4E8);
  static const Color blue500 = Color(0xFF1A3A6B);
  static const Color blue600 = Color(0xFF142E55);
  static const Color blue700 = Color(0xFF0E2240);

  // Grays
  static const Color gray25 = Color(0xFFFCFCFC);
  static const Color gray50 = Color(0xFFF7F8FB);
  static const Color gray100 = Color(0xFFEBEDF1);
  static const Color gray200 = Color(0xFFDDE0E6);
  static const Color gray300 = Color(0xFFC1C5CF);
  static const Color gray400 = Color(0xFFA0A6B4);
  static const Color gray500 = Color(0xFF7D8494);
  static const Color gray600 = Color(0xFF5A6175);
  static const Color gray700 = Color(0xFF3D4455);
  static const Color gray800 = Color(0xFF1E2536);
  static const Color gray900 = Color(0xFF0E1525);

  // Amarillo dorado del logo
  static const Color yellow50 = Color(0xFFFFF8E1);
  static const Color yellow100 = Color(0xFFFEEDB7);
  static const Color yellow400 = Color(0xFFF5C842);
  static const Color yellow500 = Color(0xFFE8A820);
  static const Color yellow600 = Color(0xFFD49A10);

  // Rojo acento
  static const Color red50 = Color(0xFFFFEAEA);
  static const Color red500 = Color(0xFFC62828);
  static const Color red600 = Color(0xFFA01E1E);

  // Verde éxito
  static const Color green50 = Color(0xFFE3FCEF);
  static const Color green500 = Color(0xFF00875A);

  // Semánticos
  static const Color bgPrimary = Colors.white;
  static const Color bgSecondary = gray50;
  /// Crema cálido — surface "papel oficial". Para tickets, comprobantes
  /// y elementos que evocan documento impreso.
  static const Color bgPaper = Color(0xFFFFFBF3);
  static const Color textPrimary = gray900;
  static const Color textSecondary = gray700;
  static const Color textTertiary = gray600;
  static const Color textMuted = gray500;
  static const Color borderSubtle = gray100;
  static const Color borderStandard = gray200;
  static const Color borderStrong = gray300;
  static const Color accentPrimary = blue500;

  // Gradientes (oficiales Aerorutas — definidos en system.md)
  static const LinearGradient heroGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [blue700, blue500, Color(0xFF2D5A9E)], // navy del bus al amanecer
  );

  static const LinearGradient yellowGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [yellow400, yellow500], // dorado del faro / sello oficial
  );
}

class AppShadows {
  static const sm = [
    BoxShadow(
      color: Color(0x051F2E52),
      blurRadius: 10,
      offset: Offset(0, 2),
    ),
  ];
  static const md = [
    BoxShadow(
      color: Color(0x081F2E52),
      blurRadius: 20,
      offset: Offset(0, 6),
    ),
  ];
  static const lg = [
    BoxShadow(
      color: Color(0x0C1F2E52),
      blurRadius: 36,
      offset: Offset(0, 12),
    ),
  ];
}

/// Tipografía monospace para datos oficiales — códigos de ticket, horas,
/// referencias bancarias, números de asiento en contextos formales.
/// "Peso de impresión térmica" del terminal.
class AppMono {
  static TextStyle style({
    double fontSize = 14,
    FontWeight fontWeight = FontWeight.w700,
    Color color = AppColors.textPrimary,
    double letterSpacing = 0.5,
  }) =>
      GoogleFonts.robotoMono(
        fontSize: fontSize,
        fontWeight: fontWeight,
        color: color,
        letterSpacing: letterSpacing,
      );

  /// Para horas tipo 14:30 — grande y dominante.
  static TextStyle hour({Color color = AppColors.textPrimary}) =>
      style(fontSize: 22, fontWeight: FontWeight.w800, color: color, letterSpacing: -0.5);

  /// Para códigos tipo "ABC12345"
  static TextStyle code({double fontSize = 18, Color color = AppColors.blue700}) =>
      style(fontSize: fontSize, fontWeight: FontWeight.w800, color: color, letterSpacing: 4);

  /// Para datos en línea: referencia, asiento — peso medio.
  static TextStyle data({double fontSize = 14, Color color = AppColors.textPrimary}) =>
      style(fontSize: fontSize, fontWeight: FontWeight.w600, color: color, letterSpacing: 0.5);
}

class AppTheme {
  static ThemeData light() {
    final base = ThemeData.light(useMaterial3: true);
    final textTheme = GoogleFonts.interTextTheme(base.textTheme).apply(
      bodyColor: AppColors.textPrimary,
      displayColor: AppColors.textPrimary,
    );

    return base.copyWith(
      colorScheme: const ColorScheme.light(
        primary: AppColors.blue500,
        onPrimary: Colors.white,
        secondary: AppColors.yellow500,
        onSecondary: AppColors.gray900,
        error: AppColors.red500,
        onError: Colors.white,
        surface: Colors.white,
        onSurface: AppColors.textPrimary,
        surfaceContainerHighest: AppColors.gray50,
        outline: AppColors.borderStandard,
      ),
      scaffoldBackgroundColor: AppColors.bgSecondary,
      textTheme: textTheme.copyWith(
        displayLarge: GoogleFonts.inter(
          fontSize: 32, fontWeight: FontWeight.w800,
          letterSpacing: -0.5, color: AppColors.textPrimary,
        ),
        displayMedium: GoogleFonts.inter(
          fontSize: 26, fontWeight: FontWeight.w800,
          letterSpacing: -0.4, color: AppColors.textPrimary,
        ),
        headlineLarge: GoogleFonts.inter(
          fontSize: 22, fontWeight: FontWeight.w700,
          letterSpacing: -0.2, color: AppColors.textPrimary,
        ),
        headlineMedium: GoogleFonts.inter(
          fontSize: 18, fontWeight: FontWeight.w700,
          color: AppColors.textPrimary,
        ),
        titleLarge: GoogleFonts.inter(
          fontSize: 16, fontWeight: FontWeight.w700,
          color: AppColors.textPrimary,
        ),
        titleMedium: GoogleFonts.inter(
          fontSize: 14, fontWeight: FontWeight.w600,
          color: AppColors.textPrimary,
        ),
        bodyLarge: GoogleFonts.inter(
          fontSize: 15, fontWeight: FontWeight.w400,
          color: AppColors.textPrimary, height: 1.45,
        ),
        bodyMedium: GoogleFonts.inter(
          fontSize: 14, fontWeight: FontWeight.w400,
          color: AppColors.textSecondary, height: 1.45,
        ),
        labelLarge: GoogleFonts.inter(
          fontSize: 14, fontWeight: FontWeight.w600,
          letterSpacing: 0.1,
        ),
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
        scrolledUnderElevation: 0,
        surfaceTintColor: Colors.transparent,
        centerTitle: false,
        systemOverlayStyle: SystemUiOverlayStyle.dark,
        titleTextStyle: GoogleFonts.inter(
          fontSize: 18,
          fontWeight: FontWeight.w800,
          color: AppColors.textPrimary,
          letterSpacing: -0.2,
        ),
        iconTheme: const IconThemeData(color: AppColors.blue700),
      ),
      cardTheme: CardThemeData(
        color: Colors.white,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          side: const BorderSide(color: Color(0xFFF1F5F9), width: 1),
          borderRadius: BorderRadius.circular(16),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.blue500,
          foregroundColor: Colors.white,
          elevation: 4,
          shadowColor: AppColors.blue500.withValues(alpha: 0.4),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          textStyle: GoogleFonts.inter(
            fontSize: 15,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.1,
          ),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.blue500,
          side: const BorderSide(color: AppColors.borderStrong, width: 1.5),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          textStyle: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.blue500,
          textStyle: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFFF8FAFC),
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        hintStyle: GoogleFonts.inter(color: AppColors.textMuted, fontSize: 14, fontWeight: FontWeight.w400),
        labelStyle: GoogleFonts.inter(color: AppColors.textSecondary, fontSize: 14, fontWeight: FontWeight.w500),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.blue500, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.red500, width: 1.5),
        ),
      ),
      dividerTheme: const DividerThemeData(
        color: AppColors.borderSubtle,
        thickness: 1,
        space: 1,
      ),
      chipTheme: ChipThemeData(
        backgroundColor: AppColors.gray100,
        labelStyle: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w600),
        side: BorderSide.none,
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: AppColors.gray900,
        contentTextStyle: GoogleFonts.inter(color: Colors.white, fontSize: 14),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        actionTextColor: AppColors.yellow400,
      ),
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: Colors.white,
        selectedItemColor: AppColors.blue500,
        unselectedItemColor: AppColors.textMuted,
        selectedLabelStyle: GoogleFonts.inter(
          fontSize: 11, fontWeight: FontWeight.w700,
        ),
        unselectedLabelStyle: GoogleFonts.inter(
          fontSize: 11, fontWeight: FontWeight.w500,
        ),
        type: BottomNavigationBarType.fixed,
        elevation: 0,
      ),
    );
  }
}
