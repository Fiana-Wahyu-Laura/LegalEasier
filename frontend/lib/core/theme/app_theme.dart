import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// LegalEasy Design System Color Palette
class AppColors {
  // Brand
  static const Color brand = Color(0xFF1A3A4A);        // Navy gelap
  static const Color brand2 = Color(0xFF2E6B5E);       // Teal
  static const Color accent = Color(0xFFC8A96E);       // Gold
  static const Color accent2 = Color(0xFFE8D5B0);      // Gold muda
  static const Color accentLight = accent2;

  // Neutral
  static const Color soft = Color(0xFFF4F0E8);         // Krem
  static const Color white = Color(0xFFFFFFFF);
  static const Color pageBg = Color(0xFFE8E4DC);       // Warm off-white
  static const Color pageBackground = pageBg;

  // Text
  static const Color text1 = Color(0xFF1A1A1A);        // Teks utama
  static const Color text2 = Color(0xFF5A5A5A);        // Teks sekunder
  static const Color text3 = Color(0xFF9A9A9A);        // Teks tersier

  // Risk levels
  static const Color danger = Color(0xFFC0392B);       // Tinggi
  static const Color warn = Color(0xFFD68910);         // Sedang
  static const Color warning = warn;
  static const Color ok = Color(0xFF1E8449);           // Aman / Rendah
  static const Color success = ok;

  // Quick action backgrounds
  static const Color uploadBg = Color(0xFFD5EDE8);
  static const Color scanBg = Color(0xFFD8E9F8);
  static const Color chatBg = Color(0xFFEDE8F8);
  static const Color historyBg = Color(0xFFF8EEE0);

  // Icon colors
  static const Color uploadIcon = Color(0xFF2E6B5E);
  static const Color scanIcon = Color(0xFF185FA5);
  static const Color chatIcon = Color(0xFF534AB7);
  static const Color historyIcon = Color(0xFFBA7517);

  // Trial gate
  static const Color gateBg = Color(0xFFFEF9E7);
  static const Color gateBorder = Color(0xFFF9CA5A);
  static const Color gateIcon = Color(0xFFBA7517);
}

/// LegalEasy Design System - Text Styles
class AppTextStyles {
  // Headings (Fraunces)
  static const splashHeadline = TextStyle(
    fontFamily: 'Fraunces',
    fontSize: 28,
    fontWeight: FontWeight.w700,
    color: AppColors.white,
    height: 1.2,
  );

  static const screenTitle = TextStyle(
    fontFamily: 'Fraunces',
    fontSize: 22,
    fontWeight: FontWeight.w700,
    color: AppColors.text1,
  );

  static const homeTitle = TextStyle(
    fontFamily: 'Fraunces',
    fontSize: 20,
    fontWeight: FontWeight.w700,
    color: AppColors.white,
  );

  static const sectionTitle = TextStyle(
    fontFamily: 'Fraunces',
    fontSize: 18,
    fontWeight: FontWeight.w700,
    color: AppColors.brand,
  );

  static const loginTitle = TextStyle(
    fontFamily: 'Fraunces',
    fontSize: 22,
    fontWeight: FontWeight.w700,
    color: AppColors.text1,
  );

  static const cardTitle = TextStyle(
    fontFamily: 'DM Sans',
    fontSize: 16,
    fontWeight: FontWeight.w500,
    color: AppColors.text1,
  );

  static const limitTitle = TextStyle(
    fontFamily: 'Fraunces',
    fontSize: 20,
    fontWeight: FontWeight.w700,
    color: AppColors.text1,
  );

  // Body text (DM Sans)
  static const bodyLarge = TextStyle(
    fontFamily: 'DM Sans',
    fontSize: 13,
    fontWeight: FontWeight.w400,
    color: AppColors.text1,
    height: 1.5,
  );

  static const bodyMedium = TextStyle(
    fontFamily: 'DM Sans',
    fontSize: 13,
    fontWeight: FontWeight.w400,
    color: AppColors.text2,
  );

  static const bodySmall = TextStyle(
    fontFamily: 'DM Sans',
    fontSize: 12,
    fontWeight: FontWeight.w400,
    color: AppColors.text2,
  );

  static const label = TextStyle(
    fontFamily: 'DM Sans',
    fontSize: 14,
    fontWeight: FontWeight.w500,
    color: AppColors.text1,
  );

  static const meta = TextStyle(
    fontFamily: 'DM Sans',
    fontSize: 11,
    fontWeight: FontWeight.w400,
    color: AppColors.text3,
  );

  static const buttonText = TextStyle(
    fontFamily: 'DM Sans',
    fontSize: 14,
    fontWeight: FontWeight.w500,
    color: AppColors.white,
  );

  static const btnSmall = TextStyle(
    fontFamily: 'DM Sans',
    fontSize: 13,
    fontWeight: FontWeight.w500,
    color: AppColors.white,
  );

  static const screenLabel = TextStyle(
    fontFamily: 'DM Sans',
    fontSize: 10,
    fontWeight: FontWeight.w500,
    color: AppColors.text3,
    letterSpacing: 1.0,
  );

  static const badgeText = TextStyle(
    fontFamily: 'DM Sans',
    fontSize: 10,
    fontWeight: FontWeight.w500,
  );

  static const statNum = TextStyle(
    fontFamily: 'DM Sans',
    fontSize: 18,
    fontWeight: FontWeight.w500,
    color: AppColors.text1,
  );

  static const navLabel = TextStyle(
    fontFamily: 'DM Sans',
    fontSize: 10,
  );

  static const chipText = TextStyle(
    fontFamily: 'DM Sans',
    fontSize: 11,
    fontWeight: FontWeight.w500,
  );
}

class AppTheme {
  static ThemeData light() {
    return ThemeData(
      useMaterial3: true,
      fontFamily: 'DM Sans',
      textTheme: GoogleFonts.dmSansTextTheme().apply(
        bodyColor: AppColors.text1,
        displayColor: AppColors.text1,
      ),
      primaryTextTheme: GoogleFonts.frauncesTextTheme().apply(
        bodyColor: AppColors.white,
        displayColor: AppColors.white,
      ),
      colorScheme: ColorScheme.fromSeed(
        seedColor: AppColors.brand,
        primary: AppColors.brand,
        secondary: AppColors.brand2,
        surface: AppColors.white,
      ),
      scaffoldBackgroundColor: AppColors.pageBg,
      
      // App Bar
      appBarTheme: const AppBarTheme(
        elevation: 0,
        backgroundColor: AppColors.brand,
        foregroundColor: AppColors.white,
        surfaceTintColor: Colors.transparent,
        iconTheme: IconThemeData(color: AppColors.white),
        titleTextStyle: AppTextStyles.screenTitle,
        centerTitle: false,
      ),

      // Input Fields
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(
            color: Color(0xFFE8E8E8),
            width: 1.5,
          ),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(
            color: Color(0xFFE8E8E8),
            width: 1.5,
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(
            color: AppColors.brand2,
            width: 1.5,
          ),
        ),
        filled: true,
        fillColor: AppColors.white,
        contentPadding: const EdgeInsets.symmetric(
          vertical: 12,
          horizontal: 14,
        ),
        labelStyle: AppTextStyles.label,
        hintStyle: AppTextStyles.bodyMedium.copyWith(
          color: AppColors.text3,
        ),
      ),

      // Elevated Button
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.brand,
          foregroundColor: AppColors.white,
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          minimumSize: const Size.fromHeight(50),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: AppTextStyles.buttonText,
          elevation: 0,
        ),
      ),

      // Outlined Button
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.brand2,
          side: const BorderSide(
            color: Color(0xFFE0E0E0),
            width: 1.2,
          ),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          minimumSize: const Size.fromHeight(50),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: AppTextStyles.buttonText,
        ),
      ),

      // Text Button
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.brand2,
          textStyle: AppTextStyles.label,
        ),
      ),

      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: AppColors.brand2,
        foregroundColor: AppColors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(50),
        ),
      ),

      // Card
      cardTheme: CardThemeData(
        color: AppColors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(
            color: Color.fromRGBO(0, 0, 0, 0.07),
            width: 0.5,
          ),
        ),
      ),

      // Dialog
      dialogTheme: DialogThemeData(
        backgroundColor: AppColors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
        ),
      ),

      // Bottom Sheet
      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: AppColors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.only(
            topLeft: Radius.circular(20),
            topRight: Radius.circular(20),
          ),
        ),
        elevation: 10,
      ),
    );
  }
}
