import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:legaleasier/features/document/presentation/providers/guest_quota_provider.dart';
import 'package:legaleasier/features/auth/presentation/providers/auth_provider.dart';

/// Simple provider that exposes whether a guest user has reached the free-analysis limit.
final hasReachedLimitProvider = Provider<bool>((ref) {
  final authUser = ref.watch(authNotifierProvider).value;
  final remaining = ref.watch(guestQuotaProvider).value ?? 5;
  return (authUser?.isGuest ?? true) && remaining <= 0;
});

class TrialController {
  final Ref ref;
  TrialController(this.ref);

  Future<void> consumeIfGuest() async {
    final authUser = ref.read(authNotifierProvider).value;
    if (authUser?.isGuest ?? true) {
      try {
        await ref
            .read(guestQuotaProvider.notifier)
            .consumeAnalysis(isGuest: true);
      } catch (_) {
        // ignore errors from persistence
      }
    }
  }

  Future<void> resetQuota() async {
    await ref.read(guestQuotaProvider.notifier).resetQuota();
  }
}

final trialControllerProvider =
    Provider<TrialController>((ref) => TrialController(ref));
