import 'package:dio/dio.dart';
import 'package:legaleasier/core/constants/api_constants.dart';
import 'package:legaleasier/features/chatbot/domain/chat_message.dart';
import 'package:legaleasier/features/chatbot/domain/chat_repository.dart';

class ChatService {
  static const _apiPrefix = ApiConstants.apiPrefix;

  final Dio dio;

  ChatService({required this.dio});

  /// Fetch persisted chat history from backend.
  /// Returns a list of ChatMessage pairs (user question + assistant answer).
  Future<List<ChatMessage>> fetchHistory(String documentId) async {
    try {
      final response = await dio.get(
        '$_apiPrefix/chat/$documentId/history',
        queryParameters: {'limit': 50, 'offset': 0},
      );

      if (response.statusCode == 200) {
        final responseData = response.data;
        if (responseData['success'] == true && responseData['data'] != null) {
          final data = responseData['data'] as Map<String, dynamic>;
          final items = data['items'] as List<dynamic>? ?? [];

          final messages = <ChatMessage>[];
          for (final item in items) {
            final question = item['question'] as String? ?? '';
            final answer = item['answer'] as String? ?? '';
            if (question.isNotEmpty) {
              messages.add(ChatMessage.user(question));
            }
            if (answer.isNotEmpty) {
              messages.add(ChatMessage.assistant(answer));
            }
          }
          return messages;
        }
      }
      return [];
    } on DioException {
      // Silently return empty on failure — chat will start fresh
      return [];
    }
  }

  Future<ChatResponse> sendMessage(
    String documentId,
    String message,
    List<ChatMessage> history,
  ) async {
    try {
      final response = await dio.post(
        '$_apiPrefix/chat/$documentId/message',
        data: {
          'message': message,
          'history': history.map((item) => item.toJson()).toList(),
          'top_k': 5,
        },
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final responseData = response.data;
        if (responseData['success'] == true && responseData['data'] != null) {
          final data = responseData['data'] as Map<String, dynamic>;
          final suggestions = <String>[];
          if (data['suggestions'] is List<dynamic>) {
            suggestions.addAll(
              (data['suggestions'] as List<dynamic>)
                  .whereType<String>()
                  .toList(),
            );
          }

          return ChatResponse(
            question: data['question'] as String? ?? message,
            answer: data['answer'] as String? ?? '',
            suggestions: suggestions,
            remainingQuota: data['remaining_quota'] as int?,
          );
        }
      }

      throw Exception('Gagal mengirim pesan chat: ${response.statusCode}');
    } on DioException catch (error) {
      final statusCode = error.response?.statusCode;
      final message = error.response?.data['message'] as String?;
      throw Exception(
          message ?? 'Kesalahan jaringan saat mengirim pesan chat (Code: $statusCode)');
    }
  }
}
