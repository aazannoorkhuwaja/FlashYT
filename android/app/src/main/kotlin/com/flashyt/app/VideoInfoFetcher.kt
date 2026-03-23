package com.flashyt.app

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

// ---------------------------------------------------------------------------
// Data models
// ---------------------------------------------------------------------------

data class VideoInfo(
    val title: String,
    val channelName: String,
    val thumbnailUrl: String,
    val formats: List<VideoFormat>
)

data class VideoFormat(
    val formatId: String,
    val primaryLabel: String,
    val secondaryLabel: String? = null,
    val estimatedSizeMb: Int,
    val isAudioOnly: Boolean,
    val height: Int?
) {
    val fullLabel: String get() = if (secondaryLabel != null) "$primaryLabel $secondaryLabel" else primaryLabel
}

// ---------------------------------------------------------------------------
// Fetcher
// ---------------------------------------------------------------------------

object VideoInfoFetcher {

    /** The four quality tiers FlashYT always presents (regardless of what yt-dlp lists). */
    private val QUALITY_TIERS = listOf(
        // Triple(Primary, Secondary, height, isAudio)
        QualityTier("1080p", "HD",  1080, false),
        QualityTier("720p",  null,  720,  false),
        QualityTier("480p",  null,  480,  false),
        QualityTier("Audio", "MP3", null, true)
    )

    private data class QualityTier(
        val p: String, val s: String?, val h: Int?, val audio: Boolean
    )

    /**
     * Runs `yt-dlp --dump-json --no-playlist <url>` and parses the result into [VideoInfo].
     * Runs on [Dispatchers.IO] — safe to call from a coroutine on any dispatcher.
     *
     * @return [Result.success] with [VideoInfo] on success, [Result.failure] on any error.
     */
    suspend fun fetch(context: Context, url: String): Result<VideoInfo> =
        withContext(Dispatchers.IO) {
            runCatching {
                val ytDlp = BinaryManager.getYtDlpPath(context)

                val process = ProcessBuilder(
                    ytDlp,
                    "--dump-json",
                    "--no-playlist",
                    "--no-warnings",
                    url
                ).redirectErrorStream(true).start()

                try {
                    val jsonOutput = process.inputStream.bufferedReader().readText()
                    val exitCode = process.waitFor()

                    if (exitCode != 0 || jsonOutput.isBlank()) {
                        Log.w("VideoInfoFetcher", "yt-dlp exited with code $exitCode (output length: ${jsonOutput.length})")
                        throw RuntimeException("yt-dlp error (code $exitCode)")
                    }

                    parseVideoInfo(jsonOutput)
                } finally {
                    process.destroyForcibly()
                }
            }
        }

    private fun parseVideoInfo(json: String): VideoInfo {
        val obj = JSONObject(json)

        val title = obj.optString("title", "Unknown Video")
        val channel = obj.optString("uploader",
            obj.optString("channel", obj.optString("uploader_id", "Unknown Channel")))
        val thumbnail = obj.optString("thumbnail", "")

        // Extract best size estimates from the formats array
        val sizeMap = buildSizeMap(obj)

        val formats = QUALITY_TIERS.map { tier ->
            VideoFormat(
                formatId  = if (tier.audio) "bestaudio" else "bestvideo[height<=${tier.h}]+bestaudio",
                primaryLabel = tier.p,
                secondaryLabel = tier.s,
                estimatedSizeMb = sizeMap[tier.h] ?: defaultSizeMb(tier.h),
                isAudioOnly = tier.audio,
                height    = tier.h
            )
        }

        return VideoInfo(title, channel, thumbnail, formats)
    }

    /**
     * Builds a map of height → estimated size (MB) from the formats array.
     * Uses filesize first, falls back to filesize_approx.
     * For each height bucket, stores the largest found size (video+audio combined estimate).
     */
    private fun buildSizeMap(obj: JSONObject): Map<Int?, Int> {
        val result = mutableMapOf<Int?, Long>()
        val formatsArray = obj.optJSONArray("formats") ?: return emptyMap()

        for (i in 0 until formatsArray.length()) {
            val fmt = formatsArray.optJSONObject(i) ?: continue
            val h: Int? = if (fmt.isNull("height")) null else fmt.optInt("height", -1).takeIf { it > 0 }
            val size = fmt.optLong("filesize", 0L).takeIf { it > 0 }
                ?: fmt.optLong("filesize_approx", 0L).takeIf { it > 0 }
                ?: continue

            result[h] = maxOf(result[h] ?: 0L, size)
        }

        return result.mapValues { (_, size) -> (size / 1_048_576L).toInt() }
    }

    /** Conservative fallback sizes when yt-dlp doesn't report filesize data. */
    private fun defaultSizeMb(height: Int?) = when (height) {
        1080 -> 180
        720  -> 90
        480  -> 45
        null -> 8
        else -> 50
    }
}
