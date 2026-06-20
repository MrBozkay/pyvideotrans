"""
Pipeline Orchestrator — Hermes'in iki modu:

A) Full Auto: İndir → Transkripsiyon → Çeviri → Voice Clone → Dublaj → Video
B) Stage-by-Stage: Her aşamayı teker teker çağır, arasına müdahale et
"""
from pathlib import Path
from typing import Optional

from hermes_api.config import HermesConfig
from hermes_api.download import VideoDownloader
from hermes_api.transcribe import Transcriber
from hermes_api.translate import Translator
from hermes_api.tts import TTSGenerator
from hermes_api.dub import DubbingEngine


class Pipeline:
    """Full pipeline orchestrator with A (auto) and B (stage) modes."""

    def __init__(self, config: Optional[HermesConfig] = None):
        self.config = config or HermesConfig()
        self.downloader = VideoDownloader(self.config)
        self.transcriber = Transcriber(self.config)
        self.translator = Translator(self.config)
        self.tts = TTSGenerator(self.config)
        self.dubber = DubbingEngine(self.config)

    # ============================================================
    # B) STAGE-BY-STAGE MODE — her aşama çağrılabilir
    # ============================================================

    def stage_download(self, url: str) -> str:
        """Stage 1: Video indir. Returns path."""
        path = self.downloader.download(url)
        return str(path)

    def stage_transcribe(self, video_path: str | Path) -> str:
        """Stage 2: Transkripsiyon. Returns SRT path."""
        return self.transcriber.transcribe(video_path)

    def stage_translate(self, srt_path: str | Path, target_lang: Optional[str] = None) -> str:
        """Stage 3: Çeviri. Returns translated SRT path."""
        return self.translator.translate(srt_path, target_lang or self.config.target_language)

    def stage_tts(self, srt_path: str | Path) -> str:
        """Stage 4: Voice clone + TTS. Returns audio path."""
        return self.tts.generate(srt_path)

    def stage_dub(self, video_path: str | Path, audio_path: str | Path, srt_path: Optional[str | Path] = None) -> str:
        """Stage 5: Dublajlı videoyu oluştur. Returns video path."""
        return self.dubber.merge_audio(video_path, audio_path, subtitle_path=srt_path)

    def stage_dub_with_cli(self, video_path: str | Path, srt_path: str | Path) -> str:
        """Stage 5 alt: pyVideoTrans VTV ile full dublaj. Returns video path."""
        return self.dubber.merge_audio_with_cli(video_path, srt_path)

    # ============================================================
    # A) FULL AUTO MODE — tek çağrıda her şey
    # ============================================================

    def run_full(
        self,
        url: str,
        target_language: Optional[str] = None,
        ref_audio: Optional[str | Path] = None,
        ref_text: str = "",
    ) -> dict:
        """
        Full pipeline: tek URL'den dublajlı videoya.
        
        Args:
            url: YouTube/Twitter/X/TikTok URL
            target_language: Hedef dil (örn. "Turkish")
            ref_audio: Ses clone referans kaydı
            ref_text: Referans kaydın transkripti
            
        Returns:
            Dict with paths for each stage output
        """
        if ref_audio:
            self.tts.set_reference_voice(ref_audio, ref_text)

        result = {
            "status": "started",
            "url": url,
            "stages": {},
        }

        # Stage 1: Download
        try:
            video_path = self.stage_download(url)
            result["stages"]["download"] = {"status": "ok", "path": video_path}
        except Exception as e:
            result["stages"]["download"] = {"status": "error", "error": str(e)}
            result["status"] = "failed"
            return result

        # Stage 2: Transcribe
        try:
            srt_path = self.stage_transcribe(video_path)
            result["stages"]["transcribe"] = {"status": "ok", "path": srt_path}
        except Exception as e:
            result["stages"]["transcribe"] = {"status": "error", "error": str(e)}
            result["status"] = "failed"
            return result

        # Stage 3: Translate
        try:
            translated_srt = self.stage_translate(srt_path, target_language or self.config.target_language)
            result["stages"]["translate"] = {"status": "ok", "path": translated_srt}
        except Exception as e:
            result["stages"]["translate"] = {"status": "error", "error": str(e)}
            result["status"] = "partial"
            return result

        # Stage 4: TTS / Voice Clone
        try:
            audio_path = self.stage_tts(translated_srt)
            result["stages"]["tts"] = {"status": "ok", "path": audio_path}
        except Exception as e:
            result["stages"]["tts"] = {"status": "error", "error": str(e)}
            result["status"] = "partial"
            return result

        # Stage 5: Dub
        try:
            dubbed_video = self.stage_dub(video_path, audio_path, translated_srt)
            result["stages"]["dub"] = {"status": "ok", "path": dubbed_video}
            result["status"] = "completed"
        except Exception as e:
            result["stages"]["dub"] = {"status": "error", "error": str(e)}
            result["status"] = "partial"

        return result

    def run_from_local(
        self,
        video_path: str | Path,
        target_language: Optional[str] = None,
        ref_audio: Optional[str | Path] = None,
    ) -> dict:
        """
        Yerel bir dosyadan pipeline çalıştır (indirme adımı atlanır).
        """
        if ref_audio:
            self.tts.set_reference_voice(ref_audio)

        result = {"status": "started", "file": str(video_path), "stages": {}}

        # Stage 2: Transcribe (skip download)
        try:
            srt_path = self.stage_transcribe(video_path)
            result["stages"]["transcribe"] = {"status": "ok", "path": srt_path}
        except Exception as e:
            result["stages"]["transcribe"] = {"status": "error", "error": str(e)}
            result["status"] = "failed"
            return result

        # Stage 3: Translate
        try:
            translated_srt = self.stage_translate(srt_path, target_language or self.config.target_language)
            result["stages"]["translate"] = {"status": "ok", "path": translated_srt}
        except Exception as e:
            result["stages"]["translate"] = {"status": "error", "error": str(e)}
            result["status"] = "partial"
            return result

        # Stage 4: TTS
        try:
            audio_path = self.stage_tts(translated_srt)
            result["stages"]["tts"] = {"status": "ok", "path": audio_path}
        except Exception as e:
            result["stages"]["tts"] = {"status": "error", "error": str(e)}
            result["status"] = "partial"
            return result

        # Stage 5: Dub
        try:
            dubbed_video = self.stage_dub(video_path, audio_path, translated_srt)
            result["stages"]["dub"] = {"status": "ok", "path": dubbed_video}
            result["status"] = "completed"
        except Exception as e:
            result["stages"]["dub"] = {"status": "error", "error": str(e)}
            result["status"] = "partial"

        return result
