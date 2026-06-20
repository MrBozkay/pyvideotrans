"""
Text-to-Speech & Voice Cloning — CosyVoice wrapper.
"""
from pathlib import Path
from typing import Optional

from hermes_api.config import HermesConfig


class TTSGenerator:
    """Generate dubbing audio using CosyVoice voice cloning or other TTS engines."""

    def __init__(self, config: HermesConfig):
        self.config = config

    def set_reference_voice(self, audio_path: str | Path, transcript: str = ""):
        """
        Set reference audio for voice cloning.
        
        Args:
            audio_path: Path to reference voice recording (WAV, 3-10s)
            transcript: Optional transcript of the reference audio
        """
        self.config.ref_audio = str(Path(audio_path).resolve())
        self.config.ref_text = transcript

    def generate(
        self,
        srt_path: str | Path,
        output_audio: Optional[str | Path] = None,
        ref_audio: Optional[str | Path] = None,
        speed: Optional[float] = None,
    ) -> str:
        """
        Generate dubbing audio from SRT subtitles using TTS.
        
        Uses pyVideoTrans CLI (tts task).
        Returns path to generated audio file.
        """
        import subprocess
        import sys

        ref = str(Path(ref_audio).resolve()) if ref_audio else (self.config.ref_audio or "")
        spd = speed if speed is not None else self.config.tts_speed

        cmd = [
            sys.executable, "-u", str(self.config.project_root / "cli.py"),
            "--task", "tts",
            "--name", str(Path(srt_path).resolve()),
            "--tts_provider", self.config.tts_provider,
            "--speed", str(spd),
        ]

        if ref:
            cmd += ["--ref_audio", ref]
            if self.config.ref_text:
                cmd += ["--ref_text", self.config.ref_text]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if result.returncode != 0:
            raise RuntimeError(f"TTS generation failed:\n{result.stderr.strip()}")

        # pyVideoTrans generates audio alongside SRT or in output dir
        srt_file = Path(srt_path)
        # Look for generated WAV/mp3 files
        candidates = (
            list(self.config.output_dir.glob("*.wav")) +
            list(self.config.output_dir.glob("*.mp3")) +
            list(self.config.output_dir.glob("*.m4a"))
        )
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        if candidates:
            return str(candidates[0])

        raise RuntimeError(f"TTS completed but output audio not found.\n{result.stdout}")
