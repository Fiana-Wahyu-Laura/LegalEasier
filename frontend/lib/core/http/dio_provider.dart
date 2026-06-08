import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Global Dio provider untuk HTTP requests
final dioProvider = Provider<Dio>((ref) {
  const configuredBackendBaseUrl = String.fromEnvironment('BACKEND_BASE_URL');
  final backendBaseUrl = configuredBackendBaseUrl.isNotEmpty
      ? configuredBackendBaseUrl
      : _defaultBackendBaseUrl();
  final baseUrl = _buildBackendBaseUrl(backendBaseUrl);

  final dio = Dio(
    BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
      sendTimeout: const Duration(seconds: 60), // longer for uploads
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ),
  );

  // Firebase auth interceptor — attach ID token and device ID to every request
  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        final user = FirebaseAuth.instance.currentUser;
        if (user != null) {
          try {
            // Get fresh ID token for API authentication
            final idToken = await user.getIdToken();
            if (idToken == null || idToken.isEmpty) {
              if (kDebugMode) {
                debugPrint('[Auth] WARNING: ID token is empty for user: ${user.uid}');
              }
            } else {
              options.headers['Authorization'] = 'Bearer $idToken';
              if (kDebugMode) {
                debugPrint('[Auth] ID token attached (${idToken.length} chars), user: ${user.uid}');
              }
            }
          } catch (e) {
            if (kDebugMode) {
              debugPrint('[Auth] ERROR getting ID token: $e');
            }
          }
        } else {
          if (kDebugMode) {
            debugPrint('[Auth] WARNING: No current user in interceptor');
          }
        }

        // Attach device ID for anonymous session linking
        try {
          final prefs = await SharedPreferences.getInstance();
          final deviceId = prefs.getString('app_device_id');
          if (deviceId != null) {
            options.headers['X-Device-ID'] = deviceId;
            if (kDebugMode) {
              debugPrint('[Auth] Device ID attached: $deviceId');
            }
          }
        } catch (e) {
          if (kDebugMode) {
            debugPrint('[Auth] WARNING: Could not attach device ID: $e');
          }
        }

        return handler.next(options);
      },
    ),
  );

  // Retry interceptor — auto-retry on 5xx and timeouts
  dio.interceptors.add(_RetryInterceptor(dio: dio));

  if (kDebugMode) {
    dio.interceptors.add(
      LogInterceptor(
        requestHeader: false,
        requestBody: false,
        responseHeader: false,
        responseBody: false,
      ),
    );
  }

  return dio;
});

/// Retry interceptor for transient server errors and timeouts.
///
/// Retries up to [maxRetries] times with exponential backoff.
/// Only retries on 5xx status codes and timeout exceptions.
class _RetryInterceptor extends Interceptor {
  final Dio dio;
  final int maxRetries;

  _RetryInterceptor({required this.dio, this.maxRetries = 2});

  @override
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    final isRetryable = _isRetryableError(err);
    final attempt = (err.requestOptions.extra['_retryAttempt'] as int?) ?? 0;

    if (isRetryable && attempt < maxRetries) {
      final nextAttempt = attempt + 1;
      final delay = Duration(milliseconds: 500 * nextAttempt); // exponential backoff

      if (kDebugMode) {
        debugPrint('[Dio Retry] Attempt $nextAttempt/$maxRetries after ${delay.inMilliseconds}ms');
      }

      await Future<void>.delayed(delay);

      // Clone request with incremented retry counter
      final options = err.requestOptions;
      options.extra['_retryAttempt'] = nextAttempt;

      try {
        final response = await dio.fetch(options);
        return handler.resolve(response);
      } on DioException catch (retryError) {
        return handler.next(retryError);
      }
    }

    return handler.next(err);
  }

  bool _isRetryableError(DioException err) {
    // Retry on timeouts
    if (err.type == DioExceptionType.connectionTimeout ||
        err.type == DioExceptionType.receiveTimeout ||
        err.type == DioExceptionType.sendTimeout) {
      return true;
    }

    // Retry on 5xx server errors
    final statusCode = err.response?.statusCode;
    if (statusCode != null && statusCode >= 500) {
      return true;
    }

    return false;
  }
}

String _defaultBackendBaseUrl() {
  if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
    return 'https://le-backend-1a4f906c.sughara.my.id/';
  }

  return 'https://le-backend-1a4f906c.sughara.my.id';
}

String _buildBackendBaseUrl(String backendBaseUrl) {
  final normalizedBaseUrl = backendBaseUrl.replaceFirst(RegExp(r'/+$'), '');
  const apiPrefix = '/api/v1';

  if (normalizedBaseUrl.endsWith(apiPrefix)) {
    return normalizedBaseUrl.substring(
      0,
      normalizedBaseUrl.length - apiPrefix.length,
    );
  }

  return normalizedBaseUrl;
}
