"""Analysis services for SmartClip AI.

This module provides multiple LLM backends for viral moment analysis:
- Groq: Fast, free LLMs (GPT OSS 120B, Llama 3.3)
- Gemini: Google's Gemini Flash
- OpenAI: GPT-4o
- Ollama: Local LLMs

Usage:
    from src.services.analyzers import get_analyzer
    
    analyzer = get_analyzer("groq", api_key="...")
    clips = await analyzer.analyze(transcript, duration, max_clips=5)
"""

from .base import BaseAnalyzer, AnalysisResult
from .groq import GroqAnalyzer
from .gemini import GeminiAnalyzer
from .openai import OpenAIAnalyzer
from .ollama import OllamaAnalyzer


def get_analyzer(
    provider: str,
    api_key: str | None = None,
    model: str | None = None,
    **kwargs
) -> BaseAnalyzer:
    """Factory function to get an analyzer instance.
    
    Args:
        provider: Analysis provider ("groq", "gemini", "openai", "ollama")
        api_key: API key for cloud providers
        model: Model name to use
        **kwargs: Additional provider-specific arguments
        
    Returns:
        Analyzer instance
        
    Raises:
        ValueError: If provider is not supported
    """
    providers = {
        "groq": GroqAnalyzer,
        "gemini": GeminiAnalyzer,
        "openai": OpenAIAnalyzer,
        "ollama": OllamaAnalyzer,
    }
    
    if provider not in providers:
        raise ValueError(f"Unknown analyzer provider: {provider}. Supported: {list(providers.keys())}")
    
    return providers[provider](api_key=api_key, model=model, **kwargs)


__all__ = [
    "BaseAnalyzer",
    "AnalysisResult",
    "GroqAnalyzer",
    "GeminiAnalyzer",
    "OpenAIAnalyzer",
    "OllamaAnalyzer",
    "get_analyzer",
]
