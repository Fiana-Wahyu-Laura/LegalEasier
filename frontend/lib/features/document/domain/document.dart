/// Document entity untuk representasi dokumen di frontend
class Document {
  final String id;
  final String filename;
  final DateTime uploadedAt;
  final int? riskScore;  // 0-100, null jika belum dianalisis
  final String? riskLevel;  // "Tinggi", "Sedang", "Rendah", "Aman"
  final bool hasAnalysis;
  final String? fileType;  // pdf, jpg, png, docx

  Document({
    required this.id,
    required this.filename,
    required this.uploadedAt,
    this.riskScore,
    this.riskLevel,
    this.hasAnalysis = false,
    this.fileType,
  });

  /// Factory constructor untuk mapping dari JSON response backend
  factory Document.fromJson(Map<String, dynamic> json) {
    return Document(
      id: json['id'] as String,
      filename: json['filename'] as String,
      uploadedAt: DateTime.parse((json['created_at'] ?? json['uploaded_at']) as String),
      riskScore: json['risk_score'] as int?,
      riskLevel: json['risk_level'] as String? ?? _calculateRiskLevel(json['risk_score'] as int?),
      hasAnalysis: json['has_analysis'] as bool? ?? (json['status'] == 'done'),
      fileType: json['file_type'] as String?,
    );
  }

  static String? _calculateRiskLevel(int? score) {
    if (score == null) return null;
    if (score <= 20) return 'Aman';
    if (score <= 40) return 'Rendah';
    if (score <= 70) return 'Sedang';
    return 'Tinggi';
  }

  /// Convert ke JSON untuk API requests
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'filename': filename,
      'uploaded_at': uploadedAt.toIso8601String(),
      'risk_score': riskScore,
      'risk_level': riskLevel,
      'has_analysis': hasAnalysis,
      'file_type': fileType,
    };
  }

  /// Copy with method untuk immutability
  Document copyWith({
    String? id,
    String? filename,
    DateTime? uploadedAt,
    int? riskScore,
    String? riskLevel,
    bool? hasAnalysis,
    String? fileType,
  }) {
    return Document(
      id: id ?? this.id,
      filename: filename ?? this.filename,
      uploadedAt: uploadedAt ?? this.uploadedAt,
      riskScore: riskScore ?? this.riskScore,
      riskLevel: riskLevel ?? this.riskLevel,
      hasAnalysis: hasAnalysis ?? this.hasAnalysis,
      fileType: fileType ?? this.fileType,
    );
  }

  @override
  String toString() =>
      'Document(id: $id, filename: $filename, riskScore: $riskScore, riskLevel: $riskLevel)';
}
