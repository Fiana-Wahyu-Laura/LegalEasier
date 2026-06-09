import 'package:dio/dio.dart';
import 'package:legaleasier/core/constants/api_constants.dart';
import 'package:legaleasier/features/analysis/domain/analysis_result.dart';

/// HTTP service for analysis API calls.
///
/// Handles the raw HTTP communication with the backend
/// analysis endpoint. Used by AnalysisRepositoryImpl.
class AnalysisService {
  static const _apiPrefix = ApiConstants.apiPrefix;

  final Dio dio;

  AnalysisService({required this.dio});

  /// GET /api/v1/documents/:id/analysis
  ///
  /// Returns null when the document is still being processed so the UI
  /// keeps polling. Only throws on truly unrecoverable errors.
  Future<AnalysisResult?> fetchAnalysis(String documentId) async {
    try {
      final response = await dio.get(
        '$_apiPrefix/documents/$documentId/analysis',
      );

      if (response.statusCode == 200) {
        final data = response.data;
        if (data['success'] == true && data['data'] != null) {
          return AnalysisResult.fromJson(data['data'] as Map<String, dynamic>);
        }
        return null;
      }
      // Unexpected success code — treat as still processing
      return null;
    } on DioException catch (e) {
      final code = e.response?.statusCode;
      // 202 = still processing, 404 = not found → keep polling
      if (code == 202 || code == 404) {
        return null;
      }
      // 400 (failed processing) or 5xx (server error) — keep polling too;
      // the backend may recover when NLP finishes or retries succeed.
      // Only throw on 401/403 (auth), or total network failure (no response).
      if (code == 401 || code == 403) {
        throw Exception('Akses ditolak. Silakan login kembali.');
      }
      if (e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.receiveTimeout ||
          e.type == DioExceptionType.connectionError) {
        // Transient network error — return null so polling continues
        return null;
      }
      // All other errors (400, 500, etc.) — also keep polling
      return null;
    }
  }
}
