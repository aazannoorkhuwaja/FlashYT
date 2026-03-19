package com.flashyt.app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.View
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import coil.load
import coil.transform.RoundedCornersTransformation
import com.google.android.material.bottomsheet.BottomSheetBehavior
import com.google.android.material.bottomsheet.BottomSheetDialog
import com.google.android.material.card.MaterialCardView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * The one and only Activity in FlashYT.
 *
 * Launched exclusively via the Android share sheet when a user shares text from YouTube.
 * Shows a BottomSheetDialog with:
 *  1. A loading spinner while fetching video metadata.
 *  2. A quality picker (thumbnail, title, channel, 4 quality cards) once ready.
 *
 * After the user taps a quality, starts [DownloadService] and finishes — the Activity
 * disappears immediately and the download continues as a foreground service.
 */
class ShareActivity : AppCompatActivity() {

    private var currentSheet: BottomSheetDialog? = null

    companion object {
        private const val REQUEST_NOTIFICATIONS = 42
    }

    // -----------------------------------------------------------------------
    // Lifecycle
    // -----------------------------------------------------------------------

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Request notification permission on Android 13+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                    REQUEST_NOTIFICATIONS
                )
            }
        }

        val url = extractYouTubeUrl(intent)
        if (url == null) {
            Toast.makeText(this, getString(R.string.not_youtube_link), Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        showLoadingSheet()
        fetchAndShow(url)
    }

    override fun onDestroy() {
        super.onDestroy()
        currentSheet?.dismiss()
    }

    // -----------------------------------------------------------------------
    // URL extraction
    // -----------------------------------------------------------------------

    private fun extractYouTubeUrl(intent: Intent?): String? {
        val text = intent?.getStringExtra(Intent.EXTRA_TEXT) ?: return null
        // extract first URL-like token from shared text (YouTube app shares "Title\nURL")
        return Regex("""https?://[^\s]+""")
            .find(text)
            ?.value
            ?.takeIf { it.contains("youtube.com") || it.contains("youtu.be") }
    }

    // -----------------------------------------------------------------------
    // Loading + fetch
    // -----------------------------------------------------------------------

    private fun fetchAndShow(url: String) {
        lifecycleScope.launch {
            // Setup binaries (no-op after first run — fast)
            val ready = withContext(Dispatchers.IO) {
                BinaryManager.setup(this@ShareActivity)
            }
            if (!ready) {
                dismissAndToast(getString(R.string.binary_setup_failed))
                return@launch
            }

            // Fetch video info with yt-dlp --dump-json
            VideoInfoFetcher.fetch(this@ShareActivity, url)
                .onSuccess { videoInfo -> showQualitySheet(url, videoInfo) }
                .onFailure  { dismissAndToast(getString(R.string.fetch_failed)) }
        }
    }

    // -----------------------------------------------------------------------
    // Loading sheet
    // -----------------------------------------------------------------------

    private fun showLoadingSheet() {
        val sheet = makeSheet()
        val view = layoutInflater.inflate(R.layout.bottom_sheet_loading, null)
        sheet.setContentView(view)
        sheet.setOnCancelListener { finish() }
        sheet.show()
        currentSheet = sheet
    }

    // -----------------------------------------------------------------------
    // Quality picker sheet
    // -----------------------------------------------------------------------

    private fun showQualitySheet(url: String, info: VideoInfo) {
        currentSheet?.dismiss()

        val sheet = makeSheet()
        val view = layoutInflater.inflate(R.layout.bottom_sheet_quality, null)

        // Thumbnail
        view.findViewById<ImageView>(R.id.imgThumbnail).load(info.thumbnailUrl) {
            crossfade(true)
            transformations(RoundedCornersTransformation(8f))
            placeholder(R.color.flashyt_card_bg)
            error(R.color.flashyt_card_bg)
        }

        // Metadata
        view.findViewById<TextView>(R.id.tvTitle).text = info.title
        view.findViewById<TextView>(R.id.tvChannel).text = info.channelName

        // Quality cards
        val container = view.findViewById<LinearLayout>(R.id.qualityContainer)
        info.formats.forEachIndexed { index, format ->
            val card = layoutInflater.inflate(R.layout.item_quality_option, container, false)

            card.findViewById<TextView>(R.id.tvQualityLabel).text = format.label
            card.findViewById<TextView>(R.id.tvQualitySize).text = "~${format.estimatedSizeMb} MB"

            // Show the lightning bolt icon only on the primary (1080p) card
            card.findViewById<View>(R.id.ivQualityIcon).visibility =
                if (index == 0) View.VISIBLE else View.GONE

            // Highlight the first card (1080p) with the red accent
            if (index == 0) {
                (card as? MaterialCardView)?.let { mcv ->
                    mcv.setCardBackgroundColor(ContextCompat.getColor(this, R.color.red_tint_10))
                    mcv.strokeWidth = 2
                    mcv.strokeColor = ContextCompat.getColor(this, R.color.flashyt_red)
                }
            }

            card.setOnClickListener {
                sheet.dismiss()
                startDownload(url, format)
                finish()
            }
            container.addView(card)
        }

        sheet.setOnCancelListener { finish() }
        sheet.behavior.peekHeight = resources.displayMetrics.heightPixels
        sheet.behavior.state = BottomSheetBehavior.STATE_EXPANDED
        sheet.show()
        currentSheet = sheet
    }

    // -----------------------------------------------------------------------
    // Download start
    // -----------------------------------------------------------------------

    private fun startDownload(url: String, format: VideoFormat) {
        Intent(this, DownloadService::class.java).apply {
            putExtra("url", url)
            putExtra("format_label", format.label)
            putExtra("is_audio_only", format.isAudioOnly)
            putExtra("height", format.height ?: 0)
        }.also { startForegroundService(it) }
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    private fun makeSheet() = BottomSheetDialog(this, R.style.ThemeOverlay_FlashYT_BottomSheet)

    private fun dismissAndToast(message: String) {
        currentSheet?.dismiss()
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
        finish()
    }
}
