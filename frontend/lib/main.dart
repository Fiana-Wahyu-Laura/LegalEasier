import 'dart:async';
import 'dart:ui';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'firebase_options.dart'; // ← tambahkan ini

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Generate device ID early for guest session persistence (#11).
  // The Dio interceptor reads this from SharedPreferences to send
  // as X-Device-ID header, enabling backend to restore guest sessions.
  await _ensureDeviceId();

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

  // Guest (anonymous) sessions are ephemeral — sign them out on restart.
  // Registered users stay logged in and skip straight to home.
  final currentUser = FirebaseAuth.instance.currentUser;
  if (currentUser != null && currentUser.isAnonymous) {
    await FirebaseAuth.instance.signOut();
  }

  runApp(const ProviderScope(child: LegalEasierApp()));
}

/// Generate and persist a device ID on first launch.
///
/// Used for guest session persistence: the backend can link anonymous
/// sessions from the same device. Must run before Firebase init so the
/// Dio interceptor can pick it up on the first API call.
Future<void> _ensureDeviceId() async {
  const key = 'app_device_id';
  final prefs = await SharedPreferences.getInstance();
  if (!prefs.containsKey(key)) {
    await prefs.setString(key, const Uuid().v4());
  }
}

class LegalEasierApp extends StatelessWidget {
  const LegalEasierApp({super.key});

  @override
  Widget build(BuildContext context) {
    // Friendly fallback UI for build errors — only set in non-debug (release) mode
    if (!kDebugMode) {
      ErrorWidget.builder = (FlutterErrorDetails details) {
        const message = 'Terjadi kesalahan aplikasi.';
        return const MaterialApp(
          home: Scaffold(
            body: Center(
              child: Padding(
                padding: EdgeInsets.all(16.0),
                child: Text(message, textAlign: TextAlign.center),
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