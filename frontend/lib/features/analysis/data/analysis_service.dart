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
      throw Exception('Failed to fetch analysis: ${response.statusCode}');
    } on DioException catch (e) {
      // 202 = still processing, 404 = not found
      final code = e.response?.statusCode;
      if (code == 202 || code == 404) {
        return null;
      }
      final message = e.response?.data?['message'] as String?;
      throw Exception(
        message ?? 'Gagal memuat analisis dokumen (Code: $code)',
      );
    }
  }
}
