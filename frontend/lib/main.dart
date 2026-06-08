import 'dart:async';
import 'dart:ui';

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

  // Modern async error handler instead of runZonedGuarded
  PlatformDispatcher.instance.onError = (error, stack) {
    if (kDebugMode) {
      debugPrint('Uncaught async error: $error');
      debugPrintStack(stackTrace: stack);
    }
    return true;
  };

  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  runApp(const ProviderScope(child: LegalEasierApp()));
}


class LegalEasierApp extends StatelessWidget {
  const LegalEasierApp({super.key});

  @override
  Widget build(BuildContext context) {
    // Friendly fallback UI for build errors — only set in non-debug (release) mode
    if (!kDebugMode) {
      ErrorWidget.builder = (FlutterErrorDetails details) {
        const message = 'Terjadi kesalahan aplikasi.';
        return MaterialApp(
          home: Scaffold(
            body: Center(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: const Text(message, textAlign: TextAlign.center),
              ),
            ),
          ),
        );
      };
    }

    return MaterialApp.router(
      debugShowCheckedModeBanner: false,
      title: 'LegalEasier',
      theme: AppTheme.light(),
      routerConfig: AppRouter.router,
    );
  }
}