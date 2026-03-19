package com.flashyt.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.net.Uri
import androidx.core.app.NotificationCompat

/**
 * Central factory for all FlashYT notifications.
 *
 * Two channels:
 *  - [CHANNEL_PROGRESS] (IMPORTANCE_LOW, no sound) — live download progress bar.
 *  - [CHANNEL_COMPLETE] (IMPORTANCE_DEFAULT) — one-shot completion alert.
 */
object FlashYTNotificationManager {

    const val CHANNEL_PROGRESS = "flashyt_downloads"
    const val CHANNEL_COMPLETE = "flashyt_complete"

    /** Notification ID for the ongoing progress notification (reused for updates). */
    const val NOTIF_ID_PROGRESS = 1001

    /** Notification ID for the completion notification (different ID so it stays after download). */
    const val NOTIF_ID_COMPLETE = 1002

    /** Notification ID for error notifications. */
    const val NOTIF_ID_ERROR = 1003

    // -----------------------------------------------------------------------
    // Channel setup — idempotent, safe to call multiple times
    // -----------------------------------------------------------------------

    private const val CHANNEL_ERROR = "flashyt_error"

    fun createChannels(context: Context) {
        val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        NotificationChannel(CHANNEL_PROGRESS, "Downloads", NotificationManager.IMPORTANCE_LOW).apply {
            description = "Shows active download progress"
            setShowBadge(false)
        }.also { nm.createNotificationChannel(it) }

        NotificationChannel(CHANNEL_COMPLETE, "Download Complete", NotificationManager.IMPORTANCE_DEFAULT).apply {
            description = "Notifies when a download finishes"
        }.also { nm.createNotificationChannel(it) }

        NotificationChannel(CHANNEL_ERROR, "Errors", NotificationManager.IMPORTANCE_HIGH).apply {
            description = "Shows download errors"
        }.also { nm.createNotificationChannel(it) }
    }

    // -----------------------------------------------------------------------
    // Progress notification
    // -----------------------------------------------------------------------

    fun buildProgressNotification(
        context: Context,
        title: String,
        progress: Int,
        speedText: String = "",
        cancelIntent: PendingIntent? = null
    ): Notification {
        val indeterminate = progress <= 0
        val subText = when {
            speedText.isNotEmpty() -> "$progress% • $speedText"
            !indeterminate         -> "$progress%"
            else                   -> context.getString(R.string.preparing)
        }

        return NotificationCompat.Builder(context, CHANNEL_PROGRESS)
            .setSmallIcon(R.drawable.ic_flashyt)
            .setContentTitle(context.getString(R.string.downloading))
            .setContentText(title.take(60))
            .setSubText(subText)
            .setProgress(100, progress.coerceIn(0, 100), indeterminate)
            .setOngoing(true)
            .setSilent(true)
            .setOnlyAlertOnce(true)
            .apply {
                cancelIntent?.let { addAction(R.drawable.ic_cancel, context.getString(R.string.cancel), it) }
            }
            .build()
    }

    // -----------------------------------------------------------------------
    // Completion notification
    // -----------------------------------------------------------------------

    fun buildCompleteNotification(
        context: Context,
        title: String,
        fileUri: Uri?
    ): Notification {
        val fileName = fileUri?.lastPathSegment ?: ""
        val mimeType = getMimeType(fileName)

        val openPendingIntent = fileUri?.let { uri ->
            val viewIntent = android.content.Intent(android.content.Intent.ACTION_VIEW).apply {
                setDataAndType(uri, mimeType)
                flags = android.content.Intent.FLAG_ACTIVITY_NEW_TASK or
                        android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION
            }
            PendingIntent.getActivity(
                context, 0, viewIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
        }

        val sharePendingIntent = fileUri?.let { uri ->
            val shareIntent = android.content.Intent(android.content.Intent.ACTION_SEND).apply {
                type = mimeType
                putExtra(android.content.Intent.EXTRA_STREAM, uri)
                addFlags(android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            PendingIntent.getActivity(
                context, 1,
                android.content.Intent.createChooser(shareIntent, context.getString(R.string.share)),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
        }

        return NotificationCompat.Builder(context, CHANNEL_COMPLETE)
            .setSmallIcon(android.R.drawable.stat_sys_download_done)
            .setContentTitle(context.getString(R.string.download_complete))
            .setContentText(title.take(60))
            .setAutoCancel(true)
            .apply {
                openPendingIntent?.let {
                    setContentIntent(it)
                    addAction(0, context.getString(R.string.open_file), it)
                }
                sharePendingIntent?.let {
                    addAction(0, context.getString(R.string.share), it)
                }
            }
            .build()
    }

    // -----------------------------------------------------------------------
    // Error notification
    // -----------------------------------------------------------------------

    fun buildErrorNotification(context: Context, message: String): Notification {
        return NotificationCompat.Builder(context, CHANNEL_ERROR)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle(context.getString(R.string.download_failed))
            .setContentText(message.take(100))
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build()
    }

    // -----------------------------------------------------------------------
    // MIME type helper
    // -----------------------------------------------------------------------

    fun getMimeType(fileName: String): String {
        return when {
            fileName.endsWith(".mp3", ignoreCase = true) -> "audio/mpeg"
            fileName.endsWith(".m4a", ignoreCase = true) -> "audio/mp4"
            fileName.endsWith(".webm", ignoreCase = true) -> "audio/webm"
            fileName.endsWith(".mp4", ignoreCase = true) -> "video/mp4"
            fileName.endsWith(".webm", ignoreCase = true) -> "video/webm"
            else -> "application/octet-stream"
        }
    }
}
