import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'package:legaleasier/core/theme/app_theme.dart';
import 'package:legaleasier/features/analysis/presentation/screens/document_analysis_screen.dart';
import 'package:legaleasier/features/chatbot/presentation/screens/chat_screen.dart';
import 'package:legaleasier/features/chatbot/presentation/screens/chat_list_screen.dart';
import 'package:legaleasier/features/auth/presentation/limit_gate_screen.dart';
import 'package:legaleasier/features/auth/presentation/screens/profile_screen.dart';
import 'package:legaleasier/features/document/presentation/screens/document_history_screen.dart';
import 'package:legaleasier/features/document/presentation/screens/home_screen.dart';
import 'package:legaleasier/features/auth/presentation/login_screen.dart';
import 'package:legaleasier/features/auth/presentation/register_screen.dart';
import 'package:legaleasier/features/onboarding/presentation/onboarding_screen.dart';

/// Maps path prefixes to bottom nav tab indices.
int _tabIndexForPath(String path) {
  if (path.startsWith('/home') || path.startsWith('/documents/')) return 0;
  if (path.startsWith('/history')) return 1;
  if (path.startsWith('/chats')) return 2;
  if (path.startsWith('/profile')) return 3;
  return 0;
}

/// Shell widget that wraps all main app routes with a BottomNavigationBar.
class _AppShell extends StatelessWidget {
  final Widget child;
  final GoRouterState state;

  const _AppShell({required this.state, required this.child});

  static const _tabRoutes = ['/home', '/history', '/chats', '/profile'];

  @override
  Widget build(BuildContext context) {
    final currentIndex = _tabIndexForPath(state.uri.path);

    return Scaffold(
      body: child,
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          border: Border(
            top: BorderSide(
              color: Colors.black.withValues(alpha: 0.1),
              width: 0.5,
            ),
          ),
        ),
        child: BottomNavigationBar(
          type: BottomNavigationBarType.fixed,
          backgroundColor: AppColors.white,
          selectedItemColor: AppColors.brand,
          unselectedItemColor: AppColors.text3,
          selectedLabelStyle: AppTextStyles.navLabel.copyWith(
            color: AppColors.brand,
          ),
          unselectedLabelStyle: AppTextStyles.navLabel,
          elevation: 0,
          currentIndex: currentIndex,
          onTap: (index) {
            if (index == currentIndex) return;
            context.go(_tabRoutes[index]);
          },
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.home_outlined, size: 20),
              activeIcon: Icon(Icons.home, size: 20),
              label: 'Beranda',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.folder_outlined, size: 20),
              activeIcon: Icon(Icons.folder, size: 20),
              label: 'Dokumen',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.chat_bubble_outline, size: 20),
              activeIcon: Icon(Icons.chat_bubble, size: 20),
              label: 'Chat',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.person_outline, size: 20),
              activeIcon: Icon(Icons.person, size: 20),
              label: 'Profil',
            ),
          ],
        ),
      ),
    );
  }
}

class AppRouter {
  static String _initialLocation() {
    final user = FirebaseAuth.instance.currentUser;
    if (user != null && !user.isAnonymous) return '/home';
    return '/onboarding';
  }

  static final router = GoRouter(
    initialLocation: _initialLocation(),
    routes: [
      // ── Auth / Onboarding (no bottom nav) ──
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
        path: '/limit-gate',
        builder: (context, state) => const LimitGateScreen(),
      ),

      // ── Main App Shell (WITH bottom nav) ──
      ShellRoute(
        builder: (context, state, child) =>
            _AppShell(state: state, child: child),
        routes: [
          GoRoute(
            path: '/home',
            builder: (context, state) => const HomeScreen(),
          ),
          GoRoute(
            path: '/history',
            builder: (context, state) => const DocumentHistoryScreen(),
          ),
          GoRoute(
            path: '/chats',
            builder: (context, state) => const ChatListScreen(),
          ),
          GoRoute(
            path: '/profile',
            builder: (context, state) => const ProfileScreen(),
          ),
          GoRoute(
            path: '/documents/:id/analysis',
            builder: (context, state) {
              final documentId = state.pathParameters['id']!;
              final documentTitle =
                  state.uri.queryParameters['title'] ?? 'Detail Dokumen';
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
              final documentTitle =
                  state.uri.queryParameters['title'] ?? 'Chat AI LegalEasy';
              return ChatScreen(
                documentId: documentId,
                documentTitle: documentTitle,
              );
            },
          ),
        ],
      ),
    ],
  );
}
