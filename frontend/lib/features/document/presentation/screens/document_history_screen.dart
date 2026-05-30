import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:legaleasier/core/theme/app_theme.dart';
import 'package:legaleasier/features/document/domain/document.dart';
import 'package:legaleasier/features/document/presentation/providers/document_provider.dart';

class DocumentHistoryScreen extends ConsumerWidget {
  const DocumentHistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final documentsAsync = ref.watch(documentsProvider((page: 1, limit: 20)));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Riwayat Dokumen'),
      ),
      body: documentsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stackTrace) => Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Text(
              'Gagal memuat riwayat dokumen. Silakan coba lagi.',
              style: AppTextStyles.bodyLarge.copyWith(color: AppColors.danger),
              textAlign: TextAlign.center,
            ),
          ),
        ),
        data: (documents) {
          if (documents.isEmpty) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Text(
                  'Belum ada dokumen di riwayat. Upload dokumen pertama Anda untuk mulai menggunakan LegalEasier.',
                  style: AppTextStyles.bodyLarge.copyWith(color: AppColors.text2),
                  textAlign: TextAlign.center,
                ),
              ),
            );
          }

          return ListView.separated(
            padding: const EdgeInsets.symmetric(vertical: 12),
            itemCount: documents.length,
            separatorBuilder: (context, index) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final document = documents[index];
              final subtitle = document.hasAnalysis
                  ? 'Analisis tersedia • ${document.riskLevel ?? 'Aman'}'
                  : 'Analisis belum selesai';
              final encodedTitle = Uri.encodeComponent(document.filename);

              return ListTile(
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                tileColor: AppColors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                title: Text(
                  document.filename,
                  style: AppTextStyles.bodyLarge.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                subtitle: Text(
                  subtitle,
                  style: AppTextStyles.meta.copyWith(
                    color: document.hasAnalysis ? AppColors.text1 : AppColors.text2,
                  ),
                ),
                trailing: const Icon(Icons.chevron_right, color: AppColors.text3),
                onTap: () {
                  context.go('/documents/${document.id}/analysis?title=$encodedTitle');
                },
              );
            },
          );
        },
      ),
    );
  }
}
