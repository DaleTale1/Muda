"""
muda/utils.py
-------------
Utility and helper functions for MuDa downloader:
1. FFmpeg & FFprobe system dependency verification.
2. Safe filename & path sanitization for cross-platform support (Windows, macOS, Linux).
3. Network connection verification.
4. JSON configuration file manager.
"""

import json
import os
import re
import shutil
import socket
from pathlib import Path
from typing import Dict, Any, Tuple


def check_ffmpeg() -> Tuple[bool, bool]:
    """
    Checks whether 'ffmpeg' and 'ffprobe' executables are installed and accessible
    in the system's PATH environment variable.

    `yt-dlp` relies on FFmpeg to extract audio from video streams and convert it
    into target formats like MP3, AAC, or FLAC.

    Returns:
        Tuple[bool, bool]: (is_ffmpeg_installed, is_ffprobe_installed)
    """
    # shutil.which searches for executable files in directories listed in os.environ["PATH"]
    ffmpeg_available = shutil.which("ffmpeg") is not None
    ffprobe_available = shutil.which("ffprobe") is not None
    
    return ffmpeg_available, ffprobe_available


def sanitize_filename(name: str) -> str:
    """
    Sanitizes a string so that it can safely be used as a filename across all OSs.
    Replaces reserved filesystem characters (< > : " / \\ | ? *) with an underscore.

    Args:
        name (str): The raw track title or playlist name.

    Returns:
        str: A clean, safe filename.
    """
    if not name:
        return "unnamed_track"
    
    # Remove invalid characters for Windows / POSIX file systems
    clean_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    
    # Remove trailing periods or spaces which cause issues in Windows file systems
    clean_name = clean_name.strip('. ')
    
    # Ensure length doesn't exceed common OS filename limit (255 chars)
    if len(clean_name) > 200:
        clean_name = clean_name[:200]
        
    return clean_name or "track"


def check_internet_connection(host: str = "8.8.8.8", port: int = 53, timeout: float = 3.0) -> bool:
    """
    Quickly verifies network connection by opening a socket to Google's public DNS server.

    Args:
        host (str): Remote host IP to ping via socket. Default is Google Public DNS (8.8.8.8).
        port (int): Port to attempt socket connection. Default is 53 (DNS).
        timeout (float): Connection timeout in seconds.

    Returns:
        bool: True if internet is reachable, False otherwise.
    """
    try:
        # Create a TCP socket and attempt connection
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except OSError:
        return False


def load_config(config_path: Path) -> Dict[str, Any]:
    """
    Loads JSON configuration settings from disk. If the file does not exist,
    returns default configuration values.

    Args:
        config_path (Path): Path object pointing to default_config.json.

    Returns:
        Dict[str, Any]: Dictionary containing configuration options.
    """
    default_settings = {
        "output_dir": "./downloads",
        "audio_format": "mp3",
        "audio_quality": "320",
        "max_concurrent_downloads": 3,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    if not config_path.exists():
        return default_settings

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Merge user config with defaults so missing keys don't cause KeyErrors
            default_settings.update(data)
            return default_settings
    except (json.JSONDecodeError, OSError):
        # Fallback gracefully if config file is corrupted
        return default_settings
