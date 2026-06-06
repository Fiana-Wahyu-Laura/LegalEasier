import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:legaleasier/core/http/dio_provider.dart';
import 'package:legaleasier/features/analysis/data/analysis_repository_impl.dart';
import 'package:legaleasier/features/analysis/data/analysis_service.dart';
import 'package:legaleasier/features/analysis/domain/analysis_repository.dart';
import 'package:legaleasier/features/analysis/domain/analysis_result.dart';

/// Analysis repository provider — analysis feature owns its data layer.
final analysisRepositoryProvider = Provider<AnalysisRepository>((ref) {
  final dio = ref.watch(dioProvider);
  final service = AnalysisService(dio: dio);
  return AnalysisRepositoryImpl(analysisService: service);
});

/// Provider untuk mengambil hasil analisis dokumen berdasarkan ID dokumen.
final documentAnalysisProvider = FutureProvider.autoDispose.family<AnalysisResult?, String>(
  (ref, documentId) async {
    final repository = ref.watch(analysisRepositoryProvider);
    return repository.getAnalysis(documentId);
  },
);
