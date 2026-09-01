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


FALLBACK_CLIENT_PROFILES: List[List[str]] = [
    # Profile 1: Multi-client standard fallback
    ["android_vr", "web_embedded", "mweb", "ios", "tv_embedded"],
    # Profile 2: iOS client (bypasses Android Play Integrity & Web BotGuard challenges)
    ["ios", "mweb"],
    # Profile 3: Smart TV Embedded client (permissive streaming protocol)
    ["tv_embedded", "tv"],
    # Profile 4: Creator clients
    ["android_creator", "web_creator"],
    # Profile 5: Lightweight mobile web
    ["mweb"],
]


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
    Includes automated fallback client retry mechanisms against HTTP 403 / BotGuard blocks.

    Args:
        output_dir (str): Folder path where MP3 files will be saved.
        audio_quality (str): Bitrate for MP3 conversion (e.g., "320", "256", "192").
        delay (float): Delay in seconds between track requests to avoid YouTube rate limiting.
        progress_callback (Optional[Callable]): Callback function receiving progress dicts.
        use_oauth (bool): Whether to authenticate via YouTube OAuth device login.
        cookies (Optional[str]): Path to a cookies.txt file for session authentication.
    """

    def __init__(
        self,
        output_dir: str = "./downloads",
        audio_quality: str = "320",
        delay: float = 1.5,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        use_oauth: bool = False,
        cookies: Optional[str] = None,
    ):
        self.output_dir = Path(output_dir).resolve()
        self.audio_quality = str(audio_quality)
        self.delay = float(delay)
        self.progress_callback = progress_callback
        self.use_oauth = use_oauth
        self.cookies = cookies

        # Ensure output folder exists on disk
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _is_403_or_bot_block(err: Exception) -> bool:
        """
        Determines whether a raised exception is an HTTP 403 Forbidden,
        Play Integrity challenge, or bot detection block.
        """
        err_msg = str(err).lower()
        keywords = [
            "403",
            "forbidden",
            "sign in to confirm",
            "bot",
            "confirm you",
            "sabr",
            "unable to download video data",
            "http error 403",
        ]
        return any(kw in err_msg for kw in keywords)

    def _get_yt_dlp_options(
        self,
        custom_filename: Optional[str] = None,
        client_profile: Optional[List[str]] = None,
        force_oauth: bool = False,
    ) -> Dict[str, Any]:
        """
        Constructs the configuration dictionary passed to `yt_dlp.YoutubeDL()`.
        """
        # Determine output filename template
        if custom_filename:
            safe_name = sanitize_filename(custom_filename)
            out_template = str(self.output_dir / f"{safe_name}.%(ext)s")
        else:
            out_template = str(self.output_dir / "%(title)s.%(ext)s")

        active_clients = client_profile or FALLBACK_CLIENT_PROFILES[0]

        ydl_opts: Dict[str, Any] = {
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
            "extractor_args": {
                "youtube": {
                    "player_client": active_clients,
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

        if self.use_oauth or force_oauth:
            ydl_opts["username"] = "oauth"
            ydl_opts["password"] = ""

        if self.cookies:
            ydl_opts["cookiefile"] = self.cookies

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
        Searches YouTube for a single SpotifyTrack using `ytsearch1:` and downloads the best audio match,
        with automatic fallback retries across client profiles if HTTP 403 occurs.

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

        last_error = ""

        # Try download with primary and fallback client profiles if 403 occurs
        for idx, client_profile in enumerate(FALLBACK_CLIENT_PROFILES):
            ydl_opts = self._get_yt_dlp_options(
                custom_filename=f"{track.artist} - {track.title}",
                client_profile=client_profile,
            )

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
                last_error = str(err)
                if self._is_403_or_bot_block(err) and idx < len(FALLBACK_CLIENT_PROFILES) - 1:
                    continue
                break

        return DownloadResult(
            title=f"{track.artist} - {track.title}",
            status="failed",
            error_message=last_error,
        )

    def download_youtube_url(self, yt_url: str) -> List[DownloadResult]:
        """
        Downloads audio directly from a YouTube video URL or playlist URL,
        automatically rotating fallback client profiles upon 403 Forbidden errors.

        Args:
            yt_url (str): YouTube video link or playlist link.

        Returns:
            List[DownloadResult]: Results of all video items.
        """
        last_error = ""

        for idx, client_profile in enumerate(FALLBACK_CLIENT_PROFILES):
            results: List[DownloadResult] = []
            ydl_opts = self._get_yt_dlp_options(client_profile=client_profile)

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
                            raw_path = ydl.prepare_filename(entry)
                            expected_path = str(Path(raw_path).with_suffix(".mp3"))
                            exists = os.path.exists(expected_path)
                            
                            results.append(
                                DownloadResult(
                                    title=title,
                                    status="success" if exists else "skipped",
                                    filepath=expected_path if exists else "",
                                )
                            )
                    else:
                        # Single video download
                        title = info_dict.get("title", "YouTube Audio")
                        ydl.download([yt_url])
                        
                        raw_path = ydl.prepare_filename(info_dict)
                        expected_path = str(Path(raw_path).with_suffix(".mp3"))
                        exists = os.path.exists(expected_path)

                        results.append(
                            DownloadResult(
                                title=title,
                                status="success" if exists else "skipped",
                                filepath=expected_path if exists else "",
                            )
                        )
                    return results
            except Exception as err:
                last_error = str(err)
                if self._is_403_or_bot_block(err) and idx < len(FALLBACK_CLIENT_PROFILES) - 1:
                    continue
                return [DownloadResult(title=yt_url, status="failed", error_message=last_error)]

        return [DownloadResult(title=yt_url, status="failed", error_message=last_error)]
