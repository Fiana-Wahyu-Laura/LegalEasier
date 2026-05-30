// This is a basic Flutter widget test for LegalEasier app.

import 'dart:ui' show Size;
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:legaleasier/main.dart';

void main() {
  testWidgets('LegalEasier app smoke test', (WidgetTester tester) async {
    // Set a larger virtual window size to avoid layout overflow in tests
    TestWidgetsFlutterBinding.ensureInitialized();
    tester.view.physicalSize = const Size(1080, 1920);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    // Build our app
    await tester.pumpWidget(
      const ProviderScope(
        child: LegalEasierApp(),
      ),
    );
    await tester.pumpAndSettle();

    // Verify app launched without errors
    expect(find.byType(LegalEasierApp), findsOneWidget);
  });
}
