import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'package:legaleasier/core/theme/app_theme.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  void _goToOnboarding() {
    if (!mounted) return;
    context.go('/onboarding');
  }

  Widget _buildFeatureItem({
    required IconData icon,
    required String text,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.18),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.16),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, size: 16, color: AppColors.white),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: AppTextStyles.bodySmall.copyWith(
                color: Colors.white.withValues(alpha: 0.92),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLogo() {
    return Container(
      width: 104,
      height: 104,
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(26),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.24),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.14),
            blurRadius: 24,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Positioned(
            left: 23,
            top: 24,
            child: Transform.rotate(
              angle: -0.08,
              child: Container(
                width: 42,
                height: 52,
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                ),
                padding: const EdgeInsets.all(8),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.start,
                  children: [
                    Container(height: 2.5, width: 18, color: AppColors.brand),
                    const SizedBox(height: 4),
                    Container(height: 2.5, width: 14, color: AppColors.brand2),
                    const SizedBox(height: 4),
                    Container(height: 2.5, width: 16, color: AppColors.brand),
                  ],
                ),
              ),
            ),
          ),
          Positioned(
            left: 41,
            top: 18,
            child: Transform.rotate(
              angle: 0.08,
              child: Container(
                width: 42,
                height: 52,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.9),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.35),
                    width: 1,
                  ),
                ),
                padding: const EdgeInsets.all(8),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.start,
                  children: [
                    Container(height: 2.5, width: 18, color: AppColors.brand2),
                    const SizedBox(height: 4),
                    Container(height: 2.5, width: 14, color: AppColors.brand2),
                    const SizedBox(height: 4),
                    Container(height: 2.5, width: 16, color: AppColors.brand2),
                  ],
                ),
              ),
            ),
          ),
          Positioned(
            right: 10,
            bottom: 10,
            child: Container(
              width: 26,
              height: 26,
              decoration: const BoxDecoration(
                color: AppColors.accent,
                shape: BoxShape.circle,
              ),
              alignment: Alignment.center,
              child: const Text(
                'AI',
                style: TextStyle(
                  fontFamily: 'DM Sans',
                  fontSize: 9,
                  fontWeight: FontWeight.w700,
                  color: AppColors.brand,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [AppColors.brand, AppColors.brand2],
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
            child: Column(
              children: [
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(
                    onPressed: _goToOnboarding,
                    child: Text(
                      'Lewati',
                      style: AppTextStyles.navLabel.copyWith(
                        color: Colors.white.withValues(alpha: 0.9),
                      ),
                    ),
                  ),
                ),
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      _buildLogo(),
                      const SizedBox(height: 28),
                      Text(
                        'LegalEasier',
                        textAlign: TextAlign.center,
                        style: AppTextStyles.splashHeadline.copyWith(
                          fontSize: 30,
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Upload, scan, dan tanya. LegalEasier menjelaskan kontrak dalam bahasa yang kamu mengerti.',
                        textAlign: TextAlign.center,
                        style: AppTextStyles.bodyLarge.copyWith(
                          color: Colors.white.withValues(alpha: 0.9),
                          height: 1.55,
                        ),
                      ),
                      const SizedBox(height: 24),
                      _buildFeatureItem(
                        icon: Icons.description_outlined,
                        text: 'Upload dokumen PDF, foto, atau hasil scan.',
                      ),
                      const SizedBox(height: 10),
                      _buildFeatureItem(
                        icon: Icons.psychology_alt_outlined,
                        text: 'Dapatkan ringkasan dan penjelasan yang lebih sederhana.',
                      ),
                      const SizedBox(height: 10),
                      _buildFeatureItem(
                        icon: Icons.history_outlined,
                        text: 'Simpan riwayat analisis untuk dibuka kembali.',
                      ),
                    ],
                  ),
                ),
                Column(
                  children: [
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: _goToOnboarding,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.accent,
                          foregroundColor: AppColors.brand,
                          minimumSize: const Size.fromHeight(50),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          textStyle: AppTextStyles.btnSmall.copyWith(
                            color: AppColors.brand,
                          ),
                        ),
                        child: const Text('Mulai Sekarang'),
                      ),
                    ),
                    const SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton(
                        onPressed: () => context.go('/login'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppColors.white,
                          side: BorderSide(
                            color: Colors.white.withValues(alpha: 0.45),
                            width: 1.2,
                          ),
                          minimumSize: const Size.fromHeight(46),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          textStyle: AppTextStyles.btnSmall.copyWith(
                            color: AppColors.white,
                            fontWeight: FontWeight.w400,
                          ),
                        ),
                        child: const Text('Sudah punya akun? Masuk'),
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'Hanya alat bantu informatif, bukan pengganti konsultasi hukum profesional.',
                      textAlign: TextAlign.center,
                      style: AppTextStyles.meta.copyWith(
                        color: Colors.white.withValues(alpha: 0.75),
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
