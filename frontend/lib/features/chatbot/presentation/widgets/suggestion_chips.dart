import 'package:flutter/material.dart';
import 'package:legaleasier/core/theme/app_theme.dart';

class SuggestionChips extends StatelessWidget {
  final List<String> suggestions;
  final ValueChanged<String> onSelected;

  const SuggestionChips({
    super.key,
    required this.suggestions,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      color: AppColors.pageBackground,
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 16),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: suggestions.map((suggestion) {
          return ActionChip(
            label: Text(
              suggestion,
              style: AppTextStyles.bodySmall.copyWith(color: AppColors.brand),
            ),
            backgroundColor: AppColors.white,
            labelPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            onPressed: () => onSelected(suggestion),
          );
        }).toList(),
      ),
    );
  }
}
