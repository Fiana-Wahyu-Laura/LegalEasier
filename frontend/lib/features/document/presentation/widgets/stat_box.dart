import 'package:flutter/material.dart';
import 'package:legaleasier/core/theme/app_theme.dart';

/// Stat box untuk menampilkan statistik di home screen
/// Grid 3 kolom dengan angka dan label
class StatBox extends StatelessWidget {
  final String number;
  final String label;

  const StatBox({
    super.key,
    required this.number,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.soft,
        borderRadius: BorderRadius.circular(12),
      ),
      padding: const EdgeInsets.all(10),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            number,
            style: AppTextStyles.statNum,
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: AppTextStyles.screenLabel,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
