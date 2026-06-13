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
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
      child: Wrap(
        spacing: 6,
        runSpacing: 6,
        children: suggestions.map((suggestion) {
          return GestureDetector(
            onTap: () => onSelected(suggestion),
            child: Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
              decoration: BoxDecoration(
                color: AppColors.white,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: Colors.black.withValues(alpha: 0.1),
                  width: 0.5,
                ),
              ),
              child: Text(
                suggestion,
                style:
                    AppTextStyles.chipText.copyWith(color: AppColors.brand2),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}
