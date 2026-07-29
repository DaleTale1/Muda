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

## 🐙 Step-by-Step GitHub Upload Instructions

Follow these exact terminal commands to push your project up to a new GitHub repository:

### Step 1: Initialize Git Local Repository
Navigate to your project root folder and run:
```bash
git init
```

### Step 2: Configure Git User (If not already set)
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### Step 3: Check Status & Stage Files
Verify `.gitignore` is present so `downloads/` and `venv/` are excluded:
```bash
git status
```
Stage all project files:
```bash
git add .
```

### Step 4: Create Initial Commit
```bash
git commit -m "feat: initial commit for MuDa audio downloader tool"
```

### Step 5: Rename Default Branch to `main`
```bash
git branch -M main
```

### Step 6: Create Remote Repository & Push to GitHub

#### Option A: Using GitHub CLI (`gh`) - Recommended
```bash
# Login to GitHub CLI (if needed)
gh auth login

# Create public repository on GitHub and push code immediately
gh repo create MuDa --public --source=. --remote=origin --push
```

#### Option B: Via GitHub Website (Manual)
1. Go to [https://github.com/new](https://github.com/new).
2. Name your repository **`MuDa`**.
3. Leave "Initialize this repository with a README" **unchecked** (since we already created one).
4. Click **Create repository**.
5. Copy the repository URL (e.g. `https://github.com/username/MuDa.git`) and run in your terminal:
```bash
git remote add origin https://github.com/YOUR_USERNAME/MuDa.git
git push -u origin main
```

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for details.
