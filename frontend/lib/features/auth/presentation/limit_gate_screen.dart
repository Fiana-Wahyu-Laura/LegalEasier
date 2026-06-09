import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:legaleasier/core/theme/app_theme.dart';
import 'providers/auth_provider.dart';

class LimitGateScreen extends ConsumerStatefulWidget {
  const LimitGateScreen({super.key});

  @override
  ConsumerState<LimitGateScreen> createState() => _LimitGateScreenState();
}

class _LimitGateScreenState extends ConsumerState<LimitGateScreen> {
  bool _isLoading = false;

  Widget _benefitRow(String text) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.check_circle, color: Colors.green, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              text,
              style: AppTextStyles.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _signInWithGoogle() async {
    setState(() => _isLoading = true);
    try {
      await ref.read(authNotifierProvider.notifier).loginWithGoogle();
      if (!mounted) return;
      context.go('/home');
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Gagal masuk dengan Google. Silakan coba lagi.'),
          backgroundColor: AppColors.danger,
        ),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Batas Gratis'),
        elevation: 0,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SizedBox(height: 8),
            Center(
              child: Container(
                width: 72,
                height: 72,
                decoration: BoxDecoration(
                  color: Colors.yellow[700],
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Center(
                  child: Icon(Icons.lock_outline, color: Colors.white, size: 36),
                ),
              ),
            ),
            const SizedBox(height: 20),
            const Text(
              'Kuota Gratis Habis',
              style: AppTextStyles.screenTitle,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'Daftar untuk melanjutkan analisis dokumen tanpa batas dan akses fitur premium.',
              style: AppTextStyles.bodyLarge.copyWith(color: AppColors.text2),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            _benefitRow('Analisis dokumen tanpa batas'),
            _benefitRow('Chat AI untuk semua dokumen'),
            _benefitRow('Riwayat dokumen tersimpan'),
            _benefitRow('Akses fitur premium'),
            const Spacer(),
            ElevatedButton(
              onPressed: _isLoading ? null : () => context.go('/register'),
              style: ElevatedButton.styleFrom(backgroundColor: AppColors.brand),
              child: const Padding(
                padding: EdgeInsets.symmetric(vertical: 14),
                child: Text('Daftar Gratis', style: AppTextStyles.buttonText),
              ),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: _isLoading ? null : _signInWithGoogle,
              icon: _isLoading
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.g_mobiledata, size: 20),
              label: Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(
                  'Lanjut dengan Google',
                  style: AppTextStyles.buttonText.copyWith(color: AppColors.brand),
                ),
              ),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: _isLoading ? null : () => context.go('/login'),
              child: Text(
                'Sudah punya akun? Masuk',
                style: AppTextStyles.bodyMedium.copyWith(color: AppColors.text2),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
