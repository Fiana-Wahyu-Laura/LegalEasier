import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:smooth_page_indicator/smooth_page_indicator.dart';

import 'package:legaleasier/core/theme/app_theme.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;

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

  void _nextPage() {
    if (_currentPage < _pages.length - 1) {
      _pageController.nextPage(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
      );
      return;
    }

    context.go('/login');
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
                  onPressed: () => context.go('/login'),
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
                  onPressed: _nextPage,
                  child: Text(
                    _currentPage < _pages.length - 1
                        ? 'Selanjutnya'
                        : 'Mulai Sekarang',
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
