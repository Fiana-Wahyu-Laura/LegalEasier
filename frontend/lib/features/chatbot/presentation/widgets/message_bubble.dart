import 'package:flutter/material.dart';
import 'package:legaleasier/core/theme/app_theme.dart';
import 'package:legaleasier/features/chatbot/domain/chat_message.dart';

class MessageBubble extends StatelessWidget {
  final ChatMessage message;

  const MessageBubble({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    final isUser = message.sender == ChatMessageSender.user;
    final alignment = isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start;
    final bubbleColor = isUser ? AppColors.brand2 : AppColors.white;
    final textColor = isUser ? AppColors.white : AppColors.text1;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: alignment,
        children: [
          Container(
            decoration: BoxDecoration(
              color: bubbleColor,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: isUser ? AppColors.brand2 : Colors.black.withOpacity(0.08),
              ),
            ),
            padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
            child: Text(
              message.text,
              style: AppTextStyles.bodyLarge.copyWith(color: textColor),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            _formatTimestamp(message.timestamp),
            style: AppTextStyles.meta,
          ),
        ],
      ),
    );
  }

  String _formatTimestamp(DateTime timestamp) {
    return '${timestamp.hour.toString().padLeft(2, '0')}:${timestamp.minute.toString().padLeft(2, '0')}';
  }
}
