#!/usr/bin/env python3
"""
main.py
-------
Main entry point for the MuDa YouTube & Spotify Audio Downloader CLI tool.

Usage Examples:
    # Interactive mode (prompts for link)
    python main.py

    # Direct YouTube link download
    python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    # Direct Spotify playlist download with custom output folder & quality
    python main.py "https://open.spotify.com/playlist/37i9dQZF1DXcBWAOFi2Ppab" -o ./my_music -q 320
"""

import io
import sys
from pathlib import Path

# Ensure UTF-8 output encoding on Windows terminals to prevent 'charmap' codec errors
if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Ensure local package import works even if run from different directories
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from muda.cli import run_cli


def main() -> None:
    """
    Application main function. Wraps CLI execution in a try-except block
    to gracefully handle user cancellation (Ctrl+C / KeyboardInterrupt).
    """
    try:
        run_cli()
    except KeyboardInterrupt:
        print("\n\n[!] Download canceled by user. Exiting gracefully.")
        sys.exit(0)
    except Exception as err:
        print(f"\n[!] Critical Error: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
