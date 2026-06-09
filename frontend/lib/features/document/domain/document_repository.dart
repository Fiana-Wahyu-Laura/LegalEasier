import 'dart:io';
import 'package:legaleasier/features/analysis/domain/analysis_result.dart';
import 'document.dart';

/// Repository interface untuk Document operations
abstract class DocumentRepository {
  /// Fetch recent documents
  /// [limit] - jumlah dokumen yang diambil
  Future<List<Document>> getRecentDocuments({int limit = 10});

  /// Get single document by ID
  Future<Document?> getDocumentById(String id);

  /// Upload document file
  /// [file] - file yang akan diupload
  Future<Document> uploadDocument(File file);

  /// Delete document
  Future<void> deleteDocument(String id);

  /// Get all documents (dengan pagination)
  /// [page] - page number (1-indexed)
  /// [limit] - jumlah item per page
  Future<List<Document>> getDocuments({int page = 1, int limit = 20});

  /// Search documents by filename
  Future<List<Document>> searchDocuments(String query);

  /// Get total document count
  Future<int> getDocumentCount();

  /// Fetch analysis result for a document
  Future<AnalysisResult?> getDocumentAnalysis(String id);

  /// Fetch server-authoritative guest quota information.
  /// Returns a map with keys: is_guest, remaining, total.
  Future<Map<String, dynamic>> getGuestQuota();
}
