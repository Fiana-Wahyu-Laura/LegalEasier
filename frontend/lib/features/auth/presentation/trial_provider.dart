import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:legaleasier/features/document/presentation/providers/guest_quota_provider.dart';
import 'package:legaleasier/features/auth/presentation/providers/auth_provider.dart';

/// Simple provider that exposes whether a guest user has reached the free-analysis limit.
final hasReachedLimitProvider = Provider<bool>((ref) {
  final authUser = ref.watch(authNotifierProvider).value;
  final remaining = ref.watch(guestQuotaProvider).value ?? 5;
  return (authUser?.isGuest ?? false) && remaining <= 0;
});

/// TrialController is the single entry point for guest quota operations.
///
/// All upload/scan flows should use this controller rather than calling
/// GuestQuotaNotifier directly. This ensures consistent behaviour and
/// makes it easy to add side effects (analytics, etc.) later.
class TrialController {
  final Ref ref;
  TrialController(this.ref);

  /// Update local quota from the upload response provided by the backend.
  /// The backend is the single source of truth — this just syncs the cache.
  void syncFromUploadResponse(int remainingQuota) {
    ref.read(guestQuotaProvider.notifier).updateFromUploadResponse(remainingQuota);
  }

  /// Optimistic local decrement after a successful upload.
  /// The backend has already consumed the slot; this keeps the UI in sync.
  Future<void> consumeIfGuest() async {
    final authUser = ref.read(authNotifierProvider).value;
    if (authUser?.isGuest ?? false) {
      await ref
          .read(guestQuotaProvider.notifier)
          .consumeAnalysis(isGuest: true);
    }
  }

  /// Force-refresh quota from the backend.
  Future<void> refreshQuota() async {
    await ref.read(guestQuotaProvider.notifier).refreshQuota();
  }
}

final trialControllerProvider =
    Provider<TrialController>((ref) => TrialController(ref));
