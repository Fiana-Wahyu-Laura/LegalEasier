import 'package:legaleasier/features/chatbot/data/chat_service.dart';
import 'package:legaleasier/features/chatbot/domain/chat_message.dart';
import 'package:legaleasier/features/chatbot/domain/chat_repository.dart';

class ChatRepositoryImpl implements ChatRepository {
  final ChatService chatService;

  ChatRepositoryImpl({required this.chatService});

  @override
  Future<ChatResponse> sendMessage(
    String documentId,
    String message,
    List<ChatMessage> history,
  ) async {
    return chatService.sendMessage(documentId, message, history);
  }
}
