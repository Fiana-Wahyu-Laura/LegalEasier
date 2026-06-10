import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:legaleasier/core/theme/app_theme.dart';
import 'package:legaleasier/features/auth/presentation/providers/auth_provider.dart';
import 'package:legaleasier/features/document/presentation/providers/document_provider.dart';
import 'package:legaleasier/features/auth/presentation/trial_provider.dart';
import 'package:legaleasier/features/document/presentation/providers/guest_quota_provider.dart';

/// Bottom sheet untuk upload atau scan dokumen
/// Design: Radius 20px top, scan preview, 2 opsi (Kamera/Upload), 2 tombol (Batal/Ambil Foto)
class UploadScanBottomSheet extends ConsumerStatefulWidget {
  final UploadMethod initialMethod;

  const UploadScanBottomSheet({
    super.key,
    this.initialMethod = UploadMethod.scan,
  });

  @override
  ConsumerState<UploadScanBottomSheet> createState() =>
      _UploadScanBottomSheetState();
}

class _UploadScanBottomSheetState extends ConsumerState<UploadScanBottomSheet> {
  late UploadMethod _selectedMethod;
  static const int _maxFileSizeBytes = 25 * 1024 * 1024;

  @override
  void initState() {
    super.initState();
    _selectedMethod = widget.initialMethod;
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authNotifierProvider);
    final authUser = authState.value;
    final remainingQuota = ref.watch(guestQuotaProvider).value ?? 5;
    // Only treat as guest when auth is resolved — avoid flicker during loading (#10)
    final isGuest = authState.isLoading ? false : (authUser?.isGuest ?? false);
    final isLocked = isGuest && remainingQuota <= 0;
    final uploadState = ref.watch(documentUploadProvider);
    final isUploading = uploadState.isLoading;

    return Container(
      decoration: const BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(20),
          topRight: Radius.circular(20),
        ),
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Handle bar
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: AppColors.text3,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),

            // Header
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Upload Dokumen',
                    style: AppTextStyles.screenTitle.copyWith(
                      fontFamily: 'Fraunces',
                    ),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Pilih metode untuk mengunggah dokumen Anda',
                    style: AppTextStyles.bodyMedium,
                  ),
                ],
              ),
            ),

            // Scan preview (active state)
            if (_selectedMethod == UploadMethod.scan)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: _buildScanPreview(),
              )
            else
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Container(
                  height: 180,
                  decoration: BoxDecoration(
                    color: AppColors.soft,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: Colors.black.withValues(alpha: 0.1),
                      width: 0.5,
                    ),
                  ),
                  child: const Center(
                    child: Icon(
                      Icons.folder_open_outlined,
                      size: 48,
                      color: AppColors.text3,
                    ),
                  ),
                ),
              ),
            const SizedBox(height: 24),

            // Upload options
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Pilih Metode',
                    style: AppTextStyles.label.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: _buildUploadOption(
                          isSelected: _selectedMethod == UploadMethod.scan,
                          icon: Icons.camera_alt_outlined,
                          title: 'Scan dengan\nKamera',
                          onTap: () {
                            setState(
                              () => _selectedMethod = UploadMethod.scan,
                            );
                          },
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _buildUploadOption(
                          isSelected: _selectedMethod == UploadMethod.file,
                          icon: Icons.cloud_upload_outlined,
                          title: 'Upload\nFile',
                          onTap: () {
                            setState(
                              () => _selectedMethod = UploadMethod.file,
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Action buttons
            if (isLocked)
              Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: Text(
                  'Kuota gratis habis. Silakan masuk untuk melanjutkan analisis.',
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.danger,
                    height: 1.4,
                  ),
                ),
              ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
              child: Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => Navigator.of(context).pop(),
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(
                          color: AppColors.text3,
                          width: 0.5,
                        ),
                        foregroundColor: AppColors.text2,
                      ),
                      child: Text(
                        'Batal',
                        style: AppTextStyles.buttonText.copyWith(
                          color: AppColors.text2,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton(
                      onPressed:
                          isUploading || isLocked ? null : _handlePrimaryAction,
                      child: isUploading
                          ? const SizedBox(
                              height: 18,
                              width: 18,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  AppColors.white,
                                ),
                              ),
                            )
                          : Text(
                              isLocked
                                  ? 'Kuota Habis'
                                  : _selectedMethod == UploadMethod.scan
                                      ? 'Ambil Foto'
                                      : 'Pilih File',
                              style: AppTextStyles.buttonText,
                            ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _handlePrimaryAction() async {
    if (_selectedMethod == UploadMethod.scan) {
      await _takePhotoAndUpload();
      return;
    }

    await _pickFileAndUpload();
  }

  Future<void> _takePhotoAndUpload() async {
    final messenger = ScaffoldMessenger.of(context);

    try {
      final picker = ImagePicker();
      final photo = await picker.pickImage(
        source: ImageSource.camera,
        imageQuality: 85,
      );

      if (photo == null) {
        return;
      }

      await _uploadFile(File(photo.path));
    } on Exception {
      if (!mounted) return;
      messenger.showSnackBar(
        const SnackBar(content: Text('Gagal membuka kamera. Coba lagi.')),
      );
    }
  }

  Future<void> _pickFileAndUpload() async {
    final messenger = ScaffoldMessenger.of(context);

    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: const ['pdf', 'png', 'jpg', 'jpeg', 'tiff'],
        allowMultiple: false,
      );

      final path = result?.files.single.path;
      if (path == null) {
        return;
      }

      await _uploadFile(File(path));
    } on Exception {
      if (!mounted) return;
      messenger.showSnackBar(
        const SnackBar(content: Text('Gagal memilih file. Coba lagi.')),
      );
    }
  }

  Future<void> _uploadFile(File file) async {
    final messenger = ScaffoldMessenger.of(context);

    try {
      final fileSize = await file.length();
      if (fileSize > _maxFileSizeBytes) {
        if (!mounted) return;
        messenger.showSnackBar(
          const SnackBar(
            content: Text('Ukuran file maksimal 25 MB.'),
          ),
        );
        return;
      }

      final uploadedDocument =
          await ref.read(documentUploadProvider.notifier).uploadDocument(file);

      // Sync quota from backend response (single source of truth).
      // Backend includes remaining_quota in the upload response for guests.
      if (uploadedDocument.remainingQuota != null) {
        ref
            .read(trialControllerProvider)
            .syncFromUploadResponse(uploadedDocument.remainingQuota!);
      } else {
        // Fallback: optimistic local decrement
        try {
          ref.read(trialControllerProvider).consumeIfGuest();
        } catch (_) {
          // Non-blocking.
        }
      }

      if (!mounted) return;
      Navigator.of(context).pop(uploadedDocument);
    } on Exception catch (error) {
      if (!mounted) return;
      messenger.showSnackBar(
        SnackBar(content: Text(_formatUploadError(error))),
      );
    }
  }

  String _formatUploadError(Exception error) {
    final message = error.toString().replaceFirst('Exception: ', '').trim();
    if (message.isEmpty) {
      return 'Upload gagal. Silakan coba lagi.';
    }
    return message;
  }

  /// Scan preview dengan corner brackets dan scan line
  Widget _buildScanPreview() {
    return Container(
      height: 180,
      decoration: BoxDecoration(
        color: AppColors.brand,
        borderRadius: BorderRadius.circular(14),
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: [
          // Placeholder background
          Container(
            color: AppColors.brand,
          ),

          // Corner brackets
          Positioned(
            top: 12,
            left: 12,
            child: _buildCornerBracket(topLeft: true),
          ),
          Positioned(
            top: 12,
            right: 12,
            child: _buildCornerBracket(topRight: true),
          ),
          Positioned(
            bottom: 12,
            left: 12,
            child: _buildCornerBracket(bottomLeft: true),
          ),
          Positioned(
            bottom: 12,
            right: 12,
            child: _buildCornerBracket(bottomRight: true),
          ),

          // Scan line
          Center(
            child: Container(
              width: 200,
              height: 2,
              decoration: BoxDecoration(
                color: AppColors.accent.withValues(alpha: 0.8),
                borderRadius: BorderRadius.circular(1),
              ),
            ),
          ),

          // Center text placeholder
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(
                  Icons.photo_camera_outlined,
                  size: 48,
                  color: AppColors.accent,
                ),
                const SizedBox(height: 12),
                Text(
                  'Arahkan ke dokumen',
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.accent,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// Overlay corner bracket untuk scan preview
  Widget _buildCornerBracket({
    bool topLeft = false,
    bool topRight = false,
    bool bottomLeft = false,
    bool bottomRight = false,
  }) {
    const size = 24.0;
    const thickness = 2.5;

    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(
        painter: CornerBracketPainter(
          topLeft: topLeft,
          topRight: topRight,
          bottomLeft: bottomLeft,
          bottomRight: bottomRight,
          color: AppColors.accent,
          thickness: thickness,
        ),
      ),
    );
  }

  /// Upload option item (scan atau file)
  Widget _buildUploadOption({
    required bool isSelected,
    required IconData icon,
    required String title,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFFEEF6F4) : AppColors.soft,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? AppColors.brand2 : Colors.transparent,
            width: 1.5,
          ),
        ),
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: isSelected
                    ? AppColors.brand2.withValues(alpha: 0.2)
                    : Colors.transparent,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                icon,
                color: isSelected ? AppColors.brand2 : AppColors.text3,
                size: 24,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              title,
              style: AppTextStyles.label.copyWith(
                color: isSelected ? AppColors.brand2 : AppColors.text2,
                fontSize: 12,
                height: 1.3,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

/// Corner bracket painter untuk scan preview
class CornerBracketPainter extends CustomPainter {
  final bool topLeft;
  final bool topRight;
  final bool bottomLeft;
  final bool bottomRight;
  final Color color;
  final double thickness;

  CornerBracketPainter({
    this.topLeft = false,
    this.topRight = false,
    this.bottomLeft = false,
    this.bottomRight = false,
    required this.color,
    required this.thickness,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = thickness
      ..strokeCap = StrokeCap.round;

    const lineLength = 8.0;

    if (topLeft) {
      // Horizontal top
      canvas.drawLine(
        const Offset(0, 0),
        const Offset(lineLength, 0),
        paint,
      );
      // Vertical left
      canvas.drawLine(
        const Offset(0, 0),
        const Offset(0, lineLength),
        paint,
      );
    }

    if (topRight) {
      // Horizontal top
      canvas.drawLine(
        Offset(size.width, 0),
        Offset(size.width - lineLength, 0),
        paint,
      );
      // Vertical right
      canvas.drawLine(
        Offset(size.width, 0),
        Offset(size.width, lineLength),
        paint,
      );
    }

    if (bottomLeft) {
      // Horizontal bottom
      canvas.drawLine(
        Offset(0, size.height),
        Offset(lineLength, size.height),
        paint,
      );
      // Vertical left
      canvas.drawLine(
        Offset(0, size.height),
        Offset(0, size.height - lineLength),
        paint,
      );
    }

    if (bottomRight) {
      // Horizontal bottom
      canvas.drawLine(
        Offset(size.width, size.height),
        Offset(size.width - lineLength, size.height),
        paint,
      );
      // Vertical right
      canvas.drawLine(
        Offset(size.width, size.height),
        Offset(size.width, size.height - lineLength),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(CornerBracketPainter oldDelegate) => false;
}

enum UploadMethod { scan, file }
