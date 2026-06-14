import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:legaleasier/core/theme/app_theme.dart';
import 'package:legaleasier/features/auth/presentation/providers/auth_provider.dart';
import 'package:legaleasier/features/document/domain/document.dart';
import 'package:legaleasier/features/document/presentation/widgets/quick_action_card.dart';
import 'package:legaleasier/features/document/presentation/providers/document_provider.dart';
import 'package:legaleasier/features/document/presentation/providers/guest_quota_provider.dart';
import 'package:legaleasier/features/document/presentation/widgets/recent_documents_section.dart';
import 'package:legaleasier/features/document/presentation/widgets/stat_box.dart';
import 'package:legaleasier/features/document/presentation/widgets/upload_scan_bottom_sheet.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  bool _hasShownLimitGate = false;

  String _buildUserName(authUser) {
    final displayName = authUser?.displayName?.trim();
    return (displayName != null && displayName.isNotEmpty)
        ? displayName
        : (authUser?.email ?? 'Pengguna');
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authNotifierProvider);
    final authUser = authState.value;
    final isAuthLoading = authState.isLoading;
    final quotaState = ref.watch(guestQuotaProvider);
    final recentDocumentsAsync = ref.watch(recentDocumentsProvider);
    final remainingQuota = quotaState.value ?? 5;

    final isGuestUser = isAuthLoading ? false : (authUser?.isGuest ?? false);
    final userName = isAuthLoading ? '' : _buildUserName(authUser);
    final userInitial = userName.isNotEmpty ? userName[0].toUpperCase() : 'U';
    final canUseFreeAnalysis = !isGuestUser || remainingQuota > 0;
    final freeAnalysisValue = isGuestUser ? remainingQuota.toString() : '∞';
    final freeAnalysisLabel = isGuestUser ? 'Sisa Gratis' : 'Akses AI';

    // Auto-redirect to limit gate when guest quota hits 0
    if (isGuestUser &&
        remainingQuota <= 0 &&
        !_hasShownLimitGate &&
        !isAuthLoading) {
      _hasShownLimitGate = true;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) context.go('/limit-gate');
      });
    }

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Home Header (matches mockup) ──
            _buildHomeHeader(
              userName: userName,
              userInitial: userInitial,
              isGuestUser: isGuestUser,
              remainingQuota: remainingQuota,
              recentDocumentsAsync: recentDocumentsAsync,
              freeAnalysisValue: freeAnalysisValue,
              freeAnalysisLabel: freeAnalysisLabel,
            ),

            // ── Body ──
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 18),

                  // Quick actions grid
                  Text(
                    'Mulai dari sini',
                    style: AppTextStyles.sectionTitle.copyWith(fontSize: 18),
                  ),
                  const SizedBox(height: 6),
                  _buildQuickActionsGrid(
                    isGuestUser: isGuestUser,
                    canUseFreeAnalysis: canUseFreeAnalysis,
                    remainingQuota: remainingQuota,
                    recentDocumentsAsync: recentDocumentsAsync,
                  ),

                  // Recent documents — registered users only (compact, max 3)
                  if (!isGuestUser) ...[
                    const SizedBox(height: 24),
                    const RecentDocumentsSection(maxItems: 3),
                    const SizedBox(height: 24),
                  ] else
                    const SizedBox(height: 24),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ─── Header ────────────────────────────────────────────────────────

  Widget _buildHomeHeader({
    required String userName,
    required String userInitial,
    required bool isGuestUser,
    required int remainingQuota,
    required AsyncValue<List<Document>> recentDocumentsAsync,
    required String freeAnalysisValue,
    required String freeAnalysisLabel,
  }) {
    return Container(
      width: double.infinity,
      decoration: const BoxDecoration(
        color: AppColors.brand,
        borderRadius: BorderRadius.only(
          bottomLeft: Radius.circular(20),
          bottomRight: Radius.circular(20),
        ),
      ),
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Top row: greeting + avatar
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Halo',
                          style: AppTextStyles.bodySmall.copyWith(
                            color: Colors.white.withValues(alpha: 0.7),
                            fontSize: 12,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          userName,
                          style: AppTextStyles.homeTitle.copyWith(
                            fontSize: 20,
                            color: AppColors.white,
                          ),
                        ),
                      ],
                    ),
                  ),
                  GestureDetector(
                    onTap: () => context.go('/profile'),
                    child: Container(
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
                            fontSize: 13,
                            color: AppColors.brand,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),

              // Sub text
              const SizedBox(height: 8),
              Text(
                'Dokumen hukummu lebih mudah dipahami hari ini.',
                style: AppTextStyles.bodySmall.copyWith(
                  color: Colors.white.withValues(alpha: 0.65),
                  fontSize: 12,
                ),
              ),

              // Trial banner — guests only
              if (isGuestUser) ...[
                const SizedBox(height: 14),
                _buildTrialBanner(remainingQuota),
              ],

              // Quick stats (3 stat boxes) — inside navy header
              const SizedBox(height: 20),
              _buildStatRow(
                recentDocumentsAsync: recentDocumentsAsync,
                freeAnalysisValue: freeAnalysisValue,
                freeAnalysisLabel: freeAnalysisLabel,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTrialBanner(int remaining) {
    final isDepleted = remaining <= 0;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.accent.withValues(alpha: 0.2),
        border: Border.all(color: AppColors.accent),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              isDepleted
                  ? 'Kuota gratis sudah habis'
                  : '$remaining analisis tersisa dari 5 gratis',
              style: AppTextStyles.bodySmall.copyWith(
                color: Colors.white.withValues(alpha: 0.9),
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          const SizedBox(width: 10),
          GestureDetector(
            onTap: () => context.go('/register'),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: AppColors.accent,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                'Upgrade',
                style: AppTextStyles.meta.copyWith(
                  color: AppColors.brand,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ─── Stats ──────────────────────────────────────────────────────────

  Widget _buildStatRow({
    required AsyncValue<List<Document>> recentDocumentsAsync,
    required String freeAnalysisValue,
    required String freeAnalysisLabel,
  }) {
    return Row(
      children: [
        Expanded(
          child: StatBox(
            number: recentDocumentsAsync.maybeWhen(
              data: (docs) => docs.length.toString(),
              orElse: () => '-',
            ),
            label: 'Dokumen',
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: StatBox(
            number: recentDocumentsAsync.maybeWhen(
              data: (docs) =>
                  docs
                      .where((d) =>
                          d.riskLevel == 'Tinggi' ||
                          d.riskLevel == 'Sedang')
                      .length
                      .toString(),
              orElse: () => '-',
            ),
            label: 'Berisiko',
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: StatBox(
            number: freeAnalysisValue,
            label: freeAnalysisLabel,
          ),
        ),
      ],
    );
  }

  // ─── Quick Actions ──────────────────────────────────────────────────

  Widget _buildQuickActionsGrid({
    required bool isGuestUser,
    required bool canUseFreeAnalysis,
    required int remainingQuota,
    required AsyncValue<List<Document>> recentDocumentsAsync,
  }) {
    return GridView.count(
      crossAxisCount: 2,
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      children: [
        // Upload Dokumen
        QuickActionCard(
          icon: Icons.cloud_upload_outlined,
          iconColor: AppColors.uploadIcon,
          bgColor: AppColors.uploadBg,
          title: 'Upload\nDokumen',
          onTap: () => _onUploadTap(
            canUseFreeAnalysis: canUseFreeAnalysis,
            remainingQuota: remainingQuota,
            isGuestUser: isGuestUser,
          ),
        ),

        // Scan Dokumen
        QuickActionCard(
          icon: Icons.camera_alt_outlined,
          iconColor: AppColors.scanIcon,
          bgColor: AppColors.scanBg,
          title: 'Scan\nDokumen',
          onTap: () => _onScanTap(
            canUseFreeAnalysis: canUseFreeAnalysis,
            remainingQuota: remainingQuota,
            isGuestUser: isGuestUser,
          ),
        ),

        // Tanya AI — locked for guests
        QuickActionCard(
          icon: Icons.chat_bubble_outline,
          iconColor: AppColors.chatIcon,
          bgColor: AppColors.chatBg,
          title: 'Tanya AI\nLegalEasier',
          locked: isGuestUser,
          onTap: () => _onChatTap(
            isGuestUser: isGuestUser,
            recentDocumentsAsync: recentDocumentsAsync,
          ),
        ),

        // Riwayat Dokumen — locked for guests
        QuickActionCard(
          icon: Icons.history,
          iconColor: AppColors.historyIcon,
          bgColor: AppColors.historyBg,
          title: 'Riwayat\nDokumen',
          locked: isGuestUser,
          onTap: () => _onHistoryTap(isGuestUser: isGuestUser),
        ),
      ],
    );
  }

  // ─── Quick Action Handlers ──────────────────────────────────────────

  Future<void> _onUploadTap({
    required bool canUseFreeAnalysis,
    required int remainingQuota,
    required bool isGuestUser,
  }) async {
    if (!canUseFreeAnalysis) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Kuota gratis (5 analisis) sudah habis. Silakan daftar untuk melanjutkan analisis tanpa batas.',
          ),
          backgroundColor: AppColors.danger,
        ),
      );
      return;
    }

    final messenger = ScaffoldMessenger.of(context);
    final result = await showModalBottomSheet<Document>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const UploadScanBottomSheet(
        initialMethod: UploadMethod.file,
      ),
    );

    if (!mounted || result == null) return;

    ref.invalidate(recentDocumentsProvider);
    final uploadTitle = Uri.encodeComponent(result.filename);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.push(
          '/documents/${result.id}/analysis?title=$uploadTitle');
    });

    if (isGuestUser) {
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            'Dokumen berhasil diupload. Sisa analisis gratis: ${remainingQuota - 1}',
          ),
        ),
      );
    } else {
      messenger.showSnackBar(
        const SnackBar(content: Text('Dokumen berhasil diupload.')),
      );
    }
  }

  Future<void> _onScanTap({
    required bool canUseFreeAnalysis,
    required int remainingQuota,
    required bool isGuestUser,
  }) async {
    if (!canUseFreeAnalysis) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Kuota gratis (5 analisis) sudah habis. Silakan daftar untuk melanjutkan analisis tanpa batas.',
          ),
          backgroundColor: AppColors.danger,
        ),
      );
      return;
    }

    final messenger = ScaffoldMessenger.of(context);
    final result = await showModalBottomSheet<Document>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const UploadScanBottomSheet(),
    );

    if (!mounted || result == null) return;

    ref.invalidate(recentDocumentsProvider);
    final scanTitle = Uri.encodeComponent(result.filename);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.push(
          '/documents/${result.id}/analysis?title=$scanTitle');
    });

    if (isGuestUser) {
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            'Dokumen hasil scan berhasil diupload. Sisa analisis gratis: ${remainingQuota - 1}',
          ),
        ),
      );
    } else {
      messenger.showSnackBar(
        const SnackBar(content: Text('Dokumen hasil scan berhasil diupload.')),
      );
    }
  }

  void _onChatTap({
    required bool isGuestUser,
    required AsyncValue<List<Document>> recentDocumentsAsync,
  }) {
    if (isGuestUser) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Fitur Chat AI hanya tersedia untuk pengguna terdaftar. Silakan daftar untuk melanjutkan.',
          ),
          backgroundColor: AppColors.danger,
        ),
      );
      Future<void>.delayed(const Duration(milliseconds: 500), () {
        if (!mounted) return;
        context.go('/register');
      });
      return;
    }

    recentDocumentsAsync.when(
      data: (documents) {
        if (documents.isEmpty) {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text(
                'Belum ada dokumen. Upload dokumen terlebih dahulu untuk menggunakan chat AI.',
              ),
            ),
          );
          return;
        }
        final document = documents.first;
        final encodedTitle = Uri.encodeComponent(document.filename);
        context.push('/documents/${document.id}/chat?title=$encodedTitle');
      },
      loading: () {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Memuat dokumen terbaru...')),
        );
      },
      error: (error, stackTrace) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Gagal memuat dokumen terbaru. Coba lagi.'),
          ),
        );
      },
    );
  }

  void _onHistoryTap({required bool isGuestUser}) {
    if (isGuestUser) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Riwayat dokumen hanya tersedia untuk pengguna terdaftar.',
          ),
          backgroundColor: AppColors.danger,
        ),
      );
      Future<void>.delayed(const Duration(milliseconds: 500), () {
        if (!mounted) return;
        context.go('/register');
      });
      return;
    }
    context.go('/history');
  }
}
