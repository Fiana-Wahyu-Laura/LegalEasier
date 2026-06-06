import 'package:legaleasier/features/analysis/domain/analysis_result.dart';

/// Repository interface for analysis feature.
///
/// Follows Clean Architecture: the analysis feature owns its own
/// data layer instead of piggybacking on DocumentRepository.
abstract class AnalysisRepository {
  /// Fetch analysis result for a document by its ID.
  Future<AnalysisResult?> getAnalysis(String documentId);
}
