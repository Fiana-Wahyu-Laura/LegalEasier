import 'package:flutter/material.dart';
import 'package:legaleasier/core/theme/app_theme.dart';

class AnalysisSummaryCard extends StatelessWidget {
  final String summary;

  const AnalysisSummaryCard({super.key, required this.summary});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.all(16),
      child: Text(
        summary,
        style: AppTextStyles.bodyLarge,
      ),
    );
  }
}
