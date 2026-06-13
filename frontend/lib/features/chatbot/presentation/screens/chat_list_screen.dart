import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:legaleasier/core/theme/app_theme.dart';
import 'package:legaleasier/features/document/domain/document.dart';
import 'package:legaleasier/features/document/presentation/providers/document_provider.dart';

/// Chat landing screen — shown when the Chat tab in bottom nav is tapped.
/// Lists documents available for AI chat.
class ChatListScreen extends ConsumerWidget {
  const ChatListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final documentsAsync = ref.watch(recentDocumentsProvider);

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppBar(
        backgroundColor: AppColors.brand,
        title: Text(
          'Chat AI',
          style: AppTextStyles.homeTitle.copyWith(fontSize: 20),
        ),
        elevation: 0,
      ),
      body: documentsAsync.when(
        data: (documents) {
          final analyzableDocs = documents
              .where((d) => d.hasAnalysis)
              .toList();

          if (analyzableDocs.isEmpty) {
            return _buildEmptyState(context);
          }

          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: analyzableDocs.length,
            itemBuilder: (context, index) {
              final doc = analyzableDocs[index];
              return _buildDocumentItem(context, doc);
            },
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _buildEmptyState(context),
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: AppColors.brand.withValues(alpha: 0.08),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.chat_bubble_outline,
                size: 36,
                color: AppColors.brand,
              ),
            ),
            const SizedBox(height: 20),
            Text(
              'Belum ada dokumen',
              style: AppTextStyles.screenTitle.copyWith(fontSize: 18),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'Upload dan analisis dokumen terlebih dahulu, '
              'lalu kamu bisa bertanya ke AI tentang isinya.',
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.text2,
                height: 1.5,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () => context.go('/home'),
              icon: const Icon(Icons.upload, size: 18),
              label: const Text('Upload Dokumen'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.brand,
                foregroundColor: AppColors.white,
                minimumSize: const Size(200, 44),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDocumentItem(BuildContext context, Document doc) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          onTap: () {
            final encodedTitle = Uri.encodeComponent(doc.filename);
            context.push('/documents/${doc.id}/chat?title=$encodedTitle');
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
                        doc.filename,
                        style: AppTextStyles.bodyMedium.copyWith(
                          fontWeight: FontWeight.w500,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          if (doc.riskLevel != null) ...[
                            _buildRiskBadge(doc.riskLevel!),
                            const SizedBox(width: 8),
                          ],
                          Text(
                            _formatDate(doc.uploadedAt),
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

  String _formatDate(DateTime date) {
    final now = DateTime.now();
    final diff = now.difference(date);
    if (diff.inDays == 0) return 'Hari ini';
    if (diff.inDays == 1) return 'Kemarin';
    if (diff.inDays < 7) return '${diff.inDays} hari lalu';
    return '${date.day}/${date.month}/${date.year}';
  }
}
