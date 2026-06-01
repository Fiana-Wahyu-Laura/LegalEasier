import 'package:flutter/material.dart';
import 'package:legaleasier/core/theme/app_theme.dart';

class RiskOverviewCard extends StatelessWidget {
  final int? riskScore;
  final String riskLevel;

  const RiskOverviewCard({super.key, required this.riskScore, required this.riskLevel});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Container(
            decoration: BoxDecoration(
              color: AppColors.white,
              borderRadius: BorderRadius.circular(16),
            ),
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Skor Risiko', style: AppTextStyles.label),
                const SizedBox(height: 8),
                Text(
                  riskScore?.toString() ?? '-',
                  style: AppTextStyles.limitTitle.copyWith(color: AppColors.brand),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(width: 12),
        Container(
          decoration: BoxDecoration(
            color: _riskLevelColor(riskLevel).withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(16),
          ),
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Level Risiko', style: AppTextStyles.label),
              const SizedBox(height: 8),
              Text(
                riskLevel,
                style: AppTextStyles.limitTitle.copyWith(
                  color: _riskLevelColor(riskLevel),
                ),
              ),
            ],
          ),
        ),
      ],
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
