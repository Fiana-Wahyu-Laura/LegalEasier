import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:smooth_page_indicator/smooth_page_indicator.dart';

import 'package:legaleasier/core/theme/app_theme.dart';
import 'package:legaleasier/features/auth/presentation/providers/auth_provider.dart';

class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;
  bool _isTryingAsGuest = false;

  static const List<Map<String, Object>> _pages = [
    {
      'title': 'Pahami dokumen hukum dengan mudah',
      'subtitle': 'Upload kontrak atau perjanjian, lalu biarkan AI membantu menjelaskan setiap klausul.',
      'icon': Icons.description_outlined,
      'accent': AppColors.brand2,
      'chips': ['Upload PDF dan foto', 'Ringkasan yang lebih jelas'],
    },
    {
      'title': 'Ringkas dan interpretasi jelas',
      'subtitle': 'Dapatkan penjelasan bahasa sederhana untuk klausul yang rumit.',
      'icon': Icons.lightbulb_outline,
      'accent': AppColors.accent,
      'chips': ['Risiko klausul penting', 'Bahasa yang mudah dipahami'],
    },
    {
      'title': 'Akses kapan saja',
      'subtitle': 'Simpan riwayat dokumen dan kembali ke analisis kapan pun diperlukan.',
      'icon': Icons.history,
      'accent': AppColors.brand,
      'chips': ['Riwayat tersimpan', 'Tanya AI kapan pun'],
    },
  ];

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  Future<void> _tryAsGuest() async {
    setState(() => _isTryingAsGuest = true);
    try {
      await ref.read(authNotifierProvider.notifier).loginAnonymously();
      if (!mounted) return;
      final user = FirebaseAuth.instance.currentUser;
      if (user != null) {
        context.go('/home');
      }
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Gagal masuk sebagai tamu. Silakan coba lagi.'),
          backgroundColor: AppColors.danger,
        ),
      );
    } finally {
      if (mounted) setState(() => _isTryingAsGuest = false);
    }
  }

  void _nextPage() {
    if (_currentPage < _pages.length - 1) {
      _pageController.nextPage(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
      );
      return;
    }

    // Last page — try as guest for instant access
    _tryAsGuest();
  }

  Widget _buildHeroCard(Map<String, Object> page) {
    final accent = page['accent'] as Color;
    final chips = page['chips'] as List<String>;

    return Container(
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: Colors.black.withValues(alpha: 0.06),
          width: 0.5,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 24,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 92,
            height: 92,
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.12),
              shape: BoxShape.circle,
            ),
            child: Icon(
              page['icon'] as IconData,
              size: 46,
              color: accent,
            ),
          ),
          const SizedBox(height: 24),
          Text(
            page['title'] as String,
            textAlign: TextAlign.center,
            style: AppTextStyles.loginTitle.copyWith(
              color: AppColors.brand,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            page['subtitle'] as String,
            textAlign: TextAlign.center,
            style: AppTextStyles.bodyLarge.copyWith(
              color: AppColors.text2,
              height: 1.55,
            ),
          ),
          const SizedBox(height: 20),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            alignment: WrapAlignment.center,
            children: [
              for (final chip in chips)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: accent.withValues(alpha: 0.18),
                      width: 1,
                    ),
                  ),
                  child: Text(
                    chip,
                    style: AppTextStyles.chipText.copyWith(
                      color: accent,
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBg,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          child: Column(
            children: [
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: _isTryingAsGuest ? null : _tryAsGuest,
                  child: Text(
                    'Lewati',
                    style: AppTextStyles.navLabel.copyWith(
                      color: AppColors.text3,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 10),
              Expanded(
                child: PageView.builder(
                  controller: _pageController,
                  itemCount: _pages.length,
                  onPageChanged: (index) {
                    setState(() {
                      _currentPage = index;
                    });
                  },
                  itemBuilder: (context, index) {
                    final page = _pages[index];
                    return Center(
                      child: _buildHeroCard(page),
                    );
                  },
                ),
              ),
              const SizedBox(height: 20),
              SmoothPageIndicator(
                controller: _pageController,
                count: _pages.length,
                effect: WormEffect(
                  activeDotColor: AppColors.brand,
                  dotColor: Colors.black.withValues(alpha: 0.12),
                  dotHeight: 10,
                  dotWidth: 10,
                  spacing: 8,
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _isTryingAsGuest
                      ? null
                      : (_currentPage < _pages.length - 1 ? _nextPage : _tryAsGuest),
                  child: _isTryingAsGuest
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : Text(
                          _currentPage < _pages.length - 1
                              ? 'Selanjutnya'
                              : 'Coba Gratis — 5 Analisis',
                        ),
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: () => context.go('/login'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.brand2,
                    side: const BorderSide(color: Color(0xFFE0E0E0)),
                  ),
                  child: const Text('Sudah punya akun? Masuk'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
