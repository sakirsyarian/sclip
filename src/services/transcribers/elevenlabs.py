"""ElevenLabs Scribe transcription service.

Uses ElevenLabs' Scribe API for speech-to-text with word-level timestamps.
Supports 99 languages with high accuracy.

API Documentation: https://elevenlabs.io/docs/api-reference/speech-to-text/convert
"""

import asyncio
import os
from typing import Callable

from .base import (
    BaseTranscriber,
    TranscriptionResult,
    WordTimestamp,
    TranscriptionError,
    TranscriptionAPIError,
    TranscriptionFileError,
)
from .chunking import (
    needs_chunking,
    split_audio,
    merge_transcription_results,
    cleanup_chunks,
    MAX_FILE_SIZE,
)


class ElevenLabsTranscriber(BaseTranscriber):
    """ElevenLabs Scribe transcription service.
    
    Features:
    - High accuracy transcription
    - Word-level timestamps
    - 99 language support
    - Speaker diarization
    - Audio event tagging
    
    Models:
    - scribe_v1: Default model, high accuracy
    """
    
    SUPPORTED_MODELS = [
        "scribe_v1",
    ]
    
    # ElevenLabs has generous file size limits
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    
    @property
    def name(self) -> str:
        return "ElevenLabs Scribe"
    
    @property
    def default_model(self) -> str:
        return "scribe_v1"
    
    def is_available(self) -> bool:
        """Check if ElevenLabs API key is available."""
        return bool(self.api_key or os.environ.get("ELEVENLABS_API_KEY"))
    
    def _get_api_key(self) -> str:
        """Get API key from instance or environment."""
        key = self.api_key or os.environ.get("ELEVENLABS_API_KEY")
        if not key:
            raise TranscriptionAPIError(
                "ElevenLabs API key not found. Set ELEVENLABS_API_KEY environment variable "
                "or pass api_key parameter. Get API key at https://elevenlabs.io"
            )
        return key

    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        progress_callback: Callable[[str], None] | None = None
    ) -> TranscriptionResult:
        """Transcribe audio using ElevenLabs Scribe API.
        
        Args:
            audio_path: Path to audio file (mp3, wav, etc.)
            language: Language code (e.g., 'id' for Indonesian, 'en' for English)
            progress_callback: Optional callback for progress updates
            
        Returns:
            TranscriptionResult with text and word timestamps
        """
        def update_progress(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)
        
        # Validate file
        if not os.path.exists(audio_path):
            raise TranscriptionFileError(f"Audio file not found: {audio_path}")
        
        file_size = os.path.getsize(audio_path)
        
        # Check if chunking is needed
        if needs_chunking(audio_path, MAX_FILE_SIZE):
            update_progress(f"Audio file large ({file_size / (1024*1024):.1f}MB), splitting into chunks...")
            return await self._transcribe_chunked(audio_path, language, progress_callback)
        
        # Single file transcription
        return await self._transcribe_single(audio_path, language, progress_callback)
    
    async def _transcribe_single(
        self,
        audio_path: str,
        language: str | None = None,
        progress_callback: Callable[[str], None] | None = None
    ) -> TranscriptionResult:
        """Transcribe a single audio file."""
        def update_progress(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)
        
        update_progress("Connecting to ElevenLabs API...")
        
        try:
            from elevenlabs.client import ElevenLabs
        except ImportError:
            raise TranscriptionError(
                "ElevenLabs SDK not installed. Install with: pip install elevenlabs"
            )
        
        api_key = self._get_api_key()
        client = ElevenLabs(api_key=api_key)
        
        model = self.get_model()
        update_progress(f"Transcribing with {model}...")
        
        # Map language codes (ElevenLabs uses 3-letter codes)
        lang_code = self._map_language_code(language)
        
        # Run API call in thread pool
        loop = asyncio.get_event_loop()
        
        try:
            with open(audio_path, "rb") as audio_file:
                transcription = await loop.run_in_executor(
                    None,
                    lambda: client.speech_to_text.convert(
                        file=audio_file,
                        model_id=model,
                        language_code=lang_code,
                        tag_audio_events=False,
                        diarize=False,
                    )
                )
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                raise TranscriptionAPIError("Invalid ElevenLabs API key")
            elif "429" in error_msg or "rate" in error_msg.lower():
                raise TranscriptionAPIError("ElevenLabs rate limit exceeded. Please wait and try again.")
            else:
                raise TranscriptionAPIError(f"ElevenLabs API error: {error_msg}")
        
        update_progress("Processing transcription results...")
        
        return self._parse_response(transcription, language)
    
    def _map_language_code(self, language: str | None) -> str | None:
        """Map 2-letter language codes to ElevenLabs 3-letter codes."""
        if not language:
            return None
        
        # Common mappings
        lang_map = {
            "id": "ind",  # Indonesian
            "en": "eng",  # English
            "es": "spa",  # Spanish
            "fr": "fra",  # French
            "de": "deu",  # German
            "it": "ita",  # Italian
            "pt": "por",  # Portuguese
            "ru": "rus",  # Russian
            "ja": "jpn",  # Japanese
            "ko": "kor",  # Korean
            "zh": "cmn",  # Chinese (Mandarin)
            "ar": "ara",  # Arabic
            "hi": "hin",  # Hindi
            "th": "tha",  # Thai
            "vi": "vie",  # Vietnamese
            "nl": "nld",  # Dutch
            "pl": "pol",  # Polish
            "tr": "tur",  # Turkish
        }
        
        return lang_map.get(language, language)

    async def _transcribe_chunked(
        self,
        audio_path: str,
        language: str | None = None,
        progress_callback: Callable[[str], None] | None = None
    ) -> TranscriptionResult:
        """Transcribe large audio file by splitting into chunks."""
        def update_progress(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)
        
        # Split audio into chunks
        try:
            chunks = split_audio(audio_path)
        except Exception as e:
            raise TranscriptionError(f"Failed to split audio: {e}")
        
        update_progress(f"Split into {len(chunks)} chunks")
        
        results = []
        try:
            for i, chunk in enumerate(chunks):
                update_progress(f"Transcribing chunk {i + 1}/{len(chunks)}...")
                
                result = await self._transcribe_single(
                    chunk.path,
                    language,
                    None
                )
                results.append((chunk, result))
            
            update_progress("Merging transcription results...")
            merged = merge_transcription_results(results)
            
            return merged
            
        finally:
            cleanup_chunks(chunks)
    
    def _parse_response(
        self, 
        transcription, 
        language: str | None
    ) -> TranscriptionResult:
        """Parse ElevenLabs response into TranscriptionResult."""
        words: list[WordTimestamp] = []
        full_text = ""
        duration = 0.0
        
        try:
            # Get full text
            full_text = transcription.text or ""
            
            # Get word-level timestamps
            if hasattr(transcription, 'words') and transcription.words:
                for w in transcription.words:
                    # Skip spacing elements
                    if hasattr(w, 'type') and w.type == "spacing":
                        continue
                    
                    word_text = w.text if hasattr(w, 'text') else str(w.get('text', ''))
                    start = w.start if hasattr(w, 'start') else w.get('start', 0)
                    end = w.end if hasattr(w, 'end') else w.get('end', 0)
                    
                    words.append(WordTimestamp(
                        word=word_text.strip(),
                        start=float(start),
                        end=float(end)
                    ))
                
                # Duration from last word
                if words:
                    duration = words[-1].end
            
            # Get detected language
            detected_lang = ""
            if hasattr(transcription, 'language_code'):
                detected_lang = transcription.language_code
        
        except Exception as e:
            raise TranscriptionAPIError(f"Failed to parse ElevenLabs response: {e}")
        
        return TranscriptionResult(
            text=full_text,
            words=words,
            language=language or detected_lang,
            duration=duration
        )
