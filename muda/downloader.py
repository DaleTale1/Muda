"""
muda/downloader.py
------------------
Core downloader module utilizing `yt-dlp` for YouTube audio extraction and conversion.

Key Features:
1. Downloads direct YouTube video and playlist links.
2. Performs YouTube search queries (`ytsearch1:...`) for Spotify tracks.
3. Automatically triggers FFmpeg post-processing to extract high-quality MP3 audio.
4. Provides real-time progress callbacks for CLI visualization.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import yt_dlp

from muda.spotify import SpotifyTrack, SpotifyParser
from muda.utils import sanitize_filename


class DownloadResult:
    """
    Data model representing the outcome of a track download operation.

    Attributes:
        title (str): Track or video title.
        status (str): Outcome state - 'success', 'failed', or 'skipped'.
        filepath (str): Absolute file path of the downloaded MP3.
        error_message (str): Details if status is 'failed'.
    """
    def __init__(self, title: str, status: str, filepath: str = "", error_message: str = ""):
        self.title = title
        self.status = status  # "success", "failed", "skipped"
        self.filepath = filepath
        self.error_message = error_message

    def __repr__(self) -> str:
        return f"<DownloadResult title='{self.title}' status='{self.status}'>"


class AudioDownloader:
    """
    Wraps yt-dlp Python API to manage audio downloads and conversions.

    Args:
        output_dir (str): Folder path where MP3 files will be saved.
        audio_quality (str): Bitrate for MP3 conversion (e.g., "320", "256", "192").
        delay (float): Delay in seconds between track requests to avoid YouTube rate limiting.
        progress_callback (Optional[Callable]): Callback function receiving progress dicts.
    """

    def __init__(
        self,
        output_dir: str = "./downloads",
        audio_quality: str = "320",
        delay: float = 1.5,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.output_dir = Path(output_dir).resolve()
        self.audio_quality = str(audio_quality)
        self.delay = float(delay)
        self.progress_callback = progress_callback

        # Ensure output folder exists on disk
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_yt_dlp_options(self, custom_filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Constructs the configuration dictionary passed to `yt_dlp.YoutubeDL()`.

        Options explained:
        - `format`: Selects the best available audio stream.
        - `postprocessors`: Invokes FFmpeg to extract audio and encode it to MP3.
        - `outtmpl`: File output path template.
        - `quiet` / `no_warnings`: Suppresses verbose stdout so Rich CLI stays clean.
        - `progress_hooks`: List of functions called by yt-dlp during download progress.
        - `sleep_interval` / `max_sleep_interval`: Adds random delay between requests to bypass YouTube rate limits.
        - `retries`: Retries failed HTTP requests automatically.

        Returns:
            Dict[str, Any]: Dictionary of yt-dlp options.
        """
        # Determine output filename template
        if custom_filename:
            safe_name = sanitize_filename(custom_filename)
            out_template = str(self.output_dir / f"{safe_name}.%(ext)s")
        else:
            out_template = str(self.output_dir / "%(title)s.%(ext)s")

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": out_template,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": self.audio_quality,
                }
            ],
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "ignoreerrors": True,
            "extract_flat": False,
            # Prevent re-downloading if file already exists in destination folder
            "nooverwrites": True,
            # Automatic Retries for temporary rate limits or dropped connections
            "retries": 10,
            "fragment_retries": 10,
            "socket_timeout": 20,
            # Rate-limiting protection: Introduce delays between requests
            "sleep_interval": int(self.delay),
            "max_sleep_interval": int(self.delay + 2.0),
            "sleep_interval_requests": 1,
            # Fix YouTube HTTP 403 & Error 152 by using fallback player clients
            # Combining android_vr, web_embedded, mweb, and tv_embedded avoids SABR rate limits.
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_vr", "web_embedded", "mweb", "ios", "tv_embedded"],
                }
            },
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-us,en;q=0.5",
            },
        }

        # Attach custom progress callback if provided
        if self.progress_callback:
            ydl_opts["progress_hooks"] = [self.progress_callback]

        return ydl_opts

    def download_url(self, url: str) -> List[DownloadResult]:
        """
        Main entry point for downloading audio from a URL string.
        Determines whether the URL is a Spotify link or a YouTube link, then routes appropriately.

        Args:
            url (str): YouTube video/playlist link or Spotify track/playlist/album link.

        Returns:
            List[DownloadResult]: List of results for each processed track.
        """
        url = url.strip()

        # Check if the URL is a Spotify link
        if SpotifyParser.is_spotify_url(url):
            return self.download_spotify_url(url)
        else:
            # Assume YouTube link or direct media URL
            return self.download_youtube_url(url)

    def download_spotify_url(self, spotify_url: str) -> List[DownloadResult]:
        """
        Parses Spotify link metadata and downloads matching tracks via YouTube search.

        Args:
            spotify_url (str): Spotify track, playlist, or album link.

        Returns:
            List[DownloadResult]: Results of all parsed tracks.
        """
        results: List[DownloadResult] = []

        try:
            tracks: List[SpotifyTrack] = SpotifyParser.parse_url(spotify_url)
        except Exception as e:
            return [DownloadResult(title=spotify_url, status="failed", error_message=str(e))]

        for track in tracks:
            result = self.download_spotify_track(track)
            results.append(result)

        return results

    def download_spotify_track(self, track: SpotifyTrack) -> DownloadResult:
        """
        Searches YouTube for a single SpotifyTrack using `ytsearch1:` and downloads the best audio match.

        Args:
            track (SpotifyTrack): Parsed Spotify track info.

        Returns:
            DownloadResult: Download outcome.
        """
        query = f"ytsearch1:{track.search_query}"
        expected_filename = f"{sanitize_filename(f'{track.artist} - {track.title}')}.mp3"
        expected_filepath = self.output_dir / expected_filename

        # Skip if file already exists in downloads folder
        if expected_filepath.exists():
            return DownloadResult(
                title=f"{track.artist} - {track.title}",
                status="skipped",
                filepath=str(expected_filepath),
                error_message="File already exists in download folder.",
            )

        ydl_opts = self._get_yt_dlp_options(custom_filename=f"{track.artist} - {track.title}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(query, download=True)
                
                if not info_dict or "entries" not in info_dict or not info_dict["entries"]:
                    return DownloadResult(
                        title=f"{track.artist} - {track.title}",
                        status="failed",
                        error_message="No YouTube search result found for track query.",
                    )

                return DownloadResult(
                    title=f"{track.artist} - {track.title}",
                    status="success",
                    filepath=str(expected_filepath),
                )
        except Exception as err:
            return DownloadResult(
                title=f"{track.artist} - {track.title}",
                status="failed",
                error_message=str(err),
            )

    def download_youtube_url(self, yt_url: str) -> List[DownloadResult]:
        """
        Downloads audio directly from a YouTube video URL or playlist URL.

        Args:
            yt_url (str): YouTube video link or playlist link.

        Returns:
            List[DownloadResult]: Results of all video items.
        """
        results: List[DownloadResult] = []
        ydl_opts = self._get_yt_dlp_options()

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract metadata first to inspect whether it's a playlist or single video
                info_dict = ydl.extract_info(yt_url, download=False)
                
                if not info_dict:
                    return [DownloadResult(title=yt_url, status="failed", error_message="Could not extract video metadata.")]

                # Check if payload is a playlist (contains 'entries' key)
                if "entries" in info_dict and info_dict["entries"]:
                    entries = [e for e in info_dict["entries"] if e is not None]
                    
                    # Now download full playlist
                    ydl.download([yt_url])

                    for entry in entries:
                        title = entry.get("title", "Unknown Title")
                        safe_title = sanitize_filename(title)
                        expected_path = str(self.output_dir / f"{safe_title}.mp3")
                        
                        results.append(
                            DownloadResult(
                                title=title,
                                status="success" if os.path.exists(expected_path) else "skipped",
                                filepath=expected_path if os.path.exists(expected_path) else "",
                            )
                        )
                else:
                    # Single video download
                    title = info_dict.get("title", "YouTube Audio")
                    ydl.download([yt_url])
                    
                    safe_title = sanitize_filename(title)
                    expected_path = str(self.output_dir / f"{safe_title}.mp3")

                    results.append(
                        DownloadResult(
                            title=title,
                            status="success" if os.path.exists(expected_path) else "skipped",
                            filepath=expected_path if os.path.exists(expected_path) else "",
                        )
                    )
        except Exception as err:
            results.append(DownloadResult(title=yt_url, status="failed", error_message=str(err)))

        return results
