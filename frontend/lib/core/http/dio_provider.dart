import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

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
      sendTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ),
  );

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        final user = FirebaseAuth.instance.currentUser;
        if (user != null) {
          final idToken = await user.getIdToken();
          options.headers['Authorization'] = 'Bearer $idToken';
        }
        return handler.next(options);
      },
    ),
  );

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

  // TODO: Add interceptor untuk JWT token
  // dio.interceptors.add(
  //   InterceptorsWrapper(
  //     onRequest: (options, handler) async {
  //       // Add JWT token dari SharedPreferences
  //       return handler.next(options);
  //     },
  //     onError: (error, handler) {
  //       // Handle 401 - refresh token atau logout
  //       return handler.next(error);
  //     },
  //   ),
  // );

  return dio;
});

String _defaultBackendBaseUrl() {
  if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
    return 'https://le-backend.sughara.my.id';
  }

  return 'https://le-backend.sughara.my.id';
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
