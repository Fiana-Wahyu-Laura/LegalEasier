import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:legaleasier/core/theme/app_theme.dart';
import 'package:legaleasier/features/chatbot/presentation/providers/chat_provider.dart';
import 'package:legaleasier/features/chatbot/presentation/widgets/message_bubble.dart';
import 'package:legaleasier/features/chatbot/presentation/widgets/suggestion_chips.dart';

class ChatScreen extends ConsumerStatefulWidget {
  final String documentId;
  final String documentTitle;

  const ChatScreen({
    super.key,
    required this.documentId,
    required this.documentTitle,
  });

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _messageController = TextEditingController();
  final _scrollController = ScrollController();

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _sendMessage() {
    final message = _messageController.text.trim();
    if (message.isEmpty) return;
    ref
        .read(chatNotifierProvider(widget.documentId).notifier)
        .sendMessage(message);
    _messageController.clear();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(chatNotifierProvider(widget.documentId));

    final data = chatState.maybeWhen(data: (d) => d, orElse: () => null);
    final suggestions = data?.suggestions ?? <String>[];
    final isSending = data?.isSending == true;
    final errorMessage = data?.errorMessage;

    // Show error as a banner at the top of the chat area.
    Widget? errorBanner;
    if (errorMessage != null && errorMessage.isNotEmpty) {
      errorBanner = Container(
        width: double.infinity,
        margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: AppColors.danger.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          children: [
            const Icon(Icons.error_outline, size: 18, color: AppColors.danger),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                _cleanError(errorMessage),
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.danger,
                  height: 1.3,
                ),
              ),
            ),
            GestureDetector(
              onTap: () {
                ref
                    .read(chatNotifierProvider(widget.documentId).notifier)
                    // Clear error by resending last message –-
                    // actually just let the user retry manually.
                    ;
              },
              child: const Icon(Icons.close, size: 16, color: AppColors.danger),
            ),
          ],
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.documentTitle),
        actions: [
          IconButton(
            onPressed: () {
              ref.invalidate(chatNotifierProvider(widget.documentId));
            },
            icon: const Icon(Icons.refresh),
            tooltip: 'Muat ulang',
          ),
        ],
      ),
      body: Column(
        children: [
          // Error banner above chat
          if (errorBanner != null) errorBanner,

          Expanded(
            child: chatState.when(
              data: (data) {
                if (data.messages.isEmpty && !isSending) {
                  return _buildEmptyState();
                }
                return _buildMessageList(data.messages, isSending);
              },
              loading: () => _buildLoadingState(),
              error: (error, stackTrace) => _buildErrorState(),
            ),
          ),

          const Divider(height: 1),

          if (suggestions.isNotEmpty)
            SuggestionChips(
              suggestions: suggestions,
              onSelected: (suggestion) {
                _messageController.text = suggestion;
                _sendMessage();
              },
            ),

          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: const InputDecoration(
                      hintText: 'Tulis pertanyaan Anda...',
                      border: OutlineInputBorder(),
                    ),
                    textInputAction: TextInputAction.send,
                    onSubmitted: (_) => _sendMessage(),
                  ),
                ),
                const SizedBox(width: 10),
                IconButton(
                  icon: const Icon(Icons.send),
                  color: isSending ? AppColors.text3 : AppColors.brand,
                  onPressed: isSending ? null : _sendMessage,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// Remove "Exception: " prefix and trim for display.
  String _cleanError(String raw) {
    return raw
        .replaceFirst(RegExp(r'^Exception:\s*'), '')
        .trim();
  }

  // --- State builders ---

  Widget _buildLoadingState() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CircularProgressIndicator(),
          const SizedBox(height: 20),
          Text(
            'Menyiapkan chat...',
            style: AppTextStyles.bodyLarge.copyWith(color: AppColors.text2),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 48, color: AppColors.danger),
            const SizedBox(height: 16),
            Text(
              'Gagal memuat chat.',
              style: AppTextStyles.bodyLarge.copyWith(color: AppColors.danger),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'Silakan muat ulang atau coba beberapa saat lagi.',
              style: AppTextStyles.bodySmall.copyWith(color: AppColors.text2),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: () {
                ref.invalidate(chatNotifierProvider(widget.documentId));
              },
              icon: const Icon(Icons.refresh),
              label: const Text('Muat Ulang'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: AppColors.brand.withValues(alpha: 0.08),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.chat_bubble_outline,
                size: 36,
                color: AppColors.brand,
              ),
            ),
            const SizedBox(height: 20),
            Text(
              'Tanya AI LegalEasy',
              style: AppTextStyles.screenTitle.copyWith(fontSize: 18),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'Ajukan pertanyaan tentang dokumen Anda. AI kami akan '
              'menjawab berdasarkan isi dokumen yang telah dianalisis.',
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.text2,
                height: 1.5,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.center,
              children: [
                _buildExampleChip('Apa isi dokumen ini?'),
                _buildExampleChip('Apa saja risikonya?'),
                _buildExampleChip('Apa yang perlu saya perhatikan?'),
                _buildExampleChip('Jelaskan klausul penting'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildExampleChip(String label) {
    return ActionChip(
      label: Text(label, style: AppTextStyles.bodySmall.copyWith(fontSize: 12)),
      onPressed: () {
        _messageController.text = label;
        _sendMessage();
      },
    );
  }

  /// Message list with optional typing indicator at the end.
  Widget _buildMessageList(List<dynamic> messages, bool isSending) {
    // After build completes, scroll to bottom for new messages.
    _scrollToBottom();

    final items = <Widget>[];
    for (final message in messages) {
      items.add(MessageBubble(message: message));
    }

    // Typing indicator when AI is responding.
    if (isSending) {
      items.add(_buildTypingIndicator());
    }

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      itemCount: items.length,
      itemBuilder: (context, index) => items[index],
    );
  }

  /// Animated typing dots bubble.
  Widget _buildTypingIndicator() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Align(
        alignment: Alignment.centerLeft,
        child: Container(
          decoration: BoxDecoration(
            color: AppColors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: Colors.black.withValues(alpha: 0.08),
            ),
          ),
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
          child: const Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _TypingDot(delay: 0),
              SizedBox(width: 4),
              _TypingDot(delay: 200),
              SizedBox(width: 4),
              _TypingDot(delay: 400),
            ],
          ),
        ),
      ),
    );
  }
}

/// Single animated dot for the typing indicator.
class _TypingDot extends StatefulWidget {
  final int delay;
  const _TypingDot({required this.delay});

  @override
  State<_TypingDot> createState() => _TypingDotState();
}

class _TypingDotState extends State<_TypingDot>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    Future.delayed(Duration(milliseconds: widget.delay), () {
      if (mounted) _controller.repeat(reverse: true);
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        final opacity = (_controller.value * 1.0).clamp(0.2, 1.0);
        return Opacity(
          opacity: opacity,
          child: Container(
            width: 8,
            height: 8,
            decoration: const BoxDecoration(
              color: AppColors.text3,
              shape: BoxShape.circle,
            ),
          ),
        );
      },
    );
  }
}
