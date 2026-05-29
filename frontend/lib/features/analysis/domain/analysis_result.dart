class RiskClause {
  final String clauseText;
  final String plainLanguage;
  final String riskLevel;
  final double confidence;

  RiskClause({
    required this.clauseText,
    required this.plainLanguage,
    required this.riskLevel,
    required this.confidence,
  });

  factory RiskClause.fromJson(Map<String, dynamic> json) {
    return RiskClause(
      clauseText: json['clause_text'] as String,
      plainLanguage: json['plain_language'] as String,
      riskLevel: json['risk_level'] as String,
      confidence: (json['confidence'] as num).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'clause_text': clauseText,
      'plain_language': plainLanguage,
      'risk_level': riskLevel,
      'confidence': confidence,
    };
  }
}

class AnalysisResult {
  final String documentId;
  final String? summary;
  final int? riskScore;
  final List<RiskClause> riskClauses;
  final String disclaimer;

  AnalysisResult({
    required this.documentId,
    required this.summary,
    required this.riskScore,
    required this.riskClauses,
    required this.disclaimer,
  });

  factory AnalysisResult.fromJson(Map<String, dynamic> json) {
    final clauses = (json['risk_clauses'] as List<dynamic>?)
            ?.map((item) => RiskClause.fromJson(item as Map<String, dynamic>))
            .toList() ??
        [];

    return AnalysisResult(
      documentId: json['document_id'] as String,
      summary: json['summary'] as String?,
      riskScore: json['risk_score'] as int?,
      riskClauses: clauses,
      disclaimer: json['disclaimer'] as String? ??
          'Hasil ini bersifat informatif dan bukan pengganti konsultasi hukum profesional.',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'document_id': documentId,
      'summary': summary,
      'risk_score': riskScore,
      'risk_clauses': riskClauses.map((clause) => clause.toJson()).toList(),
      'disclaimer': disclaimer,
    };
  }
}
