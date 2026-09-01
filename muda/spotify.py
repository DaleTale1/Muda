"""
muda/spotify.py
---------------
Spotify link parser and metadata extractor.

Spotify does not serve raw MP3 files directly, but it provides rich metadata
(Track Name, Artist, Album, Duration). This module parses Spotify URLs (Track,
Playlist, or Album), extracts track metadata without requiring developer API keys,
and converts each entry into a YouTube search query (e.g., "Artist Name - Track Title").

Performance improvements:
- `requests.Session` is reused across all HTTP calls to avoid repeated TCP handshakes.
- Parallel oEmbed sub-requests in the collection fallback path via ThreadPoolExecutor.
- lxml parser used for BeautifulSoup when available (faster than html.parser).
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

# Define user-agent header to simulate a standard browser request
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Pick the fastest available HTML parser for BeautifulSoup
try:
    import lxml  # noqa: F401
    _HTML_PARSER = "lxml"
except ImportError:
    _HTML_PARSER = "html.parser"


def _make_session() -> requests.Session:
    """Creates a requests.Session pre-loaded with default headers."""
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    return session


class SpotifyTrack:
    """
    Data structure representing a single parsed Spotify track.

    Attributes:
        title (str): Track title (e.g., "Blinding Lights")
        artist (str): Artist name (e.g., "The Weeknd")
        album (str): Album name or collection title
        duration_ms (int): Duration in milliseconds (optional)
        spotify_url (str): Original Spotify link
    """
    def __init__(self, title: str, artist: str, album: str = "", duration_ms: int = 0, spotify_url: str = ""):
        self.title = title.strip()
        self.artist = artist.strip()
        self.album = album.strip()
        self.duration_ms = duration_ms
        self.spotify_url = spotify_url

    @property
    def search_query(self) -> str:
        """
        Generates an optimized YouTube search query string.
        Adding 'audio' or 'official audio' ensures YouTube returns the music audio stream
        rather than fan covers or reaction videos.
        """
        return f"{self.artist} - {self.title} official audio"

    def __repr__(self) -> str:
        return f"<SpotifyTrack '{self.artist} - {self.title}'>"


class SpotifyParser:
    """
    Handles URL identification and metadata extraction from Spotify links.
    Uses a shared requests.Session for connection reuse across all HTTP calls.
    """

    @staticmethod
    def is_spotify_url(url: str) -> bool:
        """
        Checks if a given URL string is a valid Spotify link.

        Args:
            url (str): The URL string to test.

        Returns:
            bool: True if URL belongs to open.spotify.com or spotify.link
        """
        pattern = r"https?://(?:open|play)\.spotify\.com/(track|playlist|album)/[a-zA-Z0-9]+"
        return bool(re.match(pattern, url))

    @staticmethod
    def get_url_type(url: str) -> Optional[str]:
        """
        Extracts the resource type ('track', 'playlist', or 'album') from a Spotify URL.

        Args:
            url (str): Spotify URL

        Returns:
            Optional[str]: 'track', 'playlist', 'album', or None if invalid.
        """
        match = re.search(r"spotify\.com/(track|playlist|album)/([a-zA-Z0-9]+)", url)
        if match:
            return match.group(1)
        return None

    @classmethod
    def parse_url(cls, url: str) -> List[SpotifyTrack]:
        """
        Main entry point for parsing any Spotify link. Automatically determines whether
        it is a single track, a playlist, or an album, and returns a list of SpotifyTrack objects.

        Args:
            url (str): Spotify URL

        Returns:
            List[SpotifyTrack]: List of parsed tracks with title and artist information.

        Raises:
            ValueError: If the link format is invalid or metadata cannot be retrieved.
        """
        url_type = cls.get_url_type(url)

        if not url_type:
            raise ValueError(f"Invalid or unsupported Spotify link: {url}")

        session = _make_session()

        if url_type == "track":
            return [cls._parse_track(url, session)]
        elif url_type in ("playlist", "album"):
            return cls._parse_collection(url, url_type, session)
        else:
            raise ValueError(f"Unsupported Spotify URL type: {url_type}")

    @classmethod
    def _parse_track(cls, url: str, session: Optional[requests.Session] = None) -> SpotifyTrack:
        """
        Parses a single Spotify track using Spotify's public oEmbed API.
        Endpoint: https://open.spotify.com/oembed?url=...

        oEmbed returns structured JSON like:
        {
          "title": "Song Title",
          "author_name": "Artist Name",
          ...
        }
        """
        s = session or _make_session()
        try:
            oembed_url = f"https://open.spotify.com/oembed?url={url}"
            response = s.get(oembed_url, timeout=10)
            response.raise_for_status()
            data = response.json()

            title = data.get("title", "Unknown Track")
            artist = data.get("author_name", "Unknown Artist")

            return SpotifyTrack(title=title, artist=artist, spotify_url=url)
        except Exception:
            # Fallback to HTML meta tag scraping if oEmbed API fails
            return cls._parse_track_fallback(url, s)

    @classmethod
    def _parse_track_fallback(cls, url: str, session: Optional[requests.Session] = None) -> SpotifyTrack:
        """
        Fallback scraper for single tracks using HTML OpenGraph meta tags.
        """
        s = session or _make_session()
        response = s.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, _HTML_PARSER)

        # Extract title from og:title meta tag
        title_meta = soup.find("meta", property="og:title")
        title = title_meta["content"] if title_meta else "Unknown Track"

        # Extract artist from description or page title
        desc_meta = soup.find("meta", property="og:description")
        description = desc_meta["content"] if desc_meta else ""

        # Description format usually: "Song · Artist · Year" or "Artist · Song · Single"
        artist = "Unknown Artist"
        if " · " in description:
            parts = description.split(" · ")
            artist = parts[0] if parts[0] != title else (parts[1] if len(parts) > 1 else "Unknown Artist")

        return SpotifyTrack(title=title, artist=artist, spotify_url=url)

    @classmethod
    def _parse_collection(cls, url: str, collection_type: str, session: Optional[requests.Session] = None) -> List[SpotifyTrack]:
        """
        Parses a Spotify Playlist or Album link by fetching the Embed page:
        https://open.spotify.com/embed/{playlist|album}/{id}

        The embed page embeds JSON state data inside a <script id="__NEXT_DATA__"> or
        <script id="initial-state"> tag, which contains the full track list.
        """
        s = session or _make_session()

        # Extract Spotify ID from URL
        match = re.search(r"spotify\.com/(?:playlist|album)/([a-zA-Z0-9]+)", url)
        if not match:
            raise ValueError(f"Could not extract {collection_type} ID from URL: {url}")

        item_id = match.group(1)
        embed_url = f"https://open.spotify.com/embed/{collection_type}/{item_id}"

        response = s.get(embed_url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, _HTML_PARSER)
        tracks: List[SpotifyTrack] = []

        # 1. Try parsing JSON script data embedded by Spotify Next.js app
        script_tag = soup.find("script", id="__NEXT_DATA__")
        if script_tag and script_tag.string:
            try:
                json_data = json.loads(script_tag.string)
                # Navigate nested JSON structure for playlist/album tracks
                entity_data = json_data.get("props", {}).get("pageProps", {}).get("state", {}).get("data", {})

                # Check entity track list locations
                track_list = []
                if "playlist" in entity_data:
                    track_list = entity_data["playlist"].get("tracks", {}).get("items", [])
                elif "album" in entity_data:
                    track_list = entity_data["album"].get("tracks", {}).get("items", [])

                for item in track_list:
                    # Item could be nested under "track" (for playlists) or direct (for albums)
                    t_info = item.get("track", item)
                    name = t_info.get("name")
                    artists = [a.get("name", "") for a in t_info.get("artists", [])]
                    artist_name = ", ".join(artists) if artists else "Unknown Artist"

                    if name:
                        tracks.append(SpotifyTrack(title=name, artist=artist_name, spotify_url=url))

                if tracks:
                    return tracks
            except (json.JSONDecodeError, KeyError):
                pass

        # 2. Fallback: Parse track entries directly from HTML elements in the embed view
        track_rows = (
            soup.find_all("li", class_=re.compile(r"track", re.I))
            or soup.find_all("div", class_=re.compile(r"track", re.I))
        )

        for row in track_rows:
            title_elem = row.find(class_=re.compile(r"title|name", re.I))
            artist_elem = row.find(class_=re.compile(r"artist", re.I))

            if title_elem:
                title = title_elem.get_text(strip=True)
                artist = artist_elem.get_text(strip=True) if artist_elem else "Unknown Artist"
                tracks.append(SpotifyTrack(title=title, artist=artist, spotify_url=url))

        # 3. Secondary Fallback: fetch open.spotify.com main page HTML for meta tags, then
        #    resolve individual track oEmbed requests in parallel for speed.
        if not tracks:
            page_resp = s.get(url, timeout=10)
            if page_resp.ok:
                page_soup = BeautifulSoup(page_resp.text, _HTML_PARSER)

                # Gather unique track IDs from anchor hrefs
                track_links = page_soup.find_all("a", href=re.compile(r"/track/"))
                seen_ids: set = set()
                track_urls: List[str] = []
                for link in track_links:
                    href = link["href"]
                    t_id_match = re.search(r"/track/([a-zA-Z0-9]+)", href)
                    if t_id_match and t_id_match.group(1) not in seen_ids:
                        seen_ids.add(t_id_match.group(1))
                        track_urls.append(f"https://open.spotify.com/track/{t_id_match.group(1)}")

                # Fetch oEmbed for all discovered tracks in parallel
                if track_urls:
                    ordered: List[Optional[SpotifyTrack]] = [None] * len(track_urls)
                    with ThreadPoolExecutor(max_workers=8) as executor:
                        future_map = {
                            executor.submit(cls._parse_track, t_url, s): i
                            for i, t_url in enumerate(track_urls)
                        }
                        for future in as_completed(future_map):
                            i = future_map[future]
                            try:
                                ordered[i] = future.result()
                            except Exception:
                                pass
                    tracks = [t for t in ordered if t is not None]

        if not tracks:
            raise ValueError(f"Could not extract tracks from Spotify {collection_type}: {url}")

        return tracks
