"""Groq Whisper transcription service.

Uses Groq's fast Whisper API for speech-to-text with word-level timestamps.
Free tier available with generous limits.

Supports auto-chunking for files larger than 25MB.

API Documentation: https://console.groq.com/docs/speech-to-text
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


class GroqTranscriber(BaseTranscriber):
    """Groq Whisper transcription service.
    
    Features:
    - Very fast transcription (10x+ realtime)
    - Word-level timestamps
    - Multi-language support
    - Free tier available
    
    Models:
    - whisper-large-v3: Best accuracy, multilingual
    - whisper-large-v3-turbo: Faster, good accuracy
    """
    
    SUPPORTED_MODELS = [
        "whisper-large-v3",
        "whisper-large-v3-turbo",
    ]
    
    # Max file size: 25MB free tier, 100MB dev tier
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB for free tier
    
    @property
    def name(self) -> str:
        return "Groq Whisper"
    
    @property
    def default_model(self) -> str:
        return "whisper-large-v3-turbo"
    
    def is_available(self) -> bool:
        """Check if Groq API key is available."""
        return bool(self.api_key or os.environ.get("GROQ_API_KEY"))
    
    def _get_api_key(self) -> str:
        """Get API key from instance or environment."""
        key = self.api_key or os.environ.get("GROQ_API_KEY")
        if not key:
            raise TranscriptionAPIError(
                "Groq API key not found. Set GROQ_API_KEY environment variable "
                "or pass api_key parameter."
            )
        return key
    
    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        progress_callback: Callable[[str], None] | None = None
    ) -> TranscriptionResult:
        """Transcribe audio using Groq Whisper API.
        
        Automatically chunks large files (>24MB) for processing.
        
        Args:
            audio_path: Path to audio file (mp3, wav, flac, etc.)
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
        
        update_progress("Connecting to Groq API...")
        
        try:
            from groq import Groq
        except ImportError:
            raise TranscriptionError(
                "Groq SDK not installed. Install with: pip install groq"
            )
        
        api_key = self._get_api_key()
        client = Groq(api_key=api_key)
        
        model = self.get_model()
        update_progress(f"Transcribing with {model}...")
        
        # Run synchronous API call in thread pool
        loop = asyncio.get_event_loop()
        
        try:
            transcription = await loop.run_in_executor(
                None,
                lambda: self._do_transcribe(client, audio_path, model, language)
            )
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                raise TranscriptionAPIError("Invalid Groq API key")
            elif "429" in error_msg or "rate" in error_msg.lower():
                raise TranscriptionAPIError("Groq rate limit exceeded. Please wait and try again.")
            else:
                raise TranscriptionAPIError(f"Groq API error: {error_msg}")
        
        update_progress("Processing transcription results...")
        
        # Extract word timestamps
        words: list[WordTimestamp] = []
        
        # Handle words - can be list of objects or list of dicts
        if hasattr(transcription, 'words') and transcription.words:
            for w in transcription.words:
                # Handle both object and dict formats
                if isinstance(w, dict):
                    words.append(WordTimestamp(
                        word=w.get('word', '').strip(),
                        start=w.get('start', 0.0),
                        end=w.get('end', 0.0)
                    ))
                else:
                    words.append(WordTimestamp(
                        word=w.word.strip(),
                        start=w.start,
                        end=w.end
                    ))
        
        # Get duration from last word or segments
        duration = 0.0
        if words:
            duration = words[-1].end
        elif hasattr(transcription, 'segments') and transcription.segments:
            last_seg = transcription.segments[-1]
            if isinstance(last_seg, dict):
                duration = last_seg.get('end', 0.0)
            else:
                duration = last_seg.end
        
        return TranscriptionResult(
            text=transcription.text,
            words=words,
            language=language or getattr(transcription, 'language', ''),
            duration=duration
        )
    
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
                
                # Transcribe this chunk
                result = await self._transcribe_single(
                    chunk.path,
                    language,
                    None  # Don't pass progress callback for individual chunks
                )
                results.append((chunk, result))
            
            # Merge results
            update_progress("Merging transcription results...")
            merged = merge_transcription_results(results)
            
            return merged
            
        finally:
            # Always cleanup chunk files
            cleanup_chunks(chunks)
    
    def _do_transcribe(self, client, audio_path: str, model: str, language: str | None):
        """Perform the actual transcription (synchronous)."""
        with open(audio_path, "rb") as audio_file:
            return client.audio.transcriptions.create(
                file=audio_file,
                model=model,
                response_format="verbose_json",
                timestamp_granularities=["word", "segment"],
                language=language,
                temperature=0.0
            )
