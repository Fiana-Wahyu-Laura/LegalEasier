/// Shared API constants used across all service classes.
///
/// Single source of truth for API prefix — avoid duplicating '/api/v1'
/// in every service file.
class ApiConstants {
  /// API version prefix for all backend endpoints.
  static const String apiPrefix = '/api/v1';
}
