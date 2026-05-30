import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:legaleasier/core/theme/app_theme.dart';
import 'package:legaleasier/features/auth/presentation/RegisterScreen.dart';
import 'package:legaleasier/features/auth/presentation/LoginScreen.dart';
import 'package:legaleasier/features/auth/presentation/trial_provider.dart';

class LimitGateScreen extends ConsumerWidget {
  const LimitGateScreen({Key? key}) : super(key: key);

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

  @override
  Widget build(BuildContext context, WidgetRef ref) {
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
            Text(
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
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const RegisterScreen()),
                );
              },
              style: ElevatedButton.styleFrom(backgroundColor: AppColors.brand),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 14),
                child: Text('Daftar Gratis', style: AppTextStyles.buttonText),
              ),
            ),
            const SizedBox(height: 12),
            OutlinedButton(
              onPressed: () {
                // Google sign-in flow should be implemented by auth provider.
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const RegisterScreen()),
                );
              },
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text('Lanjut dengan Google', style: AppTextStyles.buttonText.copyWith(color: AppColors.brand)),
              ),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const LoginScreen()),
                );
              },
              child: Text('Sudah punya akun? Masuk', style: AppTextStyles.bodyMedium.copyWith(color: AppColors.text2)),
            ),
          ],
        ),
      ),
    );
  }
}
