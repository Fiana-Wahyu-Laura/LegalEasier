import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:legaleasier/core/theme/app_theme.dart';
import 'package:legaleasier/features/auth/presentation/providers/auth_provider.dart';
import 'package:legaleasier/features/document/domain/document.dart';
import 'package:legaleasier/features/document/presentation/widgets/quick_action_card.dart';
import 'package:legaleasier/features/document/presentation/widgets/trial_banner.dart';
import 'package:legaleasier/features/document/presentation/widgets/recent_documents_section.dart';
import 'package:legaleasier/features/document/presentation/widgets/stat_box.dart';
import 'package:legaleasier/features/document/presentation/widgets/upload_scan_bottom_sheet.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  bool _isSigningOut = false;

  Widget _buildAvatar(String userInitial) {
    return Container(
      width: 36,
      height: 36,
      decoration: const BoxDecoration(
        color: AppColors.accent,
        shape: BoxShape.circle,
      ),
      child: Center(
        child: Text(
          userInitial,
          style: const TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: 14,
            color: AppColors.brand,
          ),
        ),
      ),
    );
  }

  Future<void> _signOut() async {
    setState(() {
      _isSigningOut = true;
    });
    try {
      await ref.read(authNotifierProvider.notifier).logout();
      if (!mounted) return;
      context.go('/login');
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text(
            'Gagal keluar. Silakan coba lagi.',
            style: TextStyle(color: Colors.white),
          ),
          backgroundColor: AppColors.danger,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSigningOut = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authUser = ref.watch(authNotifierProvider).value;
    final displayName = authUser?.displayName?.trim();
    final userName = (displayName != null && displayName.isNotEmpty)
        ? displayName
        : (authUser?.email ?? 'Pengguna');
    final userInitial = userName.isNotEmpty ? userName[0].toUpperCase() : 'U';

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppBar(
        backgroundColor: AppColors.brand,
        title: Text(
          'Beranda',
          style: AppTextStyles.homeTitle.copyWith(
            fontSize: 20,
          ),
        ),
        elevation: 0,
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Center(
              child: GestureDetector(
                onTap: _isSigningOut ? null : _signOut,
                child: _isSigningOut
                    ? const SizedBox(
                        width: 36,
                        height: 36,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation<Color>(
                            AppColors.white,
                          ),
                        ),
                      )
                    : _buildAvatar(userInitial),
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 20),
              
              // Greeting section
              Text(
                'Halo!',
                style: AppTextStyles.homeTitle.copyWith(fontSize: 24),
              ),
              const SizedBox(height: 4),
              Text(
                'Selamat datang, $userName',
                style: AppTextStyles.bodyLarge,
              ),
              const SizedBox(height: 16),

              // Trial banner
              const TrialBanner(),
              const SizedBox(height: 24),

              // Quick stats (3 stat boxes)
              const Row(
                children: [
                  Expanded(
                    child: StatBox(
                      number: '0',
                      label: 'Dokumen',
                    ),
                  ),
                  SizedBox(width: 8),
                  Expanded(
                    child: StatBox(
                      number: '0',
                      label: 'Berisiko',
                    ),
                  ),
                  SizedBox(width: 8),
                  Expanded(
                    child: StatBox(
                      number: '5',
                      label: 'Sisa Gratis',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),

              // Quick actions grid
              Text(
                'Mulai dari sini',
                style: AppTextStyles.sectionTitle.copyWith(
                  fontSize: 18,
                ),
              ),
              const SizedBox(height: 12),
              GridView.count(
                crossAxisCount: 2,
                mainAxisSpacing: 10,
                crossAxisSpacing: 10,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                children: [
                  QuickActionCard(
                    icon: Icons.cloud_upload_outlined,
                    iconColor: AppColors.uploadIcon,
                    bgColor: AppColors.uploadBg,
                    title: 'Upload\nDokumen',
                    onTap: () async {
                      final messenger = ScaffoldMessenger.of(context);
                      final result = await showModalBottomSheet<Document>(
                        context: context,
                        isScrollControlled: true,
                        builder: (_) => const UploadScanBottomSheet(
                          initialMethod: UploadMethod.file,
                        ),
                      );

                      if (!mounted || result == null) {
                        return;
                      }

                      messenger.showSnackBar(
                        const SnackBar(
                          content: Text('Dokumen berhasil diupload.'),
                        ),
                      );
                    },
                  ),
                  QuickActionCard(
                    icon: Icons.camera_alt_outlined,
                    iconColor: AppColors.scanIcon,
                    bgColor: AppColors.scanBg,
                    title: 'Scan\nDokumen',
                    onTap: () async {
                      final messenger = ScaffoldMessenger.of(context);
                      final result = await showModalBottomSheet<Document>(
                        context: context,
                        isScrollControlled: true,
                        builder: (_) => const UploadScanBottomSheet(),
                      );

                      if (!mounted || result == null) {
                        return;
                      }

                      messenger.showSnackBar(
                        const SnackBar(
                          content: Text('Dokumen hasil scan berhasil diupload.'),
                        ),
                      );
                    },
                  ),
                  QuickActionCard(
                    icon: Icons.chat_bubble_outline,
                    iconColor: AppColors.chatIcon,
                    bgColor: AppColors.chatBg,
                    title: 'Tanya AI\nLegalEasy',
                    onTap: () {
                      // TODO: Navigate to chat
                    },
                  ),
                  QuickActionCard(
                    icon: Icons.history,
                    iconColor: AppColors.historyIcon,
                    bgColor: AppColors.historyBg,
                    title: 'Riwayat\nDokumen',
                    onTap: () {
                      // TODO: Navigate to history
                    },
                  ),
                ],
              ),
              const SizedBox(height: 24),

              // Recent documents
              const RecentDocumentsSection(),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}
