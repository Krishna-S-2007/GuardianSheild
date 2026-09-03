# WebRTC keep rules
-keep class org.webrtc.** { *; }
-dontwarn org.webrtc.**

# Gson keep rules
-keepattributes Signature
-keepattributes *Annotation*
-keep class com.google.gson.** { *; }
-keep class com.guardianshield.webrtc.** { *; }
-keep class com.guardianshield.audio.** { *; }
