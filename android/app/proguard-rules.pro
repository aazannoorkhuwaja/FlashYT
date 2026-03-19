# Add project specific ProGuard rules here.
# By default, the flags in this file are appended to flags specified
# in build.gradle.kts's proguardFiles setting.

# Keep yt-dlp execution classes
-keepclassmembers class com.flashyt.app.** { *; }

# Keep ffmpeg-kit classes
-keep class com.arthenica.ffmpegkit.** { *; }
-dontwarn com.arthenica.ffmpegkit.**

# Keep Coil
-keep class io.coil.** { *; }
-dontwarn io.coil.**

# Kotlin coroutines
-keep class kotlinx.coroutines.** { *; }
-dontwarn kotlinx.coroutines.**
