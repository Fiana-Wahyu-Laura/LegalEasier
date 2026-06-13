import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:legaleasier/core/theme/app_theme.dart';
import 'package:legaleasier/features/analysis/presentation/providers/analysis_provider.dart';
import 'package:legaleasier/features/analysis/presentation/widgets/analysis_disclaimer_card.dart';
import 'package:legaleasier/features/analysis/presentation/widgets/analysis_summary_card.dart';
import 'package:legaleasier/features/analysis/presentation/widgets/risk_clause_card.dart';
import 'package:legaleasier/features/analysis/presentation/widgets/risk_overview_card.dart';
import 'package:legaleasier/features/auth/presentation/providers/auth_provider.dart';

class DocumentAnalysisScreen extends ConsumerStatefulWidget {
  final String documentId;
  final String documentTitle;

  const DocumentAnalysisScreen({
    super.key,
    required this.documentId,
    required this.documentTitle,
  });

  @override
  ConsumerState<DocumentAnalysisScreen> createState() =>
      _DocumentAnalysisScreenState();
}

class _DocumentAnalysisScreenState
    extends ConsumerState<DocumentAnalysisScreen>
    with SingleTickerProviderStateMixin {
  Timer? _pollTimer;
  Timer? _elapsedTimer;
  DateTime? _processingStartAt;
  int _elapsedSeconds = 0;
  int _consecutiveErrors = 0;
  late AnimationController _pulseController;

  static const _pollInterval = Duration(seconds: 3);
  static const _elapsedTick = Duration(seconds: 1);
  static const _maxConsecutiveErrors = 5;

  static const _processingSteps = [
    _ProcessingStep('Membaca teks dokumen', Icons.document_scanner_outlined),
    _ProcessingStep('Menganalisis klausul risiko', Icons.search_outlined),
    _ProcessingStep('Menerjemahkan ke bahasa sederhana', Icons.translate_outlined),
    _ProcessingStep('Menyusun ringkasan', Icons.summarize_outlined),
  ];

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _cancelPolling();
    _cancelElapsedTimer();
    _pulseController.dispose();
    super.dispose();
  }

  void _cancelPolling() {
    _pollTimer?.cancel();
    _pollTimer = null;
  }

  void _cancelElapsedTimer() {
    _elapsedTimer?.cancel();
    _elapsedTimer = null;
    _processingStartAt = null;
  }

  void _startPolling() {
    if (_pollTimer != null) return;
    _pollTimer = Timer.periodic(_pollInterval, (_) {
      ref.invalidate(documentAnalysisProvider(widget.documentId));
    });
  }

  void _startElapsedTimer() {
    if (_elapsedTimer != null) return;
    _processingStartAt = DateTime.now();
    _elapsedSeconds = 0;
    _elapsedTimer = Timer.periodic(_elapsedTick, (_) {
      if (!mounted) return;
      setState(() {
        _elapsedSeconds = DateTime.now().difference(_processingStartAt!).inSeconds;
      });
    });
  }

  String _formatElapsed(int seconds) {
    if (seconds < 60) return '$seconds detik';
    final minutes = seconds ~/ 60;
    final remainingSeconds = seconds % 60;
    if (remainingSeconds == 0) return '$minutes menit';
    return '$minutes menit $remainingSeconds detik';
  }

  @override
  Widget build(BuildContext context) {
    final analysisAsyncValue =
        ref.watch(documentAnalysisProvider(widget.documentId));

    // Manage polling & elapsed timer
    analysisAsyncValue.whenData((analysis) {
      if (analysis == null) {
        _startPolling();
        _startElapsedTimer();
      } else {
        _consecutiveErrors = 0;
        _cancelPolling();
        _cancelElapsedTimer();
      }
    });
    if (analysisAsyncValue.hasError) {
      _consecutiveErrors++;
      if (_consecutiveErrors >= _maxConsecutiveErrors) {
        _cancelPolling();
        _cancelElapsedTimer();
      }
      // else: keep polling, skip showing error until threshold reached
    } else {
      _consecutiveErrors = 0;
    }

    final authAsync = ref.watch(authNotifierProvider);
    final isGuest = authAsync.maybeWhen(
      data: (user) => user?.isGuest ?? true,
      orElse: () => true,
    );

    final chatFab = analysisAsyncValue.maybeWhen(
      data: (analysis) {
        if (analysis == null) return null;

        if (isGuest) {
          // Guest users: show lock icon, redirect to limit-gate
          return FloatingActionButton.extended(
            onPressed: () => context.go('/limit-gate'),
            backgroundColor: AppColors.soft,
            foregroundColor: AppColors.text2,
            icon: const Icon(Icons.lock_outline, size: 18),
            label: const Text('Tanya AI'),
          );
        }

        return FloatingActionButton.extended(
          onPressed: () {
            final encodedTitle = Uri.encodeComponent(widget.documentTitle);
            context.push(
                '/documents/${widget.documentId}/chat?title=$encodedTitle');
          },
          icon: const Icon(Icons.chat_bubble_outline),
          label: const Text('Tanya AI'),
        );
      },
      orElse: () => null,
    );

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.documentTitle),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Muat ulang',
            onPressed: () {
              ref.invalidate(documentAnalysisProvider(widget.documentId));
            },
          ),
        ],
      ),
      floatingActionButton: chatFab,
      body: analysisAsyncValue.when(
        loading: () => _buildInitialLoading(),
        error: (error, stackTrace) {
          // Only show fatal error after consecutive failures
          if (_consecutiveErrors >= _maxConsecutiveErrors) {
            return _buildErrorState();
          }
          // Still under threshold — keep showing processing UI
          return _buildProcessingState();
        },
        data: (analysis) {
          if (analysis == null) {
            return _buildProcessingState();
          }

          final summary = analysis.summary?.trim();
          final riskLevel = analysis.riskLevel;

          return SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.documentTitle,
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

  // --- State builders ---

  Widget _buildInitialLoading() {
    return const Center(child: CircularProgressIndicator());
  }

  Widget _buildErrorState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 48, color: AppColors.danger),
            const SizedBox(height: 16),
            Text(
              'Gagal memuat hasil analisis.',
              style: AppTextStyles.bodyLarge.copyWith(color: AppColors.danger),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'Silakan coba lagi atau muat ulang halaman.',
              style: AppTextStyles.bodySmall.copyWith(color: AppColors.text2),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  /// Processing state widget with elapsed time and animated steps.
  Widget _buildProcessingState() {
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const SizedBox(height: 32),

            // --- Animated icon ---
            AnimatedBuilder(
              animation: _pulseController,
              builder: (context, child) {
                final scale =
                    1.0 + (_pulseController.value * 0.08);
                final opacity =
                    1.0 - (_pulseController.value * 0.25);
                return Transform.scale(
                  scale: scale,
                  child: Opacity(
                    opacity: opacity,
                    child: Container(
                      width: 80,
                      height: 80,
                      decoration: BoxDecoration(
                        color: AppColors.brand.withValues(alpha: 0.1),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.auto_awesome,
                        size: 36,
                        color: AppColors.brand,
                      ),
                    ),
                  ),
                );
              },
            ),

            const SizedBox(height: 24),

            // --- Title ---
            Text(
              'Menganalisis Dokumen',
              style: AppTextStyles.screenTitle.copyWith(fontSize: 20),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 4),
            Text(
              'AI kami sedang membaca dan memahami dokumen Anda',
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.text2,
              ),
              textAlign: TextAlign.center,
            ),

            const SizedBox(height: 24),

            // --- Elapsed time badge ---
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.brand.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const SizedBox(
                    width: 14,
                    height: 14,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor:
                          AlwaysStoppedAnimation<Color>(AppColors.brand),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Memproses selama ${_formatElapsed(_elapsedSeconds)}',
                    style: AppTextStyles.label.copyWith(
                      color: AppColors.brand,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 32),

            // --- Processing steps ---
            _buildProcessingSteps(),

            const SizedBox(height: 32),

            // --- Tip card ---
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.soft,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  const Icon(Icons.lightbulb_outline,
                      size: 20, color: AppColors.accent),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Analisis biasanya selesai dalam 30-60 detik '
                      'tergantung ukuran dokumen. Anda tidak perlu '
                      'menunggu di halaman ini.',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.text2,
                        height: 1.4,
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  /// Build the processing steps indicator.
  Widget _buildProcessingSteps() {
    // Advance to next step roughly every 8 seconds to simulate progress.
    final totalSteps = _processingSteps.length;
    final stepIndex = math.min(
      (_elapsedSeconds ~/ 8) % totalSteps,
      totalSteps - 1,
    );

    return Column(
      children: List.generate(totalSteps, (i) {
        final isActive = i == stepIndex;
        final isDone = i < stepIndex;
        final step = _processingSteps[i];

        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Row(
            children: [
              // Step circle
              AnimatedContainer(
                duration: const Duration(milliseconds: 400),
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  color: isDone
                      ? AppColors.brand2.withValues(alpha: 0.15)
                      : isActive
                          ? AppColors.brand.withValues(alpha: 0.1)
                          : Colors.transparent,
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: isDone
                        ? AppColors.brand2
                        : isActive
                            ? AppColors.brand
                            : AppColors.text3.withValues(alpha: 0.4),
                    width: 1.5,
                  ),
                ),
                child: isDone
                    ? const Icon(Icons.check, size: 16, color: AppColors.brand2)
                    : isActive
                        ? const SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor: AlwaysStoppedAnimation<Color>(
                                  AppColors.brand),
                            ),
                          )
                        : null,
              ),
              const SizedBox(width: 12),
              // Step label
              Text(
                step.label,
                style: AppTextStyles.bodyMedium.copyWith(
                  color: isDone
                      ? AppColors.text2
                      : isActive
                          ? AppColors.brand
                          : AppColors.text3,
                  fontWeight:
                      isActive ? FontWeight.w600 : FontWeight.w400,
                ),
              ),
            ],
          ),
        );
      }),
    );
  }

  // --- Result placeholders (when data arrives but some fields missing) ---

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

/// Model for a processing step in the UI.
class _ProcessingStep {
  final String label;
  final IconData icon;

  const _ProcessingStep(this.label, this.icon);
}
