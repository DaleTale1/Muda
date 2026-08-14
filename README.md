# 🎵 MuDa - YouTube & Spotify Audio Downloader CLI

**MuDa** (Music & Audio Downloader) is a clean, production-ready, interactive command-line tool built with Python, `yt-dlp`, and `rich`. It allows you to download high-quality MP3 audio from any **YouTube video/playlist** or **Spotify track/playlist/album**.

---

## ✨ Features

- 🎧 **YouTube & Spotify Support**: Parses single track links, full playlists, and albums.
- ⚡ **No Spotify API Keys Required**: Seamlessly extracts track titles and artists using Spotify metadata APIs & web page embeds.
- 🎼 **High-Quality Audio Extraction**: Uses `yt-dlp` and `FFmpeg` to convert streams into 320kbps MP3s.
- 🎨 **Rich Terminal Interface**: Beautiful ASCII banner, real-time progress bars, transfer speeds, and summary tables.
- 🛠️ **System Dependency Checks**: Automatically detects if `FFmpeg` is missing and provides OS-specific setup guidance.
- 🔁 **Smart Skip**: Prevents re-downloading tracks that already exist in your output directory.
- 📁 **Configurable Output**: Customize output folders, bitrates (128k to 320k), and format settings.

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
├── requirements.txt       # Dependencies (yt-dlp, rich, requests, beautifulsoup4)
├── .gitignore             # Git ignore file for virtual envs and output files
├── LICENSE                # MIT License
└── README.md              # Documentation and GitHub deployment guide
```

---

## ⚙️ Prerequisites & Installation

### 1. Install FFmpeg
`yt-dlp` requires **FFmpeg** to extract and convert audio to MP3.

- **Windows** (via WinGet or Chocolatey):
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

# On macOS / Linux:
source venv/bin/activate

# Install required Python packages
pip install -r requirements.txt
```

---

## 📱 Termux (Android) Setup & Usage Guide

You can easily set up and run **MuDa** directly on your Android device using [Termux](https://termux.dev/).

> [!TIP]
> It is recommended to install Termux via **F-Droid** or GitHub Releases instead of the outdated Google Play Store version.

### Step 1: Grant Storage Access
Allow Termux to access phone storage so downloaded MP3s save directly to your Android device storage:
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

- **Save directly to Phone's Music folder (`/sdcard/Music`)**:
  ```bash
  python main.py "https://open.spotify.com/playlist/..." -o ~/storage/music
  ```

- **Save directly to Phone's Downloads folder (`/sdcard/Download`)**:
  ```bash
  python main.py "https://www.youtube.com/watch?v=..." -o ~/storage/downloads
  ```


---

## 🚀 Usage Guide

### Mode 1: Interactive Prompt
Simply launch `main.py` without arguments, and MuDa will prompt you to paste a link:

```bash
python main.py
```

### Mode 2: Direct Command Line Arguments

```bash
# Download a single YouTube video:
python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Download a full Spotify playlist to a custom folder with 320kbps quality:
python main.py "https://open.spotify.com/playlist/37i9dQZF1DXcBWAOFi2Ppab" -o ./my_playlist -q 320

# Download a Spotify Album:
python main.py "https://open.spotify.com/album/1A2HoYik7p2Exb25LWenY3"
```

---


## 📜 License

Distributed under the MIT License. See `LICENSE` for details.

