import 'dart:io';
import 'package:legaleasier/features/analysis/domain/analysis_result.dart';
import 'package:legaleasier/features/document/domain/document.dart';
import 'package:legaleasier/features/document/domain/document_repository.dart';
import 'package:legaleasier/features/document/data/document_service.dart';

/// Implementasi DocumentRepository
/// Menghubungkan frontend ke backend API melalui DocumentService
class DocumentRepositoryImpl implements DocumentRepository {
  final DocumentService documentService;

  DocumentRepositoryImpl({required this.documentService});

  @override
  Future<List<Document>> getRecentDocuments({int limit = 10}) async {
    return documentService.fetchRecentDocuments(limit: limit);
  }

  @override
  Future<Document?> getDocumentById(String id) async {
    return documentService.fetchDocumentById(id);
  }

  @override
  Future<Document> uploadDocument(File file) async {
    return documentService.uploadDocument(file);
  }

  @override
  Future<void> deleteDocument(String id) async {
    return documentService.deleteDocument(id);
  }

  @override
  Future<List<Document>> getDocuments({int page = 1, int limit = 20}) async {
    return documentService.fetchDocuments(page: page, limit: limit);
  }

  @override
  Future<List<Document>> searchDocuments(String query) async {
    return documentService.searchDocuments(query);
  }

  @override
  Future<int> getDocumentCount() async {
    return documentService.getDocumentCount();
  }

  @override
  Future<AnalysisResult?> getDocumentAnalysis(String id) async {
    return documentService.fetchDocumentAnalysis(id);
  }
}
