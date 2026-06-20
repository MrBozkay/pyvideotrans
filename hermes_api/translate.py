"""
Translation — local LLM (Ollama) wrapper using pyVideoTrans engine.
"""
from pathlib import Path
from typing import Optional

from hermes_api.config import HermesConfig


class Translator:
    """Translate SRT subtitles using Ollama (local LLM)."""

    def __init__(self, config: HermesConfig):
        self.config = config

    def translate(
        self,
        srt_path: str | Path,
        target_lang: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Translate an SRT subtitle file to target language.
        
        Uses pyVideoTrans CLI (sts task = subtitle translation).
        Returns path to translated SRT file.
        """
        import subprocess
        import sys

        target = target_lang or self.config.target_language
        llm_model = model or self.config.ollama_model

        # Ollama ayarlarını environment variable olarak passthrough
        env = {
            "localllm_api": self.config.ollama_api,
            "localllm_model": llm_model,
            "localllm_key": "",
            "localllm_max_token": str(self.config.ollama_max_tokens),
        }

        cmd = [
            sys.executable, "-u", str(self.config.project_root / "cli.py"),
            "--task", "sts",
            "--name", str(Path(srt_path).resolve()),
            "--target_lang", target,
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=1800,
            env={**__import__("os").environ, **env},
        )
        if result.returncode != 0:
            raise RuntimeError(f"Translation failed:\n{result.stderr.strip()}")

        # pyVideoTrans translated SRT: usually <basename>_<lang>.srt
        base = Path(srt_path)
        # Look for newly created srt files in same directory
        import glob
        srt_dir = base.parent
        translated = sorted(srt_dir.glob(f"{base.stem}*_*.srt"), key=lambda p: p.stat().st_mtime)
        if translated:
            return str(translated[-1])

        # Fallback to output dir
        translated = sorted(self.config.output_dir.glob("*.srt"), key=lambda p: p.stat().st_mtime)
        if translated:
            return str(translated[-1])

        raise RuntimeError(f"Translation completed but output SRT not found.\n{result.stdout}")
