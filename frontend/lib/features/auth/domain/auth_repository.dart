import 'auth_user.dart';

abstract class AuthRepository {
  AuthUser? get currentUser;

  Future<AuthUser> loginWithEmailPassword(
    String email,
    String password,
  );

  Future<AuthUser> registerWithEmailPassword(
    String email,
    String password,
  );

  Future<AuthUser> loginWithGoogle();

  Future<AuthUser> loginAnonymously();

  /// Convert the current anonymous account to a permanent email/password account.
  /// Preserves the same UID so existing documents and data are retained.
  Future<AuthUser> linkAnonymousToEmail(String email, String password);

  /// Convert the current anonymous account to a permanent Google account.
  /// Preserves the same UID so existing documents and data are retained.
  Future<AuthUser> linkAnonymousToGoogle();

  Future<void> logout();
}
