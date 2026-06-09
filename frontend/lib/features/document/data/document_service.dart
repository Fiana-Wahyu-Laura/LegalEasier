import 'dart:io';
import 'package:dio/dio.dart';
import 'package:legaleasier/core/constants/api_constants.dart';
import 'package:legaleasier/features/analysis/domain/analysis_result.dart';
import 'package:legaleasier/features/document/domain/document.dart';

/// Service untuk HTTP calls ke backend document endpoints
class DocumentService {
  static const _apiPrefix = ApiConstants.apiPrefix;

  final Dio dio;

  DocumentService({required this.dio});

  /// GET /api/v1/documents?limit=10
  /// Fetch recent documents
  Future<List<Document>> fetchRecentDocuments({int limit = 10}) async {
    try {
      final response = await dio.get(
        '$_apiPrefix/documents',
        queryParameters: {'limit': limit},
      );

      if (response.statusCode == 200) {
        final data = response.data;
        if (data['success'] == true && data['data'] != null) {
          final payload = data['data'];
          // Handle paginated response { items: [...] } or flat array
          final List<dynamic> documentsList = payload is Map
              ? (payload['items'] as List<dynamic>? ?? [])
              : payload as List<dynamic>;
          return documentsList
              .map((doc) => Document.fromJson(doc as Map<String, dynamic>))
              .toList();
        }
        return [];
      }
      throw Exception(
          'Failed to fetch recent documents: ${response.statusCode}');
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// GET /api/v1/documents?page=1&limit=20
  /// Fetch documents dengan pagination
  Future<List<Document>> fetchDocuments({int page = 1, int limit = 20}) async {
    try {
      final response = await dio.get(
        '$_apiPrefix/documents',
        queryParameters: {'page': page, 'limit': limit},
      );

      if (response.statusCode == 200) {
        final data = response.data;
        if (data['success'] == true && data['data'] != null) {
          final payload = data['data'];
          // Handle paginated response { items: [...] } or flat array
          final List<dynamic> documentsList = payload is Map
              ? (payload['items'] as List<dynamic>? ?? [])
              : payload as List<dynamic>;
          return documentsList
              .map((doc) => Document.fromJson(doc as Map<String, dynamic>))
              .toList();
        }
        return [];
      }
      throw Exception('Failed to fetch documents: ${response.statusCode}');
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// GET /api/v1/documents/:id
  /// Fetch single document by ID
  Future<Document?> fetchDocumentById(String id) async {
    try {
      final response = await dio.get('$_apiPrefix/documents/$id');

      if (response.statusCode == 200) {
        final data = response.data;
        if (data['success'] == true && data['data'] != null) {
          return Document.fromJson(data['data'] as Map<String, dynamic>);
        }
        return null;
      }
      throw Exception('Failed to fetch document: ${response.statusCode}');
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        return null;
      }
      throw _handleDioError(e);
    }
  }

  /// POST /api/v1/documents/upload
  /// Upload document file (multipart)
  Future<Document> uploadDocument(File file) async {
    try {
      final fileName = file.path.split('/').last;
      final formData = FormData.fromMap({
        'file': await MultipartFile.fromFile(
          file.path,
          filename: fileName,
        ),
      });

      final response = await dio.post(
        '$_apiPrefix/documents/upload',
        data: formData,
        options: Options(
          contentType: Headers.multipartFormDataContentType,
          sendTimeout: const Duration(minutes: 2),
          receiveTimeout: const Duration(minutes: 2),
        ),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = response.data;
        if (data['success'] == true && data['data'] != null) {
          return Document.fromJson(data['data'] as Map<String, dynamic>);
        }
      }
      throw Exception('Failed to upload document: ${response.statusCode}');
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// DELETE /api/v1/documents/:id
  /// Delete document
  Future<void> deleteDocument(String id) async {
    try {
      final response = await dio.delete('$_apiPrefix/documents/$id');

      if (response.statusCode != 200 && response.statusCode != 204) {
        throw Exception('Failed to delete document: ${response.statusCode}');
      }
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// GET /api/v1/documents/:id/analysis
  /// Fetch document analysis result
  Future<AnalysisResult?> fetchDocumentAnalysis(String id) async {
    try {
      final response = await dio.get('$_apiPrefix/documents/$id/analysis');

      if (response.statusCode == 200) {
        final data = response.data;
        if (data['success'] == true && data['data'] != null) {
          return AnalysisResult.fromJson(data['data'] as Map<String, dynamic>);
        }
        return null;
      }
      throw Exception('Failed to fetch analysis: ${response.statusCode}');
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        return null;
      }
      throw _handleDioError(e);
    }
  }

  /// GET /api/v1/documents/count
  /// Get total document count
  Future<int> getDocumentCount() async {
    try {
      final response = await dio.get('$_apiPrefix/documents/count');

      if (response.statusCode == 200) {
        final data = response.data;
        if (data['success'] == true && data['data'] != null) {
          return data['data']['count'] as int;
        }
        return 0;
      }
      throw Exception('Failed to get document count: ${response.statusCode}');
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// GET /api/v1/documents/search?q=query
  /// Search documents
  Future<List<Document>> searchDocuments(String query) async {
    try {
      final response = await dio.get(
        '$_apiPrefix/documents/search',
        queryParameters: {'q': query},
      );

      if (response.statusCode == 200) {
        final data = response.data;
        if (data['success'] == true && data['data'] != null) {
          final List<dynamic> documentsList = data['data'] as List<dynamic>;
          return documentsList
              .map((doc) => Document.fromJson(doc as Map<String, dynamic>))
              .toList();
        }
        return [];
      }
      throw Exception('Failed to search documents: ${response.statusCode}');
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// GET /api/v1/guest/quota
  /// Fetch server-authoritative guest quota (single source of truth).
  /// Returns a map with keys: is_guest, remaining, total.
  Future<Map<String, dynamic>> fetchGuestQuota() async {
    try {
      final response = await dio.get('$_apiPrefix/guest/quota');

      if (response.statusCode == 200) {
        final data = response.data;
        if (data['success'] == true && data['data'] != null) {
          return data['data'] as Map<String, dynamic>;
        }
      }
      throw Exception('Failed to fetch guest quota: ${response.statusCode}');
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Handle Dio errors dengan pesan yang user-friendly
  Exception _handleDioError(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
        return Exception(
          'Tidak bisa terhubung ke server. Pastikan backend berjalan dan URL backend benar.',
        );
      case DioExceptionType.sendTimeout:
        return Exception(
          'Upload terlalu lama. Coba gunakan file yang lebih kecil atau koneksi yang lebih stabil.',
        );
      case DioExceptionType.receiveTimeout:
        return Exception(
          'Server terlalu lama merespons. Cek log backend, database, dan NLP service.',
        );
      case DioExceptionType.badResponse:
        final statusCode = error.response?.statusCode;
        final responseData = error.response?.data;
        final detail = responseData is Map ? responseData['detail'] : null;
        final apiMessage = responseData is Map ? responseData['message'] : null;
        final message = detail is String
            ? detail
            : apiMessage is String
                ? apiMessage
                : null;
        return Exception(
            'Error: ${message ?? 'Request gagal (Code: $statusCode)'}');
      case DioExceptionType.cancel:
        return Exception('Request dibatalkan');
      case DioExceptionType.unknown:
        return Exception('Kesalahan jaringan. Periksa koneksi Anda.');
      default:
        return Exception('Terjadi kesalahan: ${error.message}');
    }
  }
}
