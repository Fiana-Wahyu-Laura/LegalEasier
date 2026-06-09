import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../providers/document_provider.dart';

const _guestFreeAnalysesKey = 'guest_free_analyses_remaining';
const _defaultGuestFreeAnalyses = 5;

final guestQuotaProvider =
    AsyncNotifierProvider<GuestQuotaNotifier, int>(GuestQuotaNotifier.new);

/// GuestQuotaNotifier — single source of truth is the backend.
///
/// SharedPreferences serves only as an optimistic local cache. The real quota
/// is fetched from GET /guest/quota and from the upload response.
class GuestQuotaNotifier extends AsyncNotifier<int> {
  late final SharedPreferences _preferences;

  @override
  Future<int> build() async {
    _preferences = await SharedPreferences.getInstance();

    // Start with local cache for instant display, then sync from server
    final cached = _preferences.getInt(_guestFreeAnalysesKey) ?? _defaultGuestFreeAnalyses;

    // Sync from backend in the background
    _syncFromBackend();

    return cached;
  }

  Future<void> _syncFromBackend() async {
    try {
      final repository = ref.read(documentRepositoryProvider);
      final quota = await repository.getGuestQuota();

      final isGuest = quota['is_guest'] as bool? ?? false;
      if (!isGuest) {
        // Registered user — no quota limit needed
        state = const AsyncValue.data(999);
        return;
      }

      final remaining = quota['remaining'] as int? ?? _defaultGuestFreeAnalyses;
      await _preferences.setInt(_guestFreeAnalysesKey, remaining);
      state = AsyncValue.data(remaining);
    } catch (e) {
      // If backend is unreachable, fall back to cached value
      if (kDebugMode) {
        debugPrint('[GuestQuota] Failed to sync from backend: $e');
      }
    }
  }

  /// Update quota from an upload response that includes remaining_quota.
  /// This is the primary sync point after each upload/scan.
  void updateFromUploadResponse(int remaining) {
    _preferences.setInt(_guestFreeAnalysesKey, remaining);
    state = AsyncValue.data(remaining);
  }

  /// Consume one analysis locally (optimistic update).
  /// The backend has already consumed it; this keeps the local cache in sync.
  Future<void> consumeAnalysis({required bool isGuest}) async {
    if (!isGuest) return;

    final currentQuota = state.value ?? _defaultGuestFreeAnalyses;
    if (currentQuota <= 0) {
      state = const AsyncValue.data(0);
      return;
    }

    final nextQuota = currentQuota - 1;
    await _preferences.setInt(_guestFreeAnalysesKey, nextQuota);
    state = AsyncValue.data(nextQuota);
  }

  /// Force refresh from backend.
  Future<void> refreshQuota() async {
    await _syncFromBackend();
  }

  /// Reset quota (for testing / debugging).
  Future<void> resetQuota() async {
    await _preferences.setInt(_guestFreeAnalysesKey, _defaultGuestFreeAnalyses);
    state = const AsyncValue.data(_defaultGuestFreeAnalyses);
  }
}
