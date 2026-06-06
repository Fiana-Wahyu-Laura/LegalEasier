import 'package:flutter/material.dart';
import 'package:legaleasier/core/theme/app_theme.dart';

class AnalysisDisclaimerCard extends StatelessWidget {
  final String disclaimer;

  const AnalysisDisclaimerCard({super.key, required this.disclaimer});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppColors.gateBg,
        borderRadius: BorderRadius.circular(16),
      ),
      padding: const EdgeInsets.all(16),
      child: Text(
        disclaimer,
        style: AppTextStyles.bodySmall.copyWith(color: AppColors.text2),
      ),
    );
  }
}
