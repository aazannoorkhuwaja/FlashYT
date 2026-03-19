package com.flashyt.app

import android.content.Context
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
    val label: String,
    val estimatedSizeMb: Int,
    val isAudioOnly: Boolean,
    val height: Int?
)

// ---------------------------------------------------------------------------
// Fetcher
// ---------------------------------------------------------------------------

object VideoInfoFetcher {

    /** The four quality tiers FlashYT always presents (regardless of what yt-dlp lists). */
    private val QUALITY_TIERS = listOf(
        Triple("1080p HD",       1080, false),
        Triple("720p",            720, false),
        Triple("480p",            480, false),
        Triple("Audio MP3",       null, true)
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
                )
                    .redirectErrorStream(false)
                    .start()

                val jsonOutput = process.inputStream.bufferedReader().readText()
                val stderrOutput = process.errorStream.bufferedReader().readText()
                val exitCode = process.waitFor()

                if (exitCode != 0 || jsonOutput.isBlank()) {
                    throw RuntimeException(
                        "yt-dlp exited with code $exitCode.\nStderr: ${stderrOutput.take(300)}"
                    )
                }

                parseVideoInfo(jsonOutput)
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

        val formats = QUALITY_TIERS.map { (label, height, isAudio) ->
            VideoFormat(
                formatId  = if (isAudio) "bestaudio" else "bestvideo[height<=${height}]+bestaudio",
                label     = label,
                estimatedSizeMb = sizeMap[height] ?: defaultSizeMb(height),
                isAudioOnly = isAudio,
                height    = height
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

        return result.mapValues { (size) -> (size / 1_048_576L).toInt() }
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
