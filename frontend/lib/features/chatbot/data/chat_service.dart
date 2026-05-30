import 'package:dio/dio.dart';
import 'package:legaleasier/features/chatbot/domain/chat_message.dart';
import 'package:legaleasier/features/chatbot/domain/chat_repository.dart';

class ChatService {
  static const _apiPrefix = '/api/v1';

  final Dio dio;

  ChatService({required this.dio});

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
