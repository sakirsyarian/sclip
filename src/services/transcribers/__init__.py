"""Transcription services for SmartClip AI.

This module provides multiple transcription backends:
- Groq: Fast, free Whisper API
- OpenAI: OpenAI Whisper API
- Local: Local faster-whisper

Usage:
    from src.services.transcribers import get_transcriber
    
    transcriber = get_transcriber("groq", api_key="...")
    result = await transcriber.transcribe("audio.mp3", language="id")
"""

from .base import BaseTranscriber, TranscriptionResult, WordTimestamp
from .groq import GroqTranscriber
from .openai import OpenAITranscriber
from .local import LocalTranscriber


def get_transcriber(
    provider: str,
    api_key: str | None = None,
    model: str | None = None
) -> BaseTranscriber:
    """Factory function to get a transcriber instance.
    
    Args:
        provider: Transcription provider ("groq", "openai", "local")
        api_key: API key for cloud providers
        model: Model name to use
        
    Returns:
        Transcriber instance
        
    Raises:
        ValueError: If provider is not supported
    """
    providers = {
        "groq": GroqTranscriber,
        "openai": OpenAITranscriber,
        "local": LocalTranscriber,
    }
    
    if provider not in providers:
        raise ValueError(f"Unknown transcriber provider: {provider}. Supported: {list(providers.keys())}")
    
    return providers[provider](api_key=api_key, model=model)


__all__ = [
    "BaseTranscriber",
    "TranscriptionResult", 
    "WordTimestamp",
    "GroqTranscriber",
    "OpenAITranscriber",
    "LocalTranscriber",
    "get_transcriber",
]
