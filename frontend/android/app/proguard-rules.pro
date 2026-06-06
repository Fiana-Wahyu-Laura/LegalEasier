# Flutter / Dart
-keep class io.flutter.** { *; }
-keep class io.flutter.plugins.** { *; }

# Firebase
-keep class com.google.firebase.** { *; }
-dontwarn com.google.firebase.**

# Gson / JSON
-keepattributes Signature
-keepattributes *Annotation*

# Keep Dio / OkHttp
-dontwarn okhttp3.**
-dontwarn okio.**
