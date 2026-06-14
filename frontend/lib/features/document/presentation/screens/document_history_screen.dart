import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:legaleasier/core/theme/app_theme.dart';
import 'package:legaleasier/features/document/domain/document.dart';
import 'package:legaleasier/features/document/presentation/providers/document_provider.dart';

class DocumentHistoryScreen extends ConsumerStatefulWidget {
  const DocumentHistoryScreen({super.key});

  @override
  ConsumerState<DocumentHistoryScreen> createState() => _DocumentHistoryScreenState();
}

class _DocumentHistoryScreenState extends ConsumerState<DocumentHistoryScreen> {
  final TextEditingController _searchController = TextEditingController();
  String? _selectedRisk;
  bool _onlyAnalyzed = false;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _clearSearch() {
    _searchController.clear();
    setState(() {});
  }

  List<Document> _applyFilters(List<Document> docs) {
    return docs.where((d) {
      if (_selectedRisk != null && _selectedRisk!.isNotEmpty) {
        if ((d.riskLevel ?? '') != _selectedRisk) return false;
      }
      if (_onlyAnalyzed && !d.hasAnalysis) return false;
      return true;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final query = _searchController.text.trim();
    final searchAsync = query.isNotEmpty ? ref.watch(searchDocumentsProvider(query)) : null;
    final documentsAsync = query.isEmpty ? ref.watch(documentsProvider((page: 1, limit: 100))) : null;

    Widget buildList(List<Document> documents) {
      final filtered = _applyFilters(documents);

      if (filtered.isEmpty) {
        return Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Text(
              'Tidak ada dokumen yang cocok.',
              style: AppTextStyles.bodyLarge.copyWith(color: AppColors.text2),
              textAlign: TextAlign.center,
            ),
          ),
        );
      }

      return ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: filtered.length,
        itemBuilder: (context, index) {
          final document = filtered[index];
          return _buildDocumentItem(context, document);
        },
      );
    }

    Widget _buildDocumentItem(BuildContext context, Document document) {
      final hasAnalysis = document.hasAnalysis;
      final encodedTitle = Uri.encodeComponent(document.filename);

      return Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Material(
          color: AppColors.white,
          borderRadius: BorderRadius.circular(12),
          child: InkWell(
            onTap: () {
              context.push('/documents/${document.id}/analysis?title=$encodedTitle');
            },
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: Colors.black.withValues(alpha: 0.07),
                  width: 0.5,
                ),
              ),
              child: Row(
                children: [
                  // Document icon
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: AppColors.soft,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(
                      Icons.description_outlined,
                      size: 20,
                      color: AppColors.brand,
                    ),
                  ),
                  const SizedBox(width: 12),

                  // Document info
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          document.filename,
                          style: AppTextStyles.bodyMedium.copyWith(
                            fontWeight: FontWeight.w500,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            if (hasAnalysis && document.riskLevel != null) ...[
                              _buildRiskBadge(document.riskLevel!),
                              const SizedBox(width: 8),
                            ],
                            if (!hasAnalysis) ...[
                              _buildAnalyzingBadge(),
                              const SizedBox(width: 8),
                            ],
                            Text(
                              _formatDate(document.uploadedAt),
                              style: AppTextStyles.meta,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),

                  const Icon(
                    Icons.chevron_right,
                    size: 20,
                    color: AppColors.text3,
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    Widget _buildRiskBadge(String riskLevel) {
      final (Color bg, Color text) = switch (riskLevel) {
        'Tinggi' => (AppColors.dangerBg, AppColors.danger),
        'Sedang' => (AppColors.warnBg, AppColors.warn),
        _ => (AppColors.okBg, AppColors.ok),
      };

      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          riskLevel,
          style: AppTextStyles.badgeText.copyWith(color: text),
        ),
      );
    }

    Widget _buildAnalyzingBadge() {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(
          color: AppColors.soft,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          'Belum dianalisis',
          style: AppTextStyles.badgeText.copyWith(color: AppColors.text2),
        ),
      );
    }

    String _formatDate(DateTime date) {
      final now = DateTime.now();
      final diff = now.difference(date);
      if (diff.inDays == 0) return 'Hari ini';
      if (diff.inDays == 1) return 'Kemarin';
      if (diff.inDays < 7) return '${diff.inDays} hari lalu';
      return '${date.day}/${date.month}/${date.year}';
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Riwayat Dokumen'),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: TextField(
              controller: _searchController,
              onChanged: (_) => setState(() {}),
              decoration: InputDecoration(
                hintText: 'Cari dokumen...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: _clearSearch,
                      )
                    : null,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                isDense: true,
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            child: Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                ChoiceChip(
                  label: const Text('Semua'),
                  selected: _selectedRisk == null,
                  onSelected: (_) => setState(() => _selectedRisk = null),
                ),
                ...['Tinggi', 'Sedang', 'Rendah', 'Aman'].map((level) {
                  return ChoiceChip(
                    label: Text(level),
                    selected: _selectedRisk == level,
                    onSelected: (s) => setState(() => _selectedRisk = s ? level : null),
                  );
                }),
                FilterChip(
                  label: const Text('Hanya Ter-analisis'),
                  selected: _onlyAnalyzed,
                  onSelected: (v) => setState(() => _onlyAnalyzed = v),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: query.isNotEmpty
                ? searchAsync!.when(
                    loading: () => const Center(child: CircularProgressIndicator()),
                    error: (err, st) => Center(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 24),
                        child: Text(
                          'Gagal mencari dokumen. Silakan coba lagi.',
                          style: AppTextStyles.bodyLarge.copyWith(color: AppColors.danger),
                          textAlign: TextAlign.center,
                        ),
                      ),
                    ),
                    data: (docs) => buildList(docs),
                  )
                : documentsAsync!.when(
                    loading: () => const Center(child: CircularProgressIndicator()),
                    error: (err, st) => Center(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 24),
                        child: Text(
                          'Gagal memuat riwayat dokumen. Silakan coba lagi.',
                          style: AppTextStyles.bodyLarge.copyWith(color: AppColors.danger),
                          textAlign: TextAlign.center,
                        ),
                      ),
                    ),
                    data: (docs) => buildList(docs),
                  ),
          ),
        ],
      ),
    );
  }
}
