"""
Video downloader — yt-dlp wrapper for YouTube, Twitter/X, TikTok, etc.
"""
import subprocess
import json as json_mod
from pathlib import Path
from typing import Optional

from hermes_api.config import HermesConfig


class VideoDownloader:
    """Download videos from YouTube, Twitter/X, etc. via yt-dlp."""

    def __init__(self, config: HermesConfig):
        self.config = config
        self.output_dir = config.output_dir / "downloads"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download(
        self,
        url: str,
        output_template: Optional[str] = None,
        format: str = "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    ) -> Path:
        """
        Download a video from URL.
        
        Args:
            url: YouTube, Twitter/X, TikTok, etc. URL
            output_template: Custom output filename template
            format: yt-dlp format string
            
        Returns:
            Path to downloaded video file
        """
        tmpl = output_template or str(self.output_dir / "%(title).100s_%(id)s.%(ext)s")
        
        cmd = [
            "yt-dlp",
            "-f", format,
            "-o", tmpl,
            "--restrict-filenames",
            "--no-playlist",
            "--print", "after_move:filepath",
            url,
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp failed:\n{result.stderr.strip()}")
        
        # Son çıktı satırı filepath
        lines = [l.strip() for l in result.stdout.split("\n") if l.strip()]
        if lines:
            return Path(lines[-1])
        raise RuntimeError("yt-dlp returned no output")

    def list_formats(self, url: str) -> str:
        """List available formats for a URL."""
        cmd = ["yt-dlp", "-F", "--no-playlist", url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp format list failed:\n{result.stderr.strip()}")
        return result.stdout

    def get_info(self, url: str) -> dict:
        """Get video metadata (title, duration, etc.)"""
        cmd = ["yt-dlp", "--dump-json", "--no-playlist", url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp info failed:\n{result.stderr.strip()}")
        return json_mod.loads(result.stdout)
