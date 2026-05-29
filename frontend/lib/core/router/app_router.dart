import 'package:go_router/go_router.dart';

import 'package:legaleasier/features/analysis/presentation/screens/document_analysis_screen.dart';
import 'package:legaleasier/features/document/presentation/screens/home_screen.dart';
import 'package:legaleasier/features/auth/presentation/LoginScreen.dart';
import 'package:legaleasier/features/auth/presentation/RegisterScreen.dart';
import 'package:legaleasier/features/onboarding/presentation/OnboardingScreen.dart';
import 'package:legaleasier/features/onboarding/presentation/SplashScreen.dart';

class AppRouter {
  static final router = GoRouter(
    initialLocation: '/splash',
    routes: [
      GoRoute(
        path: '/splash',
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: '/onboarding',
        builder: (context, state) => const OnboardingScreen(),
      ),
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegisterScreen(),
      ),
      GoRoute(
        path: '/home',
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: '/documents/:id/analysis',
        builder: (context, state) {
          final documentId = state.params['id']!;
          final documentTitle = state.queryParams['title'] ?? 'Detail Dokumen';
          return DocumentAnalysisScreen(
            documentId: documentId,
            documentTitle: documentTitle,
          );
        },
      ),
    ],
  );
}
