import 'package:legaleasier/features/analysis/data/analysis_service.dart';
import 'package:legaleasier/features/analysis/domain/analysis_repository.dart';
import 'package:legaleasier/features/analysis/domain/analysis_result.dart';

/// Concrete implementation of [AnalysisRepository].
///
/// Delegates HTTP calls to [AnalysisService].
class AnalysisRepositoryImpl implements AnalysisRepository {
  final AnalysisService analysisService;

  AnalysisRepositoryImpl({required this.analysisService});

  @override
  Future<AnalysisResult?> getAnalysis(String documentId) async {
    return analysisService.fetchAnalysis(documentId);
  }
}
