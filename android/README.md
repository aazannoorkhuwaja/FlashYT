# FlashYT Android

Share any YouTube video → select quality → download. No account, no server, no browser switch.

## How it works

1. Open YouTube → find any video → tap **Share** → select **FlashYT** from the share sheet.
2. A quality picker appears with the video thumbnail, title, and 4 options.
3. Tap a quality. FlashYT immediately starts a background download.
4. A notification shows live progress. Tap **Open File** when done.

Everything runs locally on-device using a bundled `yt-dlp` binary and `ffmpeg-kit`.

---

## Build locally

### Prerequisites
- Android Studio Ladybug (2024.2+) or JDK 17 + Android SDK
- `yt-dlp_linux_aarch64` binary downloaded to `app/src/main/assets/yt-dlp`

### First-time binary setup
```bash
mkdir -p app/src/main/assets
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux_aarch64 \
  -o app/src/main/assets/yt-dlp
```
> `ffmpeg` is **not** bundled manually — it comes automatically from the `ffmpeg-kit-full` Gradle dependency.

### Build debug APK
```bash
chmod +x gradlew
./gradlew :app:assembleDebug
```

Output: `app/build/outputs/apk/debug/app-debug.apk`

### Install on device
```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

---

## CI (GitHub Actions)

Every push to the `android/main` branch automatically:
1. Downloads the latest `yt-dlp` ARM64 binary
2. Builds the debug APK via Gradle
3. Uploads it as a downloadable artifact: **FlashYT-v1.0.0-debug**

---

## Project structure

```
android/
├── app/src/main/
│   ├── AndroidManifest.xml       ← share intent filter, no launcher icon
│   ├── assets/
│   │   └── yt-dlp               ← ARM64 executable (download before build)
│   ├── kotlin/com/flashyt/app/
│   │   ├── ShareActivity.kt      ← share intent + quality picker bottom sheet
│   │   ├── DownloadService.kt    ← foreground service, yt-dlp subprocess
│   │   ├── BinaryManager.kt      ← copies + chmod yt-dlp; ffmpeg via ffmpeg-kit
│   │   ├── VideoInfoFetcher.kt   ← yt-dlp --dump-json, parses formats
│   │   └── FlashYTNotificationManager.kt ← progress + complete notifications
│   └── res/
│       ├── layout/               ← bottom_sheet_quality, item_quality_option, loading
│       ├── values/               ← colors, strings, themes (Kinetic Vault design)
│       └── drawable/             ← ic_flashyt bolt, ic_cancel
└── .github/workflows/android-build.yml
```

---

## Permissions

| Permission | Why |
|---|---|
| `INTERNET` | yt-dlp needs network to download |
| `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_DATA_SYNC` | Background download service |
| `POST_NOTIFICATIONS` | Progress + completion notifications (Android 13+) |
| `WRITE_EXTERNAL_STORAGE` (API ≤ 28 only) | Legacy storage for Android 9 |

---

## Design

The UI follows the **Kinetic Vault** design system:
- Deep black backgrounds (`#000000` / `#0A0A0A`)
- YouTube red (`#FF0000`) as accent
- No border lines — surfaces defined by background color contrast
- 32dp rounded top corners on bottom sheet
- 56dp touch targets on all interactive rows
