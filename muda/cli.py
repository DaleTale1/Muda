"""
muda/cli.py
-----------
Interactive Command Line Interface (CLI) for MuDa audio downloader.

Uses `rich` for colored terminal output, ASCII banners, tables, progress bars,
and status panels.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from muda import __version__
from muda.downloader import AudioDownloader, DownloadResult
from muda.spotify import SpotifyParser
from muda.utils import check_ffmpeg, check_internet_connection, load_config

# Initialize Rich Console instance for pretty terminal rendering
console = Console()


def print_banner() -> None:
    """
    Renders an ASCII art banner and application summary to the terminal.
    """
    banner_text = Text()
    banner_text.append("   __  ___    ___      ___ \n", style="bold cyan")
    banner_text.append("  /  |/  /_ _|   \\ ___/ _ \\\n", style="bold cyan")
    banner_text.append(" / /|_/ / _` | |) / _ \\ __/\n", style="bold blue")
    banner_text.append("/_/  /_/\\__,_|___/\\___/_/  \n", style="bold magenta")
    banner_text.append(f"  YouTube & Spotify Audio Downloader v{__version__}\n", style="italic white")

    console.print(Panel(banner_text, border_style="cyan", expand=False))


def display_ffmpeg_warning() -> None:
    """
    Displays a prominent warning panel if FFmpeg is missing on the host machine,
    along with OS-specific terminal commands to install it.
    """
    warning_content = Text()
    warning_content.append("⚠️  FFmpeg Not Found in System PATH!\n\n", style="bold red")
    warning_content.append(
        "MuDa uses FFmpeg to extract audio and convert streams into high-quality MP3 files.\n"
        "Without FFmpeg, downloads may fail or result in raw video files.\n\n",
        style="white",
    )
    warning_content.append("How to Install FFmpeg:\n", style="bold yellow")
    warning_content.append("  • Windows: ", style="bold white")
    warning_content.append("winget install ffmpeg  ", style="green")
    warning_content.append("(or download from https://ffmpeg.org/download.html)\n", style="dim white")
    warning_content.append("  • macOS:   ", style="bold white")
    warning_content.append("brew install ffmpeg\n", style="green")
    warning_content.append("  • Linux:   ", style="bold white")
    warning_content.append("sudo apt update && sudo apt install ffmpeg\n\n", style="green")
    warning_content.append("After installing, restart your terminal and run MuDa again.", style="italic cyan")

    console.print(Panel(warning_content, title="Dependency Warning", border_style="red"))


def display_summary_table(results: List[DownloadResult], output_dir: str) -> None:
    """
    Renders a Rich Table summarizing all processed tracks and their download status.

    Args:
        results (List[DownloadResult]): List of DownloadResult objects.
        output_dir (str): Destination folder where files were saved.
    """
    table = Table(title="Download Summary", show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Track / Video Title", style="cyan", min_width=30)
    table.add_column("Status", justify="center", width=12)
    table.add_column("Details", style="dim white")

    success_count = 0
    skipped_count = 0
    failed_count = 0

    for idx, res in enumerate(results, start=1):
        if res.status == "success":
            status_cell = "[bold green]Success[/bold green]"
            details_cell = res.filepath or "Downloaded"
            success_count += 1
        elif res.status == "skipped":
            status_cell = "[bold yellow]Skipped[/bold yellow]"
            details_cell = res.error_message or "File already exists"
            skipped_count += 1
        else:
            status_cell = "[bold red]Failed[/bold red]"
            details_cell = res.error_message or "Download error"
            failed_count += 1

        table.add_row(str(idx), res.title, status_cell, details_cell)

    console.print()
    console.print(table)

    # Print summary statistics bar
    stats_text = (
        f"[bold green]Completed: {success_count}[/bold green] | "
        f"[bold yellow]Skipped: {skipped_count}[/bold yellow] | "
        f"[bold red]Failed: {failed_count}[/bold red] | "
        f"[bold blue]Location: {Path(output_dir).resolve()}[/bold blue]"
    )
    console.print(Panel(stats_text, title="Stats", border_style="blue"))


def run_cli() -> None:
    """
    Main CLI entry point function. Parses arguments, checks dependencies,
    prompts for input if needed, and executes downloads.
    """
    print_banner()

    # Load default settings from config directory
    config_file = Path(__file__).parent.parent / "config" / "default_config.json"
    config = load_config(config_file)

    # Setup command line argument parser
    parser = argparse.ArgumentParser(
        description="MuDa - High Quality Audio Downloader for YouTube & Spotify",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "url",
        nargs="?",
        default=None,
        help="YouTube video/playlist URL or Spotify track/playlist/album URL",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=config.get("output_dir", "./downloads"),
        help="Destination directory to save MP3 files",
    )
    parser.add_argument(
        "-q",
        "--quality",
        default=config.get("audio_quality", "320"),
        choices=["128", "192", "256", "320"],
        help="Audio quality bitrate in kbps",
    )
    parser.add_argument(
        "--oauth",
        action="store_true",
        default=config.get("use_oauth", False),
        help="Authenticate via YouTube OAuth (device login) to bypass strict bot/Android restrictions",
    )
    parser.add_argument(
        "--cookies",
        default=config.get("cookies", None),
        help="Path to cookies.txt file for YouTube authentication",
    )

    args = parser.parse_args()

    # Step 1: Perform System Dependency Checks
    ffmpeg_ok, _ = check_ffmpeg()
    if not ffmpeg_ok:
        display_ffmpeg_warning()

    # Step 2: Internet Connection Check
    if not check_internet_connection():
        console.print("[bold red]Error:[/bold red] No active internet connection detected. Please check your network.", style="red")
        sys.exit(1)

    # Step 3: Interactive Prompt if URL argument was omitted
    url = args.url
    if not url:
        console.print("[bold yellow]Enter YouTube or Spotify link below:[/bold yellow]")
        url = Prompt.ask("[bold cyan]URL[/bold cyan]")

    if not url or not url.strip():
        console.print("[bold red]Error:[/bold red] No URL provided. Exiting.")
        sys.exit(1)

    url = url.strip()

    # Identify URL platform type for user feedback
    if SpotifyParser.is_spotify_url(url):
        url_type = SpotifyParser.get_url_type(url)
        console.print(f"🎵 [bold green]Detected Spotify {url_type.capitalize()} link[/bold green]")
    else:
        console.print("▶️  [bold red]Detected YouTube link / search query[/bold red]")

    # Step 4: Progress Callback setup for Rich CLI
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:

        current_task = progress.add_task("[cyan]Processing link...", total=None)

        def progress_hook(d: Dict[str, Any]) -> None:
            """Callback invoked by yt-dlp to update the Rich progress bar."""
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                filename = Path(d.get("filename", "Audio")).name

                if total > 0:
                    progress.update(
                        current_task,
                        description=f"[cyan]Downloading: [bold]{filename[:25]}[/bold]",
                        total=total,
                        completed=downloaded,
                    )
                else:
                    progress.update(
                        current_task,
                        description=f"[cyan]Downloading: [bold]{filename[:25]}[/bold]",
                    )
            elif d.get("status") == "finished":
                progress.update(current_task, description="[green]Extracting audio (FFmpeg)...")

        # Initialize Downloader Engine with automatic fallback and optional OAuth / cookies
        downloader = AudioDownloader(
            output_dir=args.output,
            audio_quality=args.quality,
            progress_callback=progress_hook,
            use_oauth=args.oauth,
            cookies=args.cookies,
        )

        try:
            results = downloader.download_url(url)
        except Exception as e:
            console.print(f"[bold red]Unexpected error during download execution:[/bold red] {e}")
            sys.exit(1)

    # Step 5: Render final summary table
    display_summary_table(results, args.output)
