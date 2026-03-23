package com.flashyt.app

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

/**
 * Manages the setup and paths of binary executables required for downloading.
 *
 * yt-dlp: bundled in assets/yt-dlp (ARM64 standalone binary), copied to filesDir/bin on first launch.
 * ffmpeg: bundled in assets/ffmpeg (ARM64 static binary), copied to filesDir/bin on first launch.
 *         Both binaries are passed to yt-dlp via their absolute paths on disk.
 */
object BinaryManager {

    private const val YTDLP_BINARY = "yt-dlp"
    private const val FFMPEG_BINARY = "ffmpeg"

    /**
     * Ensures yt-dlp is copied from assets and executable.
     * Must be called from an IO coroutine before any download or info fetch.
     *
     * @return true if setup succeeded and yt-dlp is runnable, false otherwise.
     */
    suspend fun setup(context: Context): Boolean = withContext(Dispatchers.IO) {
        try {
            copyBinary(context, YTDLP_BINARY)
            copyBinary(context, FFMPEG_BINARY)
            if (!verifyYtDlp(context)) {
                throw IllegalStateException("yt-dlp verification failed (binary may be corrupt or incompatible with this architecture)")
            }
            true
        } catch (e: Exception) {
            android.util.Log.e("BinaryManager", "Setup failed: ${e.message}", e)
            false
        }
    }

    private fun copyBinary(context: Context, name: String) {
        val binDir = getBinDir(context)
        val dest = File(binDir, name)
        if (!dest.exists()) {
            context.assets.open(name).use { input ->
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
            val process = ProcessBuilder(ytDlp.absolutePath, "--version")
                .redirectErrorStream(true)
                .start()
            try {
                val result = process.inputStream.bufferedReader().readLine()
                process.waitFor()
                result != null
            } finally {
                process.destroyForcibly()
            }
        } catch (e: Exception) {
            false
        }
    }

    /** Absolute path to the yt-dlp binary in the app's private files directory. */
    fun getYtDlpPath(context: Context): String =
        File(getBinDir(context), YTDLP_BINARY).absolutePath

    /**
     * Absolute path to the ffmpeg binary in the app's private files directory.
     * The binary is bundled in assets/ffmpeg and extracted on first launch.
     * This path is passed to yt-dlp via --ffmpeg-location.
     */
    fun getFfmpegPath(context: Context): String =
        File(getBinDir(context), FFMPEG_BINARY).absolutePath

    private fun getBinDir(context: Context): File =
        File(context.filesDir, "bin").also { it.mkdirs() }
}
