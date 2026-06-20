"""
Dubbing Engine — merge dubbed audio back into video with FFmpeg.
"""
import subprocess
from pathlib import Path
from typing import Optional

from hermes_api.config import HermesConfig


class DubbingEngine:
    """Merge dubbed audio + subtitles back into the video."""

    def __init__(self, config: HermesConfig):
        self.config = config

    def merge_audio(
        self,
        video_path: str | Path,
        audio_path: str | Path,
        output_path: Optional[str | Path] = None,
        subtitle_path: Optional[str | Path] = None,
        keep_original_audio: Optional[bool] = None,
    ) -> str:
        """
        Replace original audio with dubbed audio (and optionally burn subtitles).
        
        Args:
            video_path: Original video file
            audio_path: Dubbed audio file (from TTS)
            output_path: Output video path (auto-generated if None)
            subtitle_path: Optional SRT to burn in
            keep_original_audio: Mix original background audio
        
        Returns:
            Path to the final dubbed video
        """
        video = Path(video_path)
        audio = Path(audio_path)
        output = Path(output_path) if output_path else (
            self.config.output_dir / f"{video.stem}_dubbed{video.suffix}"
        )
        output.parent.mkdir(parents=True, exist_ok=True)

        mix_bg = keep_original_audio if keep_original_audio is not None else self.config.keep_original_audio

        mixed_audio = None
        if mix_bg:
            # Mix dubbed audio with original (keep background)
            # Reduce original volume, overlay dubbed audio
            mixed_audio = output.with_suffix(".mixed.wav")
            cmd_mix = [
                "ffmpeg", "-y",
                "-i", str(video),
                "-i", str(audio),
                "-filter_complex",
                "[0:a]volume=0.3[bg];[1:a]volume=1.0[dub];[bg][dub]amix=inputs=2:duration=first[out]",
                "-map", "[out]",
                "-ac", "2",
                str(mixed_audio),
            ]
            subprocess.run(cmd_mix, check=True, capture_output=True, text=True, timeout=300)
            audio_to_use = mixed_audio
        else:
            audio_to_use = audio

        # Replace audio in video
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video),
            "-i", str(audio_to_use),
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
        ]

        # Optionally burn subtitles
        if subtitle_path and Path(subtitle_path).exists():
            cmd += ["-vf", f"subtitles={Path(subtitle_path).resolve()}"]

        cmd.append(str(output))

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg merge failed:\n{result.stderr.strip()}")

        # Cleanup temp mixed audio
        if mix_bg and mixed_audio and mixed_audio.exists():
            mixed_audio.unlink()

        return str(output)

    def merge_audio_with_cli(
        self,
        video_path: str | Path,
        srt_path: str | Path,
    ) -> str:
        """
        Full video dubbing using pyVideoTrans CLI (vtv task = video translation).
        This handles the entire STT→Translate→TTS→Merge pipeline.
        
        Args:
            video_path: Input video
            srt_path: Already translated SRT (skip STT/translate)
            
        Returns:
            Path to the final dubbed video
        """
        import sys

        cmd = [
            sys.executable, "-u", str(self.config.project_root / "cli.py"),
            "--task", "vtv",
            "--name", str(Path(video_path).resolve()),
            "--srt", str(Path(srt_path).resolve()),
            "--cuda", str(int(self.config.use_cuda)),
            "--tts_provider", self.config.tts_provider,
        ]
        if self.config.ref_audio:
            cmd += ["--ref_audio", self.config.ref_audio]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if result.returncode != 0:
            raise RuntimeError(f"Video dubbing failed:\n{result.stderr.strip()}")

        # Output is usually in output/ dir
        outputs = sorted(self.config.output_dir.glob("*dubbed*"), key=lambda p: p.stat().st_mtime)
        if outputs:
            return str(outputs[-1])
        raise RuntimeError(f"Dubbing completed but output not found.\n{result.stdout}")
