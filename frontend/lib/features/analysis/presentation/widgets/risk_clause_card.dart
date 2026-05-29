import 'package:flutter/material.dart';
import 'package:legaleasier/core/theme/app_theme.dart';
import 'package:legaleasier/features/analysis/domain/analysis_result.dart';

class RiskClauseCard extends StatelessWidget {
  final RiskClause clause;

  const RiskClauseCard({super.key, required this.clause});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.black.withOpacity(0.06)),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 8,
                height: 8,
                margin: const EdgeInsets.only(top: 6, right: 10),
                decoration: BoxDecoration(
                  color: _riskLevelColor(clause.riskLevel),
                  shape: BoxShape.circle,
                ),
              ),
              Expanded(
                child: Text(
                  clause.clauseText,
                  style: AppTextStyles.bodyLarge,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text('Bahasa sederhana', style: AppTextStyles.label),
          const SizedBox(height: 8),
          Text(
            clause.plainLanguage,
            style: AppTextStyles.bodyMedium,
          ),
          const SizedBox(height: 12),
          Text(
            'Confidence: ${clause.confidence.toStringAsFixed(2)}',
            style: AppTextStyles.meta,
          ),
        ],
      ),
    );
  }

  Color _riskLevelColor(String level) {
    switch (level) {
      case 'Tinggi':
        return AppColors.danger;
      case 'Sedang':
        return AppColors.warn;
      case 'Rendah':
      case 'Aman':
        return AppColors.ok;
      default:
        return AppColors.text2;
    }
  }
}
