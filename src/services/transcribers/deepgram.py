"""Deepgram Nova transcription service.

Uses Deepgram's Nova-3 API for speech-to-text with word-level timestamps.
$200 free credit available for new accounts.

API Documentation: https://developers.deepgram.com/docs/getting-started-with-pre-recorded-audio
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


class DeepgramTranscriber(BaseTranscriber):
    """Deepgram Nova transcription service.
    
    Features:
    - Very fast transcription
    - Word-level timestamps
    - Multi-language support (Indonesian included)
    - $200 free credit for new accounts
    - High accuracy with Nova-3 model
    
    Models:
    - nova-3: Latest, best accuracy (default)
    - nova-2: Previous generation, still excellent
    - whisper-large: Deepgram-hosted Whisper
    """
    
    SUPPORTED_MODELS = [
        "nova-3",
        "nova-2",
        "whisper-large",
    ]
    
    # Deepgram has generous file size limits, but we use chunking for consistency
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    
    @property
    def name(self) -> str:
        return "Deepgram Nova"
    
    @property
    def default_model(self) -> str:
        return "nova-3"
    
    def is_available(self) -> bool:
        """Check if Deepgram API key is available."""
        return bool(self.api_key or os.environ.get("DEEPGRAM_API_KEY"))
    
    def _get_api_key(self) -> str:
        """Get API key from instance or environment."""
        key = self.api_key or os.environ.get("DEEPGRAM_API_KEY")
        if not key:
            raise TranscriptionAPIError(
                "Deepgram API key not found. Set DEEPGRAM_API_KEY environment variable "
                "or pass api_key parameter. Get $200 free credit at https://deepgram.com"
            )
        return key

    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        progress_callback: Callable[[str], None] | None = None
    ) -> TranscriptionResult:
        """Transcribe audio using Deepgram Nova API.
        
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
        
        # Check if chunking is needed (use same threshold as other providers)
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
        
        update_progress("Connecting to Deepgram API...")
        
        try:
            from deepgram import DeepgramClient, PrerecordedOptions, FileSource
        except ImportError:
            raise TranscriptionError(
                "Deepgram SDK not installed. Install with: pip install deepgram-sdk"
            )
        
        api_key = self._get_api_key()
        client = DeepgramClient(api_key)
        
        model = self.get_model()
        update_progress(f"Transcribing with {model}...")
        
        # Read audio file
        with open(audio_path, "rb") as audio_file:
            buffer_data = audio_file.read()
        
        payload: FileSource = {
            "buffer": buffer_data,
        }
        
        # Configure options
        options = PrerecordedOptions(
            model=model,
            smart_format=True,
            punctuate=True,
            paragraphs=True,
            utterances=False,
            language=language or "id",  # Default to Indonesian
        )
        
        # Run API call in thread pool
        loop = asyncio.get_event_loop()
        
        try:
            response = await loop.run_in_executor(
                None,
                lambda: client.listen.rest.v("1").transcribe_file(payload, options)
            )
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                raise TranscriptionAPIError("Invalid Deepgram API key")
            elif "429" in error_msg or "rate" in error_msg.lower():
                raise TranscriptionAPIError("Deepgram rate limit exceeded. Please wait and try again.")
            else:
                raise TranscriptionAPIError(f"Deepgram API error: {error_msg}")
        
        update_progress("Processing transcription results...")
        
        return self._parse_response(response, language)

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
    
    def _parse_response(
        self, 
        response, 
        language: str | None
    ) -> TranscriptionResult:
        """Parse Deepgram response into TranscriptionResult."""
        words: list[WordTimestamp] = []
        full_text = ""
        duration = 0.0
        
        try:
            # Get results from response
            results = response.results
            
            if results and results.channels:
                channel = results.channels[0]
                if channel.alternatives:
                    alt = channel.alternatives[0]
                    
                    # Get full transcript
                    full_text = alt.transcript or ""
                    
                    # Get word-level timestamps
                    if hasattr(alt, 'words') and alt.words:
                        for w in alt.words:
                            words.append(WordTimestamp(
                                word=w.punctuated_word or w.word,
                                start=w.start,
                                end=w.end
                            ))
                        
                        # Duration from last word
                        if words:
                            duration = words[-1].end
            
            # Get duration from metadata if available
            if hasattr(response, 'metadata') and response.metadata:
                if hasattr(response.metadata, 'duration'):
                    duration = response.metadata.duration
        
        except Exception as e:
            raise TranscriptionAPIError(f"Failed to parse Deepgram response: {e}")
        
        return TranscriptionResult(
            text=full_text,
            words=words,
            language=language or "",
            duration=duration
        )
