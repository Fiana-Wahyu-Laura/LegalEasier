import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'firebase_options.dart'; // ← tambahkan ini

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Global Flutter error handler
  FlutterError.onError = (FlutterErrorDetails details) {
    FlutterError.presentError(details);
    if (kDebugMode) {
      // In debug, print full details
      debugPrint(details.toString());
    }
    // In production, send to analytics/monitoring here
  };

  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  // Run app inside a guarded zone to catch uncaught async errors
  runZonedGuarded(() {
    runApp(const ProviderScope(child: LegalEasierApp()));
  }, (error, stack) {
    // Log uncaught errors from the zone. Replace with crash reporting if available.
    if (kDebugMode) {
      debugPrint('Uncaught zone error: $error');
      debugPrintStack(stackTrace: stack);
    }
  });
}

class LegalEasierApp extends StatelessWidget {
  const LegalEasierApp({super.key});

  @override
  Widget build(BuildContext context) {
    // Friendly fallback UI for build errors
    ErrorWidget.builder = (FlutterErrorDetails details) {
      final message = kDebugMode ? details.exceptionAsString() : 'Terjadi kesalahan aplikasi.';
      return MaterialApp(
        home: Scaffold(
          body: Center(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Text(message, textAlign: TextAlign.center),
            ),
          ),
        ),
      );
    };

    return MaterialApp.router(
      debugShowCheckedModeBanner: false,
      title: 'LegalEasier',
      theme: AppTheme.light(),
      routerConfig: AppRouter.router,
    );
  }
}