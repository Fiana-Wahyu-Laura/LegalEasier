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

      return ListView.separated(
        padding: const EdgeInsets.symmetric(vertical: 12),
        itemCount: filtered.length,
        separatorBuilder: (context, index) => const Divider(height: 1),
        itemBuilder: (context, index) {
          final document = filtered[index];
          final subtitle = document.hasAnalysis
              ? 'Analisis tersedia • ${document.riskLevel ?? 'Aman'}'
              : 'Analisis belum selesai';
          final encodedTitle = Uri.encodeComponent(document.filename);

          return ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            tileColor: AppColors.white,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
            ),
            title: Text(
              document.filename,
              style: AppTextStyles.bodyLarge.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            subtitle: Text(
              subtitle,
              style: AppTextStyles.meta.copyWith(
                color: document.hasAnalysis ? AppColors.text1 : AppColors.text2,
              ),
            ),
            trailing: const Icon(Icons.chevron_right, color: AppColors.text3),
            onTap: () {
              context.push('/documents/${document.id}/analysis?title=$encodedTitle');
            },
          );
        },
      );
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
