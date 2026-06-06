import 'package:legaleasier/features/chatbot/domain/chat_message.dart';

class ChatResponse {
  final String question;
  final String answer;
  final List<String> suggestions;
  final int? remainingQuota;

  ChatResponse({
    required this.question,
    required this.answer,
    required this.suggestions,
    this.remainingQuota,
  });
}

abstract class ChatRepository {
  Future<ChatResponse> sendMessage(
    String documentId,
    String message,
    List<ChatMessage> history,
  );

  Future<List<ChatMessage>> fetchHistory(String documentId);
}
