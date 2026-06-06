import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/auth_repository.dart';
import '../../domain/auth_user.dart';
import '../../data/firebase_auth_repository.dart';

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => FirebaseAuthRepository(),
);

final authNotifierProvider = AsyncNotifierProvider<AuthNotifier, AuthUser?>(
  AuthNotifier.new,
);

class AuthNotifier extends AsyncNotifier<AuthUser?> {
  late final AuthRepository _repository;

  @override
  AuthUser? build() {
    _repository = ref.read(authRepositoryProvider);
    return _repository.currentUser;
  }

  Future<void> loginWithEmailPassword(String email, String password) async {
    state = const AsyncValue.loading();
    try {
      final user = await _repository.loginWithEmailPassword(email, password);
      state = AsyncValue.data(user);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
      rethrow;
    }
  }

  Future<void> registerWithEmailPassword(String email, String password) async {
    state = const AsyncValue.loading();
    try {
      final user = await _repository.registerWithEmailPassword(email, password);
      state = AsyncValue.data(user);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
      rethrow;
    }
  }

  Future<void> loginWithGoogle() async {
    state = const AsyncValue.loading();
    try {
      final user = await _repository.loginWithGoogle();
      state = AsyncValue.data(user);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
      rethrow;
    }
  }

  Future<void> logout() async {
    state = const AsyncValue.loading();
    try {
      await _repository.logout();
      state = const AsyncValue.data(null);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
      rethrow;
    }
  }
}
