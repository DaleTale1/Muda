# 🎵 MuDa - YouTube & Spotify Audio Downloader CLI

**MuDa** (Music & Audio Downloader) is a clean, production-ready, interactive command-line tool built with Python, `yt-dlp`, and `rich`. It allows you to download high-quality MP3 audio from any **YouTube video/playlist** or **Spotify track/playlist/album**.

---

## ✨ Features

- 🎧 **YouTube & Spotify Support**: Parses single track links, full playlists, and albums.
- ⚡ **No Spotify API Keys Required**: Seamlessly extracts track titles and artists using Spotify metadata APIs & web page embeds.
- 🎼 **High-Quality Audio Extraction**: Uses `yt-dlp` and `FFmpeg` to convert streams into up to 320kbps MP3s.
- 🎨 **Rich Terminal Interface**: Beautiful ASCII banner, real-time progress bars, transfer speeds, and summary tables.
- 🛠️ **System Dependency Checks**: Automatically detects if `FFmpeg` is missing and provides OS-specific setup guidance.
- 🔁 **Smart Skip**: Prevents re-downloading tracks that already exist in your output directory.
- 📁 **Configurable Output**: Customize output folders, bitrates (128k–320k), parallel workers, and format settings.
- ⚡ **Parallel Playlist Downloads**: Spotify playlists download multiple tracks simultaneously for much faster completion.
- 🔄 **Auto Fallback**: Automatically rotates YouTube client profiles if a 403 / bot-block error is encountered.

---

## 📁 Project Structure

```
MuDa/
├── muda/
│   ├── __init__.py        # Package exports and version info
│   ├── cli.py             # Rich CLI rendering, progress bars, and argument parsing
│   ├── downloader.py      # Core download engine leveraging yt-dlp Python API
│   ├── spotify.py         # Spotify link parser (Tracks, Playlists, Albums)
│   └── utils.py           # Dependency verification (FFmpeg), filename sanitization
├── config/
│   └── default_config.json# Default settings (output dir, audio quality, bitrates)
├── downloads/             # Destination folder for downloaded MP3 files
├── main.py                # Main script entry point
├── requirements.txt       # Dependencies (yt-dlp, rich, requests, beautifulsoup4, lxml)
├── .gitignore             # Git ignore file for virtual envs and output files
├── LICENSE                # MIT License
└── README.md              # Documentation and GitHub deployment guide
```

---

## ⚙️ Prerequisites & Installation

### 1. Install FFmpeg
`yt-dlp` requires **FFmpeg** to extract and convert audio to MP3.

- **Windows** (via WinGet):
  ```bash
  winget install ffmpeg
  ```
- **macOS** (via Homebrew):
  ```bash
  brew install ffmpeg
  ```
- **Linux** (Debian/Ubuntu):
  ```bash
  sudo apt update && sudo apt install ffmpeg -y
  ```
- **Android** (Termux):
  ```bash
  pkg update && pkg install ffmpeg python git -y
  ```

### 2. Clone / Download & Install Dependencies

```bash
# Navigate to project directory
cd MuDa

# (Optional) Create and activate a Python virtual environment
python -m venv venv

# On Windows (PowerShell / CMD):
.\venv\Scripts\activate

# On macOS / Linux / Termux:
source venv/bin/activate

# Install required Python packages
pip install -r requirements.txt
```

> [!TIP]
> `lxml` is installed automatically and gives MuDa a 2–5× boost in Spotify metadata parsing speed.

---

## 🚀 Usage Guide

### Mode 1: Interactive Prompt
Launch without arguments — MuDa will prompt you to paste a link:

```bash
python main.py
```

### Mode 2: Direct Command Line Arguments

```bash
# Download a single YouTube video:
python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Download a full YouTube playlist:
python main.py "https://www.youtube.com/playlist?list=PLxxxxxxx"

# Download a Spotify track:
python main.py "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"

# Download a full Spotify playlist to a custom folder at 320kbps:
python main.py "https://open.spotify.com/playlist/37i9dQZF1DXcBWAOFi2Ppab" -o ./my_playlist -q 320

# Download a Spotify Album:
python main.py "https://open.spotify.com/album/1A2HoYik7p2Exb25LWenY3"
```

### All Available Options

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `url` | — | *(prompted)* | YouTube or Spotify URL to download |
| `--output` | `-o` | `./downloads` | Folder to save MP3 files into |
| `--quality` | `-q` | `320` | Audio bitrate: `128`, `192`, `256`, or `320` kbps |
| `--workers` | `-w` | `4` | Parallel download threads for Spotify playlists |
| `--oauth` | — | off | Authenticate with YouTube via device login (helps bypass strict bot blocks) |
| `--cookies` | — | none | Path to a `cookies.txt` file for YouTube session auth |

**Examples:**

```bash
# Download a Spotify playlist using 8 parallel threads (faster for large playlists):
python main.py "https://open.spotify.com/playlist/..." -w 8

# Download at 192kbps to a specific folder:
python main.py "https://www.youtube.com/watch?v=..." -q 192 -o ~/Music

# Use a cookies file to bypass age-restrictions or bot blocks:
python main.py "https://www.youtube.com/watch?v=..." --cookies cookies.txt

# Authenticate via YouTube OAuth (device login flow):
python main.py "https://www.youtube.com/watch?v=..." --oauth
```

> [!NOTE]
> For Spotify playlists, MuDa searches YouTube for each track and downloads the best audio match.
> The `--workers` flag controls how many tracks download in parallel (default: 4).
> Increase it on fast connections, lower it if you hit rate limits.

---

## 📱 Termux (Android) Setup & Usage Guide

You can run **MuDa** directly on your Android device using [Termux](https://termux.dev/).

> [!TIP]
> Install Termux via **F-Droid** or GitHub Releases — the Google Play Store version is outdated.

### Step 1: Grant Storage Access
Allow Termux to access phone storage so downloaded MP3s save to your device:
```bash
termux-setup-storage
```

### Step 2: Update Packages & Install System Tools
```bash
pkg update && pkg upgrade -y
pkg install python ffmpeg git -y
```

### Step 3: Clone Repository & Install Python Packages
```bash
git clone https://github.com/YOUR_USERNAME/MuDa.git
cd MuDa
pip install -r requirements.txt
```

### Step 4: Run MuDa on Termux

- **Interactive Mode**:
  ```bash
  python main.py
  ```

- **Save to Phone's Music folder (`/sdcard/Music`)**:
  ```bash
  python main.py "https://open.spotify.com/playlist/..." -o ~/storage/music
  ```

- **Save to Phone's Downloads folder (`/sdcard/Download`)**:
  ```bash
  python main.py "https://www.youtube.com/watch?v=..." -o ~/storage/downloads
  ```

- **Download a large Spotify playlist fast** (8 parallel threads):
  ```bash
  python main.py "https://open.spotify.com/playlist/..." -o ~/storage/music -w 8
  ```

> [!NOTE]
> MuDa automatically uses the **iOS YouTube client** as its first download strategy, which avoids
> the 403 Forbidden / Play Integrity errors that affect Android-based clients.
> If a 403 still occurs, MuDa will automatically retry with alternative client profiles.

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| `HTTP Error 403` | MuDa auto-retries with fallback clients. If it persists, try `--cookies cookies.txt` or `--oauth` |
| `FFmpeg not found` | Install FFmpeg for your OS (see Prerequisites above) and restart your terminal |
| Slow Spotify playlist | Increase workers: `-w 8` or `-w 10` |
| Track not found | The YouTube search found no match — try searching with a more specific query or a different Spotify link |
| `No module named 'yt_dlp'` | Run `pip install -r requirements.txt` inside the project folder |

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for details.
