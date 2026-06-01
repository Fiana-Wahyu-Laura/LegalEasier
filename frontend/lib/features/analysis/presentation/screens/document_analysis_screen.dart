import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:legaleasier/core/theme/app_theme.dart';
import 'package:legaleasier/features/analysis/presentation/providers/analysis_provider.dart';
import 'package:legaleasier/features/analysis/presentation/widgets/analysis_disclaimer_card.dart';
import 'package:legaleasier/features/analysis/presentation/widgets/analysis_summary_card.dart';
import 'package:legaleasier/features/analysis/presentation/widgets/risk_clause_card.dart';
import 'package:legaleasier/features/analysis/presentation/widgets/risk_overview_card.dart';

class DocumentAnalysisScreen extends ConsumerWidget {
  final String documentId;
  final String documentTitle;

  const DocumentAnalysisScreen({
    super.key,
    required this.documentId,
    required this.documentTitle,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final analysisAsyncValue = ref.watch(documentAnalysisProvider(documentId));

    final chatFab = analysisAsyncValue.maybeWhen(
      data: (analysis) {
        if (analysis == null) return null;
        return FloatingActionButton.extended(
          onPressed: () {
            final encodedTitle = Uri.encodeComponent(documentTitle);
            context.go('/documents/$documentId/chat?title=$encodedTitle');
          },
          icon: const Icon(Icons.chat_bubble_outline),
          label: const Text('Tanya AI'),
        );
      },
      orElse: () => null,
    );

    return Scaffold(
      appBar: AppBar(
        title: Text(documentTitle),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Muat ulang',
            onPressed: () {
              ref.invalidate(documentAnalysisProvider(documentId));
            },
          ),
        ],
      ),
      floatingActionButton: chatFab,
      body: analysisAsyncValue.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stackTrace) => Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Text(
              'Gagal memuat hasil analisis. Silakan coba lagi.',
              style: AppTextStyles.bodyLarge.copyWith(color: AppColors.danger),
              textAlign: TextAlign.center,
            ),
          ),
        ),
        data: (analysis) {
          if (analysis == null) {
            return Center(
              child: const Padding(
                padding: EdgeInsets.symmetric(horizontal: 24),
                child: Text(
                  'Analisis dokumen belum tersedia. Silakan periksa kembali setelah beberapa saat.',
                  style: AppTextStyles.bodyLarge,
                  textAlign: TextAlign.center,
                ),
              ),
            );
          }

          final summary = analysis.summary?.trim();
          final riskLevel = analysis.riskLevel;

          return SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  documentTitle,
                  style: AppTextStyles.sectionTitle,
                ),
                const SizedBox(height: 8),
                const Text(
                  'Ringkasan analisis dokumen',
                  style: AppTextStyles.label,
                ),
                const SizedBox(height: 16),
                if (summary != null && summary.isNotEmpty)
                  AnalysisSummaryCard(summary: summary)
                else
                  _buildEmptySummaryCard(),
                const SizedBox(height: 20),
                RiskOverviewCard(
                  riskScore: analysis.riskScore,
                  riskLevel: riskLevel,
                ),
                const SizedBox(height: 16),
                if (analysis.riskClauses.isEmpty)
                  _buildNoRiskClauseCard()
                else
                  ...analysis.riskClauses.map(
                    (clause) => RiskClauseCard(clause: clause),
                  ),
                const SizedBox(height: 20),
                AnalysisDisclaimerCard(disclaimer: analysis.disclaimer),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildEmptySummaryCard() {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
      ),
      padding: const EdgeInsets.all(16),
      child: Text(
        'Ringkasan belum tersedia untuk dokumen ini.',
        style: AppTextStyles.bodyLarge.copyWith(color: AppColors.text2),
      ),
    );
  }

  Widget _buildNoRiskClauseCard() {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
      ),
      padding: const EdgeInsets.all(16),
      child: Text(
        'Tidak ditemukan klausul risiko yang signifikan. Dokumen tampak aman untuk saat ini.',
        style: AppTextStyles.bodyLarge.copyWith(color: AppColors.text2),
      ),
    );
  }
}
