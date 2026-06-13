import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:legaleasier/core/theme/app_theme.dart';
import 'package:legaleasier/features/document/domain/document.dart';
import 'package:legaleasier/features/document/presentation/providers/document_provider.dart';

/// Recent documents section di home screen
class RecentDocumentsSection extends ConsumerWidget {
  const RecentDocumentsSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recentDocumentsAsync = ref.watch(recentDocumentsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Dokumen Terbaru',
          style: AppTextStyles.cardTitle.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 12),
        recentDocumentsAsync.when(
          loading: () => Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 32),
            decoration: BoxDecoration(
              color: AppColors.white,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: Colors.black.withValues(alpha: 0.08),
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
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: Colors.black.withValues(alpha: 0.08),
                width: 0.5,
              ),
            ),
            child: Text(
              'Gagal memuat dokumen. Silakan coba lagi.',
              style: AppTextStyles.bodyLarge.copyWith(color: AppColors.danger),
            ),
          ),
          data: (documents) {
            if (documents.isEmpty) {
              return Container(
                decoration: BoxDecoration(
                  color: AppColors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: Colors.black.withValues(alpha: 0.08),
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

            return Column(
              children: documents
                  .map((document) => _buildDocumentItem(context, document))
                  .toList(),
            );
          },
        ),
      ],
    );
  }

  Widget _buildDocumentItem(BuildContext context, Document document) {
    final hasAnalysis = document.hasAnalysis;
    final subtitle = hasAnalysis
        ? 'Analisis tersedia • ${document.riskLevel ?? 'Aman'}'
        : null;

    return GestureDetector(
      onTap: () {
        final encodedTitle = Uri.encodeComponent(document.filename);
        context.push('/documents/${document.id}/analysis?title=$encodedTitle');
      },
      child: Container(
        width: double.infinity,
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: Colors.black.withValues(alpha: 0.05),
            width: 0.5,
          ),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    document.filename,
                    style: AppTextStyles.bodyLarge.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 8),
                  if (hasAnalysis)
                    Text(
                      subtitle!,
                      style: AppTextStyles.meta.copyWith(
                        color: AppColors.text1,
                      ),
                    )
                  else
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const SizedBox(
                          width: 12,
                          height: 12,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(
                                AppColors.brand),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Sedang dianalisis...',
                          style: AppTextStyles.meta.copyWith(
                            color: AppColors.brand,
                          ),
                        ),
                      ],
                    ),
                ],
              ),
            ),
            const Icon(
              Icons.chevron_right,
              color: AppColors.text3,
            ),
          ],
        ),
      ),
    );
  }
}
