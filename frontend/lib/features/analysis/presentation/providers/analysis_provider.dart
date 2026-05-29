import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:legaleasier/features/analysis/domain/analysis_result.dart';
import 'package:legaleasier/features/document/presentation/providers/document_provider.dart';

/// Provider untuk mengambil hasil analisis dokumen berdasarkan ID dokumen.
final documentAnalysisProvider = FutureProvider.autoDispose.family<AnalysisResult?, String>(
  (ref, documentId) async {
    final repository = ref.watch(documentRepositoryProvider);
    return repository.getDocumentAnalysis(documentId);
  },
);
