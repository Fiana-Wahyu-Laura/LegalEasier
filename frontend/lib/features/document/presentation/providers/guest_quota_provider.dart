import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _guestFreeAnalysesKey = 'guest_free_analyses_remaining';
const _defaultGuestFreeAnalyses = 5;

final guestQuotaProvider =
    AsyncNotifierProvider<GuestQuotaNotifier, int>(GuestQuotaNotifier.new);

class GuestQuotaNotifier extends AsyncNotifier<int> {
  late final SharedPreferences _preferences;

  @override
  Future<int> build() async {
    _preferences = await SharedPreferences.getInstance();
    return _preferences.getInt(_guestFreeAnalysesKey) ?? _defaultGuestFreeAnalyses;
  }

  Future<void> consumeAnalysis({required bool isGuest}) async {
    if (!isGuest) return;

    final currentQuota = state.value ?? _defaultGuestFreeAnalyses;
    if (currentQuota <= 0) {
      state = const AsyncValue.data(0);
      throw Exception('Kuota gratis habis.');
    }

    final nextQuota = currentQuota - 1;
    await _preferences.setInt(_guestFreeAnalysesKey, nextQuota);
    state = AsyncValue.data(nextQuota);
  }

  Future<void> refreshQuota() async {
    final latest = _preferences.getInt(_guestFreeAnalysesKey) ?? _defaultGuestFreeAnalyses;
    state = AsyncValue.data(latest);
  }

  Future<void> resetQuota() async {
    await _preferences.setInt(_guestFreeAnalysesKey, _defaultGuestFreeAnalyses);
    state = const AsyncValue.data(_defaultGuestFreeAnalyses);
  }
}
