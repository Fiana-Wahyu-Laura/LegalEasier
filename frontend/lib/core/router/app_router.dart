import 'package:go_router/go_router.dart';

import 'package:legaleasier/features/analysis/presentation/screens/document_analysis_screen.dart';
import 'package:legaleasier/features/chatbot/presentation/screens/chat_screen.dart';
import 'package:legaleasier/features/auth/presentation/limit_gate_screen.dart';
import 'package:legaleasier/features/document/presentation/screens/document_history_screen.dart';
import 'package:legaleasier/features/document/presentation/screens/home_screen.dart';
import 'package:legaleasier/features/auth/presentation/login_screen.dart';
import 'package:legaleasier/features/auth/presentation/register_screen.dart';
import 'package:legaleasier/features/onboarding/presentation/onboarding_screen.dart';
import 'package:legaleasier/features/onboarding/presentation/splash_screen.dart';

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
        path: '/history',
        builder: (context, state) => const DocumentHistoryScreen(),
      ),
      GoRoute(
        path: '/documents/:id/analysis',
        builder: (context, state) {
          final documentId = state.pathParameters['id']!;
          final documentTitle = state.uri.queryParameters['title'] ?? 'Detail Dokumen';
          return DocumentAnalysisScreen(
            documentId: documentId,
            documentTitle: documentTitle,
          );
        },
      ),
      GoRoute(
        path: '/documents/:id/chat',
        builder: (context, state) {
          final documentId = state.pathParameters['id']!;
          final documentTitle = state.uri.queryParameters['title'] ?? 'Chat AI LegalEasy';
          return ChatScreen(
            documentId: documentId,
            documentTitle: documentTitle,
          );
        },
      ),
      GoRoute(
        path: '/limit-gate',
        builder: (context, state) => const LimitGateScreen(),
      ),
    ],
  );
}
