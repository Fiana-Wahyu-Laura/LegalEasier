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

  Future<void> logout();
}
