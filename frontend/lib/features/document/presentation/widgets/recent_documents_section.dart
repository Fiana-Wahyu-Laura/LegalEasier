import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:legaleasier/core/theme/app_theme.dart';
import 'package:legaleasier/features/document/domain/document.dart';
import 'package:legaleasier/features/document/presentation/providers/document_provider.dart';

/// Recent documents section di home screen.
///
/// When [maxItems] is provided, only the first [maxItems] documents are shown
/// and a "Lihat lebih banyak →" link is displayed below them.
class RecentDocumentsSection extends ConsumerWidget {
  final int? maxItems;
  const RecentDocumentsSection({super.key, this.maxItems});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recentDocumentsAsync = ref.watch(recentDocumentsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                'Dokumen Terbaru',
                style: AppTextStyles.cardTitle.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            if (maxItems != null)
              GestureDetector(
                onTap: () => context.go('/history'),
                child: Text(
                  'Lihat semua →',
                  style: AppTextStyles.meta.copyWith(
                    color: AppColors.brand2,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(height: 12),
        recentDocumentsAsync.when(
          loading: () => Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 32),
            decoration: BoxDecoration(
              color: AppColors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: Colors.black.withValues(alpha: 0.07),
                width: 0.5,
              ),
            ),
            child: const Center(
              child: CircularProgressIndicator(),
            ),
          ),
          error: (error, stackTrace) => Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
            decoration: BoxDecoration(
              color: AppColors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: Colors.black.withValues(alpha: 0.07),
                width: 0.5,
              ),
            ),
            child: Text(
              'Gagal memuat dokumen. Silakan coba lagi.',
              style: AppTextStyles.bodyLarge.copyWith(color: AppColors.danger),
            ),
          ),
          data: (documents) {
            final limit = maxItems;
            if (documents.isEmpty) {
              return Container(
                decoration: BoxDecoration(
                  color: AppColors.white,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: Colors.black.withValues(alpha: 0.07),
                    width: 0.5,
                  ),
                ),
                padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 16),
                child: Center(
                  child: Column(
                    children: [
                      const Icon(
                        Icons.file_copy_outlined,
                        size: 48,
                        color: AppColors.text3,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Belum ada dokumen',
                        style: AppTextStyles.label.copyWith(
                          color: AppColors.text2,
                        ),
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'Upload dokumen pertama Anda sekarang',
                        style: AppTextStyles.meta,
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
              );
            }

            final displayDocs = limit != null && documents.length > limit
                ? documents.take(limit).toList()
                : documents;

            return Column(
              children: [
                ...displayDocs.map(
                    (document) => _buildDocumentItem(context, document)),
                if (limit != null && documents.length > limit)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: SizedBox(
                      width: double.infinity,
                      child: OutlinedButton(
                        onPressed: () => context.go('/history'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppColors.brand2,
                          side: const BorderSide(
                            color: AppColors.brand2,
                            width: 1,
                          ),
                          minimumSize: const Size(double.infinity, 44),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                        child: Text(
                          'Lihat ${documents.length - limit} dokumen lainnya →',
                          style: AppTextStyles.label.copyWith(
                            color: AppColors.brand2,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            );
          },
        ),
      ],
    );
  }

  Widget _buildDocumentItem(BuildContext context, Document document) {
    final hasAnalysis = document.hasAnalysis;

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          onTap: () {
            final encodedTitle = Uri.encodeComponent(document.filename);
            context.push('/documents/${document.id}/analysis?title=$encodedTitle');
          },
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: Colors.black.withValues(alpha: 0.07),
                width: 0.5,
              ),
            ),
            child: Row(
              children: [
                // Document icon
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: AppColors.soft,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(
                    Icons.description_outlined,
                    size: 20,
                    color: AppColors.brand,
                  ),
                ),
                const SizedBox(width: 12),

                // Document info
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        document.filename,
                        style: AppTextStyles.bodyMedium.copyWith(
                          fontWeight: FontWeight.w500,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          if (hasAnalysis && document.riskLevel != null) ...[
                            _buildRiskBadge(document.riskLevel!),
                            const SizedBox(width: 8),
                          ],
                          if (!hasAnalysis) ...[
                            _buildAnalyzingBadge(),
                            const SizedBox(width: 8),
                          ],
                          Text(
                            _formatDate(document.uploadedAt),
                            style: AppTextStyles.meta,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),

                const Icon(
                  Icons.chevron_right,
                  size: 20,
                  color: AppColors.text3,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildRiskBadge(String riskLevel) {
    final (Color bg, Color text) = switch (riskLevel) {
      'Tinggi' => (AppColors.dangerBg, AppColors.danger),
      'Sedang' => (AppColors.warnBg, AppColors.warn),
      _ => (AppColors.okBg, AppColors.ok),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        riskLevel,
        style: AppTextStyles.badgeText.copyWith(color: text),
      ),
    );
  }

  Widget _buildAnalyzingBadge() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: AppColors.soft,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        'Menganalisis...',
        style: AppTextStyles.badgeText.copyWith(color: AppColors.text2),
      ),
    );
  }

  String _formatDate(DateTime date) {
    final now = DateTime.now();
    final diff = now.difference(date);
    if (diff.inDays == 0) return 'Hari ini';
    if (diff.inDays == 1) return 'Kemarin';
    if (diff.inDays < 7) return '${diff.inDays} hari lalu';
    return '${date.day}/${date.month}/${date.year}';
  }
}
