"""
Speech-to-Text — Faster-Whisper wrapper using pyVideoTrans engine.
"""
from pathlib import Path
from typing import Optional

from hermes_api.config import HermesConfig


class Transcriber:
    """Transcribe audio/video using Faster-Whisper (GPU)."""

    def __init__(self, config: HermesConfig):
        self.config = config

    def transcribe(
        self,
        audio_path: str | Path,
        model: Optional[str] = None,
        language: Optional[str] = None,
        cuda: Optional[bool] = None,
    ) -> str:
        """
        Transcribe audio file to SRT subtitles.
        
        Uses pyVideoTrans CLI under the hood (stt task).
        Returns path to generated SRT file.
        """
        import subprocess
        import sys

        model = model or self.config.asr_model
        lang = language or self.config.asr_language
        use_cuda = cuda if cuda is not None else self.config.use_cuda

        cmd = [
            sys.executable, "-u", str(self.config.project_root / "cli.py"),
            "--task", "stt",
            "--name", str(Path(audio_path).resolve()),
            "--model_name", model,
            "--detect_lang", lang,
            "--cuda", str(int(use_cuda)),
            "--recogn_type", str(self.config.asr_provider),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if result.returncode != 0:
            raise RuntimeError(f"Transcription failed:\n{result.stderr.strip()}")

        # pyVideoTrans output SRT: same name as input, .srt extension
        audio_file = Path(audio_path)
        srt_path = audio_file.with_suffix(".srt")
        if srt_path.exists():
            return str(srt_path)

        # Fallback: ara output klasöründe
        import glob
        srt_files = list(self.config.output_dir.glob("*.srt"))
        if srt_files:
            return str(srt_files[-1])

        raise RuntimeError(f"Transcription completed but SRT not found.\n{result.stdout}")
