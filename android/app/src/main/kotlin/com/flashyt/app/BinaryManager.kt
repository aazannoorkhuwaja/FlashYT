package com.flashyt.app

import android.content.Context
import com.arthenica.ffmpegkit.FFmpegKitConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

/**
 * Manages the setup and paths of binary executables required for downloading.
 *
 * yt-dlp: bundled in assets/yt-dlp (ARM64 standalone binary), copied to filesDir/bin on first launch.
 * ffmpeg: provided automatically by the ffmpeg-kit-full Gradle dependency — no manual bundling needed.
 *         FFmpegKitConfig.getFFmpegPath(context) returns the correct path at runtime.
 */
object BinaryManager {

    private const val YTDLP_BINARY = "yt-dlp"

    /**
     * Ensures yt-dlp is copied from assets and executable.
     * Must be called from an IO coroutine before any download or info fetch.
     *
     * @return true if setup succeeded and yt-dlp is runnable, false otherwise.
     */
    suspend fun setup(context: Context): Boolean = withContext(Dispatchers.IO) {
        try {
            copyYtDlp(context)
            verifyYtDlp(context)
        } catch (e: Exception) {
            false
        }
    }

    private fun copyYtDlp(context: Context) {
        val binDir = getBinDir(context)
        val dest = File(binDir, YTDLP_BINARY)
        if (!dest.exists()) {
            context.assets.open(YTDLP_BINARY).use { input ->
                dest.outputStream().use { output ->
                    input.copyTo(output)
                }
            }
        }
        // Always ensure executable bit is set (survives reinstalls via the exists() check above)
        dest.setExecutable(true, false)
    }

    private fun verifyYtDlp(context: Context): Boolean {
        return try {
            val ytDlp = File(getBinDir(context), YTDLP_BINARY)
            ProcessBuilder(ytDlp.absolutePath, "--version")
                .redirectErrorStream(true)
                .start()
                .inputStream
                .bufferedReader()
                .readLine() != null
        } catch (e: Exception) {
            false
        }
    }

    /** Absolute path to the yt-dlp binary in the app's private files directory. */
    fun getYtDlpPath(context: Context): String =
        File(getBinDir(context), YTDLP_BINARY).absolutePath

    /**
     * Absolute path to the ffmpeg binary managed by ffmpeg-kit-full.
     * ffmpeg-kit extracts its native binary on first use — no manual setup required.
     * This path is passed to yt-dlp via --ffmpeg-location.
     */
    fun getFfmpegPath(context: Context): String =
        FFmpegKitConfig.getFFmpegPath(context)

    private fun getBinDir(context: Context): File =
        File(context.filesDir, "bin").also { it.mkdirs() }
}
