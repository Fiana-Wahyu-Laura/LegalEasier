import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:legaleasier/core/theme/app_theme.dart';
import 'package:legaleasier/features/auth/presentation/providers/auth_provider.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authNotifierProvider);
    final authUser = authState.value;
    final isGuest = authUser?.isGuest ?? true;

    final displayName = (authUser?.displayName != null &&
            authUser!.displayName!.trim().isNotEmpty)
        ? authUser.displayName!.trim()
        : (authUser?.email ?? 'Pengguna Tamu');
    final email = authUser?.email ?? '-';
    final initial = displayName.isNotEmpty
        ? displayName[0].toUpperCase()
        : 'U';

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppBar(
        backgroundColor: AppColors.brand,
        title: Text(
          'Profil',
          style: AppTextStyles.homeTitle.copyWith(fontSize: 20),
        ),
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            const SizedBox(height: 16),

            // Avatar
            Container(
              width: 80,
              height: 80,
              decoration: const BoxDecoration(
                color: AppColors.accent,
                shape: BoxShape.circle,
              ),
              child: Center(
                child: Text(
                  initial,
                  style: const TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.w700,
                    color: AppColors.brand,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Name
            Text(
              displayName,
              style: AppTextStyles.screenTitle.copyWith(fontSize: 20),
            ),
            const SizedBox(height: 4),
            Text(
              email,
              style: AppTextStyles.bodyMedium.copyWith(color: AppColors.text2),
            ),

            if (isGuest) ...[
              const SizedBox(height: 8),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.accent.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  'Akun Tamu',
                  style: AppTextStyles.badgeText.copyWith(
                    color: AppColors.accent,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],

            const SizedBox(height: 32),

            // Info cards
            _buildInfoCard(
              icon: Icons.email_outlined,
              title: 'Email',
              value: email,
            ),
            const SizedBox(height: 10),
            _buildInfoCard(
              icon: Icons.person_outline,
              title: 'Jenis Akun',
              value: isGuest ? 'Tamu (5 analisis gratis)' : 'Terdaftar',
            ),

            const SizedBox(height: 32),

            // Upgrade banner for guests
            if (isGuest)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.accent.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: AppColors.accent.withValues(alpha: 0.3),
                  ),
                ),
                child: Column(
                  children: [
                    const Icon(Icons.star_outline,
                        size: 32, color: AppColors.accent),
                    const SizedBox(height: 8),
                    Text(
                      'Simpan riwayat & akses penuh',
                      style: AppTextStyles.cardTitle.copyWith(
                        color: AppColors.brand,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Daftar akun gratis untuk menyimpan semua dokumen, '
                      'chat AI tanpa batas, dan sync lintas perangkat.',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.text2,
                        height: 1.5,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 14),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: () => context.go('/register'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.accent,
                          foregroundColor: AppColors.brand,
                          minimumSize: const Size(double.infinity, 48),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          textStyle: AppTextStyles.buttonText,
                        ),
                        child: const Text('Daftar Gratis'),
                      ),
                    ),
                  ],
                ),
              ),

            const SizedBox(height: 24),

            // Logout / Exit button
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () async {
                  await ref.read(authNotifierProvider.notifier).logout();
                  if (!context.mounted) return;
                  context.go('/onboarding');
                },
                icon: Icon(
                  isGuest ? Icons.exit_to_app : Icons.logout,
                  size: 18,
                ),
                label: Text(isGuest ? 'Keluar' : 'Logout'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.danger,
                  minimumSize: const Size(double.infinity, 48),
                  side: BorderSide(
                    color: AppColors.danger.withValues(alpha: 0.3),
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  textStyle: AppTextStyles.buttonText,
                ),
              ),
            ),

            const SizedBox(height: 16),

            // App version
            Text(
              'LegalEasier v0.1.0',
              style: AppTextStyles.meta.copyWith(color: AppColors.text3),
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoCard({
    required IconData icon,
    required String title,
    required String value,
  }) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: AppColors.brand.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, size: 20, color: AppColors.brand),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.text3,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  value,
                  style: AppTextStyles.bodyMedium.copyWith(
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
