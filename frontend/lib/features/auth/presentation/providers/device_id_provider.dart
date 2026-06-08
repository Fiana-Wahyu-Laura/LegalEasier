import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

const _deviceIdKey = 'app_device_id';

/// Provider to get or generate device ID for persistent anonymous session linking.
/// 
/// Device ID is generated once per app install and stored in SharedPreferences.
/// Used to link anonymous user sessions so data persists across logout/login.
final deviceIdProvider = FutureProvider<String>((ref) async {
  final prefs = await SharedPreferences.getInstance();
  
  // Try to get existing device ID
  var deviceId = prefs.getString(_deviceIdKey);
  
  // If not found, generate new one
  if (deviceId == null) {
    deviceId = const Uuid().v4();
    await prefs.setString(_deviceIdKey, deviceId);
  }
  
  return deviceId;
});
