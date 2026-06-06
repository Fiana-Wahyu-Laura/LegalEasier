import 'package:flutter/material.dart';
import 'package:legaleasier/core/theme/app_theme.dart';

/// Trial banner yang menampilkan sisa analisis gratis
class TrialBanner extends StatelessWidget {
  final int remaining;
  final VoidCallback? onUpgradeTap;

  const TrialBanner({
    super.key,
    this.remaining = 5,
    this.onUpgradeTap,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.accentLight.withValues(alpha: 0.18),
        border: Border.all(
          color: AppColors.accent,
          width: 1,
        ),
        borderRadius: BorderRadius.circular(12),
      ),
      padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Coba gratis LegalEasy',
                  style: AppTextStyles.label.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Sisa: $remaining analisis gratis',
                  style: AppTextStyles.meta,
                ),
              ],
            ),
          ),
          GestureDetector(
            onTap: onUpgradeTap,
            child: Container(
              decoration: BoxDecoration(
                color: AppColors.accent,
                borderRadius: BorderRadius.circular(10),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
              child: Text(
                'Upgrade',
                style: AppTextStyles.badgeText.copyWith(
                  color: AppColors.brand,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
