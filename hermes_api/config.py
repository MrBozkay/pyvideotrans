"""
Configuration for Hermes API wrapper over pyVideoTrans.
Sets up pyVideoTrans settings for headless/GPU operation.
"""
import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class HermesConfig:
    """Single source of truth for Hermes API configuration."""

    # --- Paths ---
    project_root: Path = PROJECT_ROOT
    voices_dir: Path = PROJECT_ROOT / "voices"
    output_dir: Path = PROJECT_ROOT / "output"
    cache_dir: Path = PROJECT_ROOT / "cache"

    # --- GPU / Hardware ---
    use_cuda: bool = True
    device: str = "cuda"  # "cuda" or "cpu"
    compute_type: str = "float16"  # for Faster-Whisper

    # --- ASR (Faster-Whisper) ---
    asr_model: str = "large-v3"       # model boyutu
    asr_provider: int = 0              # 0=faster-whisper, 1=openai-whisper
    asr_language: str = "auto"        # "auto" veya "en", "tr", etc.
    remove_noise: bool = False
    enable_diarize: bool = False
    rephrase: int = 0                 # 0=none, 1=LLM split

    # --- Translation (Ollama local LLM) ---
    translate_provider: str = "localllm"
    ollama_api: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen3:8b"              # veya "llama3", "mistral"
    ollama_max_tokens: int = 4096
    target_language: str = "Turkish"            # hedef dil

    # --- TTS / Voice Clone (CosyVoice) ---
    tts_provider: str = "cosyvoice"
    cosyvoice_api: str = ""                     # boşsa local gradio endpoint
    ref_audio: Optional[str] = None             # ses clone referansı
    ref_text: Optional[str] = ""                # referans sesin transkripti
    tts_speed: float = 1.0
    voice_clone_mode: str = "3s极速复刻"          # CosyVoice clone mode

    # --- Video ---
    keep_original_audio: bool = False           # background noise mix
    subtitle_style: str = "bilingual"           # "bilingual", "translated", "source"

    def resolve(self) -> dict:
        """Export as pyVideoTrans params dict (for videotrans.configure.config)."""
        return {
            "use_cuda": self.use_cuda,
            "device": self.device,
            "compute_type": self.compute_type,
            "recogn_type": self.asr_provider,
            "model_name": self.asr_model,
            "detect_lang": self.asr_language,
            "remove_noise": self.remove_noise,
            "enable_diarize": self.enable_diarize,
            "rephrase": self.rephrase,
            # Translation
            "trans_provider": self.translate_provider,
            "localllm_api": self.ollama_api,
            "localllm_model": self.ollama_model,
            "localllm_key": "",
            "localllm_max_token": self.ollama_max_tokens,
            "target_language": self.target_language,
            # TTS
            "tts_provider": self.tts_provider,
            "cosyvoice_api": self.cosyvoice_api,
            "ref_audio": self.ref_audio,
            "ref_text": self.ref_text or "",
            "tts_speed": self.tts_speed,
            "voice_clone_mode": self.voice_clone_mode,
        }

    def save_json(self, path: Optional[Path] = None) -> Path:
        """Save config to JSON (for persistence)."""
        path = path or self.project_root / "hermes_config.json"
        data = {k: str(v) if isinstance(v, Path) else v
                for k, v in self.__dict__.items() if not k.startswith("_")}
        data["project_root"] = str(self.project_root)
        data["voices_dir"] = str(self.voices_dir)
        data["output_dir"] = str(self.output_dir)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    @classmethod
    def load_json(cls, path: Path) -> "HermesConfig":
        """Load config from JSON file."""
        data = json.loads(path.read_text(encoding="utf-8"))
        # Convert string paths back to Path
        for key in ("project_root", "voices_dir", "output_dir"):
            if key in data:
                data[key] = Path(data[key])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
