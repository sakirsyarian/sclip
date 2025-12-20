"""YouTube video downloader service using yt-dlp.

Provides functionality to download YouTube videos for processing.
This is an optional feature - users can also process local video files.

Key Features:
    - Download YouTube videos in best available quality
    - Get video metadata without downloading
    - Handle various error conditions gracefully
    - Report download progress via callbacks
    - Automatic cleanup on error

Supported URL Formats:
    - Standard: youtube.com/watch?v=VIDEO_ID
    - Short: youtu.be/VIDEO_ID
    - Embed: youtube.com/embed/VIDEO_ID
    - Mobile: m.youtube.com/watch?v=VIDEO_ID
    - Shorts: youtube.com/shorts/VIDEO_ID

Error Handling:
    - VideoUnavailableError: Private, deleted, or geo-restricted videos
    - AgeRestrictedError: Age-gated content requiring authentication
    - DownloadError: Network issues, rate limits, etc.

Usage:
    from src.services.downloader import YouTubeDownloader, download_youtube
    
    # Using the class
    downloader = YouTubeDownloader(output_dir="/tmp")
    path = await downloader.download(url, progress_callback=on_progress)
    
    # Using the convenience function
    path = await download_youtube(url, output_dir="/tmp")
    
    # Get info without downloading
    info = await get_video_info_from_url(url)
"""

import asyncio
import os
import re
import tempfile
from pathlib import Path
from typing import Callable

from src.types import ValidationResult, ExitCode
from src.utils.logger import get_logger
from src.utils.cleanup import register_temp_file


# yt-dlp import with graceful handling if not installed
# yt-dlp is optional - only needed for YouTube URL support
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False


def is_yt_dlp_available() -> bool:
    """Check if yt-dlp is available.
    
    Returns:
        True if yt-dlp is installed and importable, False otherwise
    """
    return YT_DLP_AVAILABLE


def validate_youtube_url(url: str) -> ValidationResult:
    """Validate that URL is a valid YouTube URL.
    
    Supports:
    - Standard watch URLs (youtube.com/watch?v=...)
    - Short URLs (youtu.be/...)
    - Embed URLs (youtube.com/embed/...)
    - Mobile URLs (m.youtube.com/watch?v=...)
    - YouTube Shorts (youtube.com/shorts/...)
    
    Args:
        url: YouTube URL to validate
        
    Returns:
        ValidationResult with valid=True if URL matches any pattern
    """
    if not url:
        return ValidationResult(
            valid=False,
            error="YouTube URL is empty",
            error_code=ExitCode.INPUT_ERROR
        )
    
    youtube_patterns = [
        r"^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]{11}",
        r"^https?://youtu\.be/[\w-]{11}",
        r"^https?://(?:www\.)?youtube\.com/embed/[\w-]{11}",
        r"^https?://m\.youtube\.com/watch\?v=[\w-]{11}",
        r"^https?://(?:www\.)?youtube\.com/shorts/[\w-]{11}",
    ]
    
    for pattern in youtube_patterns:
        if re.match(pattern, url, re.IGNORECASE):
            return ValidationResult(valid=True)
    
    return ValidationResult(
        valid=False,
        error=f"Invalid YouTube URL: {url}",
        error_code=ExitCode.INPUT_ERROR
    )


def extract_video_id(url: str) -> str | None:
    """Extract video ID from YouTube URL.
    
    Args:
        url: YouTube URL
        
    Returns:
        Video ID string or None if not found
    """
    patterns = [
        r"(?:v=|/)([a-zA-Z0-9_-]{11})(?:[&?/]|$)",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"embed/([a-zA-Z0-9_-]{11})",
        r"shorts/([a-zA-Z0-9_-]{11})",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


# Custom exception classes for specific download error conditions
# These allow callers to handle different error types appropriately

class DownloadError(Exception):
    """Exception raised when video download fails.
    
    Base class for download-related errors. Includes an error_code
    attribute for CLI exit code handling.
    """
    
    def __init__(self, message: str, error_code: ExitCode = ExitCode.PROCESSING_ERROR):
        super().__init__(message)
        self.error_code = error_code


class VideoUnavailableError(DownloadError):
    """Exception raised when video is unavailable.
    
    This includes:
    - Private videos
    - Deleted videos
    - Geo-restricted videos
    - Copyright-blocked videos
    """
    
    def __init__(self, message: str):
        super().__init__(message, ExitCode.INPUT_ERROR)


class AgeRestrictedError(DownloadError):
    """Exception raised when video is age-restricted.
    
    Age-restricted videos require authentication to download,
    which is not supported in the current implementation.
    """
    
    def __init__(self, message: str):
        super().__init__(message, ExitCode.INPUT_ERROR)



class YouTubeDownloader:
    """YouTube video downloader using yt-dlp.
    
    Provides methods to download videos and retrieve metadata from YouTube.
    Handles various error conditions and supports progress reporting.
    
    Example:
        downloader = YouTubeDownloader()
        
        # Get video info without downloading
        info = await downloader.get_video_info("https://youtube.com/watch?v=...")
        
        # Download video with progress
        def on_progress(downloaded, total):
            print(f"{downloaded}/{total} bytes")
        
        path = await downloader.download(url, output_dir, progress_callback=on_progress)
    """
    
    def __init__(self, output_dir: str | None = None):
        """Initialize the downloader.
        
        Args:
            output_dir: Default output directory for downloads.
                       If None, uses system temp directory.
        """
        if not YT_DLP_AVAILABLE:
            raise DownloadError(
                "yt-dlp is not installed. Install it with: pip install yt-dlp",
                ExitCode.DEPENDENCY_ERROR
            )
        
        self._output_dir = output_dir or tempfile.gettempdir()
        self._logger = get_logger()
        self._current_progress_callback: Callable[[int, int], None] | None = None
    
    def _get_ydl_opts(
        self,
        output_template: str,
        progress_callback: Callable[[int, int], None] | None = None
    ) -> dict:
        """Get yt-dlp options for downloading.
        
        Args:
            output_template: Output filename template
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary of yt-dlp options
        """
        self._current_progress_callback = progress_callback
        
        opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "merge_output_format": "mp4",
            # Avoid age-restriction issues where possible
            "age_limit": None,
            # Handle errors gracefully
            "ignoreerrors": False,
            "no_color": True,
        }
        
        if progress_callback:
            opts["progress_hooks"] = [self._progress_hook]
        
        return opts
    
    def _progress_hook(self, d: dict) -> None:
        """Progress hook for yt-dlp.
        
        Args:
            d: Progress dictionary from yt-dlp
        """
        if self._current_progress_callback is None:
            return
        
        if d["status"] == "downloading":
            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            if total > 0:
                self._current_progress_callback(downloaded, total)
        elif d["status"] == "finished":
            total = d.get("total_bytes", 0) or d.get("downloaded_bytes", 0)
            if total > 0:
                self._current_progress_callback(total, total)
    
    def _handle_yt_dlp_error(self, error: Exception, url: str) -> None:
        """Handle yt-dlp errors and raise appropriate exceptions.
        
        Args:
            error: The exception from yt-dlp
            url: The URL that was being processed
            
        Raises:
            VideoUnavailableError: If video is private, deleted, or unavailable
            AgeRestrictedError: If video is age-restricted
            DownloadError: For other download failures
        """
        error_msg = str(error).lower()
        
        # Check for private/unavailable video
        if any(phrase in error_msg for phrase in [
            "private video",
            "video unavailable",
            "video is unavailable",
            "this video is private",
            "video has been removed",
            "video is no longer available",
            "this video does not exist",
        ]):
            raise VideoUnavailableError(
                f"Video is unavailable or private: {url}"
            )
        
        # Check for age-restricted content
        if any(phrase in error_msg for phrase in [
            "age-restricted",
            "sign in to confirm your age",
            "age verification",
            "content warning",
        ]):
            raise AgeRestrictedError(
                f"Video is age-restricted and cannot be downloaded without authentication: {url}"
            )
        
        # Check for geo-restriction
        if any(phrase in error_msg for phrase in [
            "not available in your country",
            "geo-restricted",
            "blocked in your country",
        ]):
            raise VideoUnavailableError(
                f"Video is geo-restricted and not available in your region: {url}"
            )
        
        # Check for copyright issues
        if any(phrase in error_msg for phrase in [
            "copyright",
            "blocked",
            "content id",
        ]):
            raise VideoUnavailableError(
                f"Video is blocked due to copyright: {url}"
            )
        
        # Generic download error
        raise DownloadError(f"Failed to download video: {error}")


    async def get_video_info(self, url: str) -> dict | None:
        """Get video metadata without downloading.
        
        Retrieves information like title, duration, resolution, etc.
        without actually downloading the video file.
        
        Args:
            url: YouTube URL
            
        Returns:
            Dictionary with video metadata or None if unavailable.
            Keys include: title, duration, width, height, fps, etc.
            
        Raises:
            VideoUnavailableError: If video is private or unavailable
            AgeRestrictedError: If video is age-restricted
            DownloadError: For other errors
        """
        validation = validate_youtube_url(url)
        if not validation.valid:
            raise DownloadError(validation.error or "Invalid URL", ExitCode.INPUT_ERROR)
        
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "skip_download": True,
        }
        
        def extract_info():
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, extract_info)
            
            if info is None:
                return None
            
            # Extract relevant fields
            return {
                "id": info.get("id"),
                "title": info.get("title"),
                "description": info.get("description"),
                "duration": info.get("duration"),
                "width": info.get("width"),
                "height": info.get("height"),
                "fps": info.get("fps"),
                "view_count": info.get("view_count"),
                "like_count": info.get("like_count"),
                "channel": info.get("channel"),
                "channel_id": info.get("channel_id"),
                "upload_date": info.get("upload_date"),
                "thumbnail": info.get("thumbnail"),
                "formats": len(info.get("formats", [])),
            }
            
        except yt_dlp.utils.DownloadError as e:
            self._handle_yt_dlp_error(e, url)
            return None  # Never reached, but satisfies type checker
        except Exception as e:
            raise DownloadError(f"Failed to get video info: {e}")
    
    async def download(
        self,
        url: str,
        output_dir: str | None = None,
        filename: str | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
        register_for_cleanup: bool = True
    ) -> str:
        """Download YouTube video to local file.
        
        Downloads the video in the best available quality (preferring mp4).
        Supports progress reporting via callback.
        
        Args:
            url: YouTube URL to download
            output_dir: Directory to save the video. Uses default if None.
            filename: Custom filename (without extension). Uses video title if None.
            progress_callback: Optional callback(downloaded_bytes, total_bytes)
            register_for_cleanup: If True, register downloaded file for cleanup
            
        Returns:
            Path to the downloaded video file
            
        Raises:
            VideoUnavailableError: If video is private or unavailable
            AgeRestrictedError: If video is age-restricted
            DownloadError: For other download failures
        """
        validation = validate_youtube_url(url)
        if not validation.valid:
            raise DownloadError(validation.error or "Invalid URL", ExitCode.INPUT_ERROR)
        
        target_dir = output_dir or self._output_dir
        
        # Ensure output directory exists
        Path(target_dir).mkdir(parents=True, exist_ok=True)
        
        # Build output template
        if filename:
            # Sanitize filename
            safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            output_template = os.path.join(target_dir, f"{safe_filename}.%(ext)s")
        else:
            # Use video title
            output_template = os.path.join(target_dir, "%(title)s.%(ext)s")
        
        opts = self._get_ydl_opts(output_template, progress_callback)
        downloaded_file: str | None = None
        
        def do_download() -> str:
            nonlocal downloaded_file
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    raise DownloadError("Failed to extract video info")
                
                # Get the actual downloaded filename
                if "requested_downloads" in info and info["requested_downloads"]:
                    downloaded_file = info["requested_downloads"][0]["filepath"]
                else:
                    # Fallback: construct from template
                    ext = info.get("ext", "mp4")
                    if filename:
                        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                        downloaded_file = os.path.join(target_dir, f"{safe_filename}.{ext}")
                    else:
                        title = info.get("title", "video")
                        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                        downloaded_file = os.path.join(target_dir, f"{safe_title}.{ext}")
                
                return downloaded_file
        
        try:
            self._logger.debug(f"Starting download: {url}")
            
            # Run download in thread pool
            loop = asyncio.get_event_loop()
            result_path = await loop.run_in_executor(None, do_download)
            
            # Verify file exists
            if not os.path.exists(result_path):
                raise DownloadError(f"Download completed but file not found: {result_path}")
            
            # Register for cleanup if requested
            if register_for_cleanup:
                register_temp_file(result_path)
            
            self._logger.debug(f"Download complete: {result_path}")
            return result_path
            
        except yt_dlp.utils.DownloadError as e:
            # Clean up partial download if it exists
            if downloaded_file and os.path.exists(downloaded_file):
                try:
                    os.remove(downloaded_file)
                except OSError:
                    pass
            self._handle_yt_dlp_error(e, url)
            raise  # Never reached
        except DownloadError:
            raise
        except Exception as e:
            # Clean up partial download if it exists
            if downloaded_file and os.path.exists(downloaded_file):
                try:
                    os.remove(downloaded_file)
                except OSError:
                    pass
            raise DownloadError(f"Download failed: {e}")


# Convenience functions for simpler API

async def download_youtube(
    url: str,
    output_dir: str,
    progress_callback: Callable[[int, int], None] | None = None
) -> str:
    """Download YouTube video to local file.
    
    Convenience function that creates a YouTubeDownloader and downloads
    the video. For more control, use YouTubeDownloader directly.
    
    Args:
        url: YouTube URL to download
        output_dir: Directory to save the video
        progress_callback: Optional callback(downloaded_bytes, total_bytes)
        
    Returns:
        Path to the downloaded video file
        
    Raises:
        VideoUnavailableError: If video is private or unavailable
        AgeRestrictedError: If video is age-restricted
        DownloadError: For other download failures
    """
    downloader = YouTubeDownloader(output_dir)
    return await downloader.download(url, output_dir, progress_callback=progress_callback)


async def get_video_info_from_url(url: str) -> dict | None:
    """Get video metadata without downloading.
    
    Convenience function that creates a YouTubeDownloader and retrieves
    video information without downloading.
    
    Args:
        url: YouTube URL
        
    Returns:
        Dictionary with video metadata or None if unavailable
        
    Raises:
        VideoUnavailableError: If video is private or unavailable
        AgeRestrictedError: If video is age-restricted
        DownloadError: For other errors
    """
    downloader = YouTubeDownloader()
    return await downloader.get_video_info(url)


def check_yt_dlp_installed() -> tuple[bool, str | None]:
    """Check if yt-dlp is installed and get version.
    
    Returns:
        Tuple of (is_installed, version_string or None)
    """
    if not YT_DLP_AVAILABLE:
        return False, None
    
    try:
        version = yt_dlp.version.__version__
        return True, version
    except AttributeError:
        return True, "unknown"


__all__ = [
    "YouTubeDownloader",
    "DownloadError",
    "VideoUnavailableError",
    "AgeRestrictedError",
    "download_youtube",
    "get_video_info_from_url",
    "validate_youtube_url",
    "extract_video_id",
    "is_yt_dlp_available",
    "check_yt_dlp_installed",
    "YT_DLP_AVAILABLE",
]
