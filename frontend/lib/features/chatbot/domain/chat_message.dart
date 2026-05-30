enum ChatMessageSender { user, assistant }

extension ChatMessageSenderExtension on ChatMessageSender {
  String get roleValue {
    switch (this) {
      case ChatMessageSender.user:
        return 'user';
      case ChatMessageSender.assistant:
        return 'assistant';
    }
  }
}

class ChatMessage {
  final String id;
  final String text;
  final ChatMessageSender sender;
  final DateTime timestamp;
  final bool isSuggestion;

  ChatMessage({
    required this.id,
    required this.text,
    required this.sender,
    required this.timestamp,
    this.isSuggestion = false,
  });

  factory ChatMessage.user(String text) {
    return ChatMessage(
      id: DateTime.now().microsecondsSinceEpoch.toString(),
      text: text,
      sender: ChatMessageSender.user,
      timestamp: DateTime.now(),
    );
  }

  factory ChatMessage.assistant(String text) {
    return ChatMessage(
      id: DateTime.now().microsecondsSinceEpoch.toString(),
      text: text,
      sender: ChatMessageSender.assistant,
      timestamp: DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'role': sender.roleValue,
      'content': text,
    };
  }
}
