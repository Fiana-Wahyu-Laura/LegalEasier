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

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  void _sendMessage() {
    final message = _messageController.text.trim();
    if (message.isEmpty) return;
    ref.read(chatNotifierProvider(widget.documentId).notifier).sendMessage(message);
    _messageController.clear();
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(chatNotifierProvider(widget.documentId));

    final data = chatState.maybeWhen(data: (d) => d, orElse: () => null);
    final suggestions = data?.suggestions ?? <String>[];
    final isSending = data?.isSending == true;

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
          Expanded(
            child: chatState.when(
              data: (data) {
                if (data.messages.isEmpty) {
                  return Center(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 24),
                      child: Text(
                        'Mulai tanya AI LegalEasy untuk mendapatkan jawaban berbasis dokumen.',
                        style: AppTextStyles.bodyLarge.copyWith(color: AppColors.text2),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  );
                }

                return ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  itemCount: data.messages.length,
                  itemBuilder: (context, index) {
                    final message = data.messages[index];
                    return MessageBubble(message: message);
                  },
                );
              },
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, stackTrace) => Center(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: Text(
                    'Gagal memuat chat. Silakan coba lagi.',
                    style: AppTextStyles.bodyLarge.copyWith(color: AppColors.danger),
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
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
}
