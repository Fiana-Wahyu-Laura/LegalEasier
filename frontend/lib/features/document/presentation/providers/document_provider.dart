import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:legaleasier/core/http/dio_provider.dart';
import 'package:legaleasier/features/document/data/document_service.dart';
import 'package:legaleasier/features/document/data/document_repository_impl.dart';
import 'package:legaleasier/features/document/domain/document.dart';
import 'package:legaleasier/features/document/domain/document_repository.dart';

/// Document Repository provider
final documentRepositoryProvider = Provider<DocumentRepository>((ref) {
  final dio = ref.watch(dioProvider);
  final documentService = DocumentService(dio: dio);
  return DocumentRepositoryImpl(documentService: documentService);
});

/// Recent documents provider - fetch recent dokumen
final recentDocumentsProvider =
    FutureProvider.autoDispose<List<Document>>((ref) async {
  final repository = ref.watch(documentRepositoryProvider);
  return repository.getRecentDocuments(limit: 10);
});

/// All documents provider dengan pagination
final documentsProvider = FutureProvider.family
    .autoDispose<List<Document>, ({int page, int limit})>((ref, params) async {
  final repository = ref.watch(documentRepositoryProvider);
  return repository.getDocuments(page: params.page, limit: params.limit);
});

/// Single document provider by ID
final documentByIdProvider =
    FutureProvider.family.autoDispose<Document?, String>((ref, id) async {
  final repository = ref.watch(documentRepositoryProvider);
  return repository.getDocumentById(id);
});

/// Document count provider
final documentCountProvider =
    FutureProvider.autoDispose<int>((ref) async {
  final repository = ref.watch(documentRepositoryProvider);
  return repository.getDocumentCount();
});

/// Search documents provider
final searchDocumentsProvider =
    FutureProvider.family.autoDispose<List<Document>, String>((ref, query) async {
  final repository = ref.watch(documentRepositoryProvider);
  if (query.isEmpty) {
    return [];
  }
  return repository.searchDocuments(query);
});

/// Upload document notifier — uses AsyncNotifier per CLAUDE.md §7
class DocumentUploadNotifier extends AutoDisposeAsyncNotifier<Document?> {
  @override
  Future<Document?> build() async => null;

  Future<Document> uploadDocument(File file) async {
    state = const AsyncValue.loading();
    try {
      final repository = ref.read(documentRepositoryProvider);
      final result = await repository.uploadDocument(file);
      state = AsyncValue.data(result);
      return result;
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
      rethrow;
    }
  }

  void reset() {
    state = const AsyncValue.data(null);
  }
}

/// Upload document provider
final documentUploadProvider =
    AsyncNotifierProvider.autoDispose<DocumentUploadNotifier, Document?>(
  DocumentUploadNotifier.new,
);
