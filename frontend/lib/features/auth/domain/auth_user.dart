class AuthUser {
  final String uid;
  final String? email;
  final String? displayName;
  final bool isGuest;

  const AuthUser({
    required this.uid,
    this.email,
    this.displayName,
    this.isGuest = false,
  });
}
