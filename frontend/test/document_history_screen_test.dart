import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:legaleasier/features/document/presentation/screens/document_history_screen.dart';
import 'package:legaleasier/features/document/domain/document.dart';
import 'package:legaleasier/features/document/presentation/providers/document_provider.dart';

void main() {
  group('DocumentHistoryScreen', () {
    final docA = Document(
      id: '1',
      filename: 'Invoice A',
      uploadedAt: DateTime.parse('2026-01-01T00:00:00Z'),
      riskScore: 90,
      riskLevel: 'Tinggi',
      hasAnalysis: true,
      fileType: 'pdf',
    );

    final docB = Document(
      id: '2',
      filename: 'Contract B',
      uploadedAt: DateTime.parse('2026-02-01T00:00:00Z'),
      riskScore: null,
      riskLevel: null,
      hasAnalysis: false,
      fileType: 'pdf',
    );

    final docC = Document(
      id: '3',
      filename: 'Agreement C',
      uploadedAt: DateTime.parse('2026-03-01T00:00:00Z'),
      riskScore: 10,
      riskLevel: 'Aman',
      hasAnalysis: true,
      fileType: 'pdf',
    );

    testWidgets('renders documents from provider', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            documentsProvider((page: 1, limit: 100)).overrideWith(
              (ref) => Future.value([docA, docB, docC]),
            ),
          ],
          child: const MaterialApp(home: DocumentHistoryScreen()),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Invoice A'), findsOneWidget);
      expect(find.text('Contract B'), findsOneWidget);
      expect(find.text('Agreement C'), findsOneWidget);
    });

    testWidgets('search shows filtered results', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            documentsProvider((page: 1, limit: 100)).overrideWith(
              (ref) => Future.value([docA, docB, docC]),
            ),
            searchDocumentsProvider('invoice').overrideWith(
              (ref) => Future.value([docA]),
            ),
          ],
          child: const MaterialApp(home: DocumentHistoryScreen()),
        ),
      );

      await tester.pumpAndSettle();

      // Enter search query
      await tester.enterText(find.byType(TextField), 'invoice');
      await tester.pumpAndSettle();

      expect(find.text('Invoice A'), findsOneWidget);
      expect(find.text('Contract B'), findsNothing);
      expect(find.text('Agreement C'), findsNothing);
    });

    testWidgets('filters by risk level and "Hanya Ter-analisis"', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            documentsProvider((page: 1, limit: 100)).overrideWith(
              (ref) => Future.value([docA, docB, docC]),
            ),
          ],
          child: const MaterialApp(home: DocumentHistoryScreen()),
        ),
      );

      await tester.pumpAndSettle();

      // Tap 'Tinggi' choice chip
      final tinggiChip = find.widgetWithText(ChoiceChip, 'Tinggi');
      expect(tinggiChip, findsOneWidget);
      await tester.tap(tinggiChip);
      await tester.pumpAndSettle();

      expect(find.text('Invoice A'), findsOneWidget);
      expect(find.text('Agreement C'), findsNothing);

      // Toggle 'Hanya Ter-analisis'
      final onlyAnalyzed = find.widgetWithText(FilterChip, 'Hanya Ter-analisis');
      expect(onlyAnalyzed, findsOneWidget);
      await tester.tap(onlyAnalyzed);
      await tester.pumpAndSettle();

      // docB is not analyzed so it should not be shown; Invoice A stays
      expect(find.text('Invoice A'), findsOneWidget);
      expect(find.text('Contract B'), findsNothing);
    });
  });
}
