package com.flashyt.app

import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.os.IBinder
import android.util.Log
import androidx.core.content.FileProvider
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.io.File

/**
 * Foreground service that runs yt-dlp as a subprocess and streams its output to track progress.
 *
 * Started by [ShareActivity] after the user selects a quality.
 * Lives independently of any Activity — download continues if screen is locked or app is in bg.
 *
 * Cancellation: the ongoing notification has a CANCEL action that sends ACTION_CANCEL back here,
 * which kills the yt-dlp subprocess and stops the service.
 */
class DownloadService : Service() {

    private var downloadJob: Job? = null
    private var currentProcess: Process? = null

    companion object {
        const val ACTION_CANCEL = "com.flashyt.app.ACTION_CANCEL_DOWNLOAD"
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Handle cancel action from notification button
        if (intent?.action == ACTION_CANCEL) {
            cancelDownload()
            return START_NOT_STICKY
        }

        val url = intent?.getStringExtra("url") ?: run { stopSelf(); return START_NOT_STICKY }
        val isAudioOnly = intent.getBooleanExtra("is_audio_only", false)
        val height = intent.getIntExtra("height", 1080)

        FlashYTNotificationManager.createChannels(this)

        // Must call startForeground immediately (Android 12+ strict requirement)
        startForeground(
            FlashYTNotificationManager.NOTIF_ID_PROGRESS,
            FlashYTNotificationManager.buildProgressNotification(
                context = this,
                title = "Preparing…",
                progress = 0,
                cancelIntent = buildCancelIntent()
            )
        )

        val serviceJob = SupervisorJob()
        downloadJob = CoroutineScope(Dispatchers.IO + serviceJob).launch {
            try {
                runDownload(url, isAudioOnly, height)
            } finally {
                serviceJob.cancel()
            }
            stopSelf()
        }

        return START_REDELIVER_INTENT
    }

    // -----------------------------------------------------------------------
    // Download orchestration
    // -----------------------------------------------------------------------

    private fun runDownload(url: String, isAudioOnly: Boolean, height: Int) {
        val ytDlp  = BinaryManager.getYtDlpPath(this)
        val ffmpeg = BinaryManager.getFfmpegPath(this)
        val outputDir = getDownloadDirectory()
        val outputTemplate = "$outputDir/%(title)s.%(ext)s"

        val cmd = buildCommand(ytDlp, ffmpeg, url, isAudioOnly, height, outputTemplate)

        try {
            val process = ProcessBuilder(cmd)
                .redirectErrorStream(true)
                .start()
            currentProcess = process

            // Stream yt-dlp output, parse progress lines
            var lastProgress = -1
            var videoTitle = "Downloading…"
            val progressRegex = Regex("""\[download\]\s+([\d.]+)%""")
            val speedRegex    = Regex("""at\s+([\d.]+\s*\w+/s)""")

            process.inputStream.bufferedReader().forEachLine { line ->
                // yt-dlp prints destination file name early — extract a clean title from it
                if (line.startsWith("[download] Destination:")) {
                    val filename = line.substringAfterLast("/").substringBeforeLast(".")
                    if (filename.isNotBlank()) videoTitle = filename.take(60)
                }

                progressRegex.find(line)?.groupValues?.get(1)?.toFloatOrNull()?.let { pctF ->
                    val pct = pctF.toInt()
                    if (pct != lastProgress) {
                        lastProgress = pct
                        val speed = speedRegex.find(line)?.groupValues?.get(1) ?: ""
                        updateProgressNotification(videoTitle, pct, speed)
                    }
                }
            }

            val exitCode = process.waitFor()
            currentProcess = null

            if (exitCode == 0) {
                val fileUri = resolveOutputUri(outputDir, videoTitle)
                showCompleteNotification(videoTitle, fileUri)
            } else {
                // Download failed silently — dismiss progress notification
                stopForeground(STOP_FOREGROUND_REMOVE)
            }

        } catch (e: Exception) {
            Log.e("DownloadService", "Download failed: ", e)
            showErrorNotification("Download failed: ${e.message}")
            stopForeground(STOP_FOREGROUND_REMOVE)
        }
    }

    private fun showErrorNotification(message: String) {
        val notif = FlashYTNotificationManager.buildErrorNotification(this, message)
        (getSystemService(NOTIFICATION_SERVICE) as NotificationManager)
            .notify(FlashYTNotificationManager.NOTIF_ID_ERROR, notif)
    }

    // -----------------------------------------------------------------------
    // Command construction
    // -----------------------------------------------------------------------

    private fun buildCommand(
        ytDlp: String, ffmpeg: String, url: String,
        isAudioOnly: Boolean, height: Int, outputTemplate: String
    ): List<String> = if (isAudioOnly) {
        listOf(
            ytDlp,
            "--ffmpeg-location", ffmpeg,
            "-f", "bestaudio",
            "--extract-audio",
            "--audio-format", "mp3",
            "--output", outputTemplate,
            "--newline",
            "--no-playlist",
            url
        )
    } else {
        listOf(
            ytDlp,
            "--ffmpeg-location", ffmpeg,
            "-f", "bestvideo[height<=${height}]+bestaudio/best[height<=${height}]",
            "--merge-output-format", "mp4",
            "--output", outputTemplate,
            "--newline",
            "--no-playlist",
            url
        )
    }

    // -----------------------------------------------------------------------
    // Output directory
    // -----------------------------------------------------------------------

    /**
     * Returns a writable directory for the downloaded file.
     * Uses the app's external files Downloads directory — no storage permission needed on any SDK.
     * Files are visible from the notification's Open File action via FileProvider.
     */
    private fun getDownloadDirectory(): String {
        val dir = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS)
            ?: filesDir
        if (!dir.exists() && !dir.mkdirs()) {
            throw IllegalStateException("Failed to create download directory: ${dir.absolutePath}")
        }
        return dir.absolutePath
    }

    /** Scans the output directory for the most recently modified file matching the title. */
    private fun resolveOutputUri(dir: String, title: String): Uri? {
        return try {
            val directory = File(dir)
            val match = directory.listFiles()
                ?.filter { it.isFile && it.name.startsWith(title.take(20), ignoreCase = true) }
                ?.maxByOrNull { it.lastModified() }
                ?: directory.listFiles()?.maxByOrNull { it.lastModified() }

            match?.let { file ->
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                    FileProvider.getUriForFile(this, "$packageName.fileprovider", file)
                } else {
                    Uri.fromFile(file)
                }
            }
        } catch (e: Exception) {
            null
        }
    }

    // -----------------------------------------------------------------------
    // Notification helpers
    // -----------------------------------------------------------------------

    private fun updateProgressNotification(title: String, progress: Int, speed: String) {
        val notif = FlashYTNotificationManager.buildProgressNotification(
            context = this,
            title = title,
            progress = progress,
            speedText = speed,
            cancelIntent = buildCancelIntent()
        )
        (getSystemService(NOTIFICATION_SERVICE) as NotificationManager)
            .notify(FlashYTNotificationManager.NOTIF_ID_PROGRESS, notif)
    }

    private fun showCompleteNotification(title: String, fileUri: Uri?) {
        stopForeground(STOP_FOREGROUND_DETACH)
        val notif = FlashYTNotificationManager.buildCompleteNotification(this, title, fileUri)
        (getSystemService(NOTIFICATION_SERVICE) as NotificationManager)
            .notify(FlashYTNotificationManager.NOTIF_ID_COMPLETE, notif)
    }

    private fun buildCancelIntent(): PendingIntent {
        val cancelIntent = Intent(this, DownloadService::class.java).apply {
            action = ACTION_CANCEL
        }
        return PendingIntent.getService(
            this, 99, cancelIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
    }

    // -----------------------------------------------------------------------
    // Cancellation
    // -----------------------------------------------------------------------

    private fun cancelDownload() {
        downloadJob?.cancel()
        currentProcess?.destroyForcibly()
        currentProcess = null
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        super.onDestroy()
        downloadJob?.cancel()
        currentProcess?.destroyForcibly()
    }
}
