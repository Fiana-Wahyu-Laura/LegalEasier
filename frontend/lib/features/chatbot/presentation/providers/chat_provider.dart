import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:legaleasier/core/http/dio_provider.dart';
import 'package:legaleasier/features/chatbot/data/chat_repository_impl.dart';
import 'package:legaleasier/features/chatbot/data/chat_service.dart';
import 'package:legaleasier/features/chatbot/domain/chat_message.dart';
import 'package:legaleasier/features/chatbot/domain/chat_repository.dart';

final chatRepositoryProvider = Provider<ChatRepository>((ref) {
  final dio = ref.watch(dioProvider);
  return ChatRepositoryImpl(chatService: ChatService(dio: dio));
});

final chatNotifierProvider = StateNotifierProvider.autoDispose
    .family<ChatNotifier, AsyncValue<ChatState>, String>(
  (ref, documentId) {
    return ChatNotifier(
      repository: ref.watch(chatRepositoryProvider),
      documentId: documentId,
    );
  },
);

class ChatState {
  final List<ChatMessage> messages;
  final List<String> suggestions;
  final int? remainingQuota;
  final bool isSending;
  final String? errorMessage;

  ChatState({
    required this.messages,
    required this.suggestions,
    required this.remainingQuota,
    required this.isSending,
    this.errorMessage,
  });

  factory ChatState.initial() {
    return ChatState(
      messages: [],
      suggestions: [],
      remainingQuota: null,
      isSending: false,
      errorMessage: null,
    );
  }

  ChatState copyWith({
    List<ChatMessage>? messages,
    List<String>? suggestions,
    int? remainingQuota,
    bool? isSending,
    String? errorMessage,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      suggestions: suggestions ?? this.suggestions,
      remainingQuota: remainingQuota ?? this.remainingQuota,
      isSending: isSending ?? this.isSending,
      errorMessage: errorMessage, // null explicitly clears error unless passed
    );
  }
}

class ChatNotifier extends StateNotifier<AsyncValue<ChatState>> {
  final ChatRepository repository;
  final String documentId;

  ChatNotifier({required this.repository, required this.documentId})
      : super(const AsyncValue.loading()) {
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    try {
      final messages = await repository.fetchHistory(documentId);
      state = AsyncValue.data(ChatState.initial().copyWith(messages: messages));
    } catch (e, st) {
      // Fallback to empty state on load failure
      state = AsyncValue.data(ChatState.initial());
    }
  }

  Future<void> sendMessage(String message) async {
    final currentState = state.value ?? ChatState.initial();
    final userMessage = ChatMessage.user(message);
    final updatedMessages = [...currentState.messages, userMessage];

    state = AsyncValue.data(
      currentState.copyWith(
        messages: updatedMessages,
        isSending: true,
        suggestions: [],
      ),
    );

    try {
      final response = await repository.sendMessage(documentId, message, updatedMessages);
      final botMessage = ChatMessage.assistant(response.answer);
      final nextState = currentState.copyWith(
        messages: [...updatedMessages, botMessage],
        suggestions: response.suggestions,
        remainingQuota: response.remainingQuota,
        isSending: false,
      );
      state = AsyncValue.data(nextState);
    } catch (error, stackTrace) {
      // Preserve history, only update error message
      state = AsyncValue.data(currentState.copyWith(
        messages: updatedMessages,
        isSending: false,
        errorMessage: error.toString(),
      ));
    }
  }
}
