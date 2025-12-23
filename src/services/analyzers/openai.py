"""OpenAI LLM analysis service.

Uses OpenAI's GPT models for viral moment analysis.
Paid service with high quality results.

API Documentation: https://platform.openai.com/docs/guides/chat
"""

import asyncio
import json
import os
from typing import Callable

from src.services.transcribers.base import TranscriptionResult
from src.types import ClipData, CaptionSegment

from .base import (
    BaseAnalyzer,
    AnalysisResult,
    AnalysisError,
    AnalysisAPIError,
    AnalysisParseError,
    build_analysis_prompt,
    format_transcript_with_timestamps,
    get_captions_for_range,
)


class OpenAIAnalyzer(BaseAnalyzer):
    """OpenAI LLM analysis service.
    
    Features:
    - High quality analysis
    - Large context windows
    - Paid service
    - Supports custom base URL for OpenAI-compatible APIs
    
    Models:
    - gpt-4o: Best quality
    - gpt-4o-mini: Good balance of quality and cost
    - gpt-4-turbo: Previous generation
    
    Custom Base URL:
    - Together AI: https://api.together.xyz/v1
    - OpenRouter: https://openrouter.ai/api/v1
    - Fireworks: https://api.fireworks.ai/inference/v1
    - Local (LM Studio): http://localhost:1234/v1
    - Local (vLLM): http://localhost:8000/v1
    """
    
    SUPPORTED_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ]
    
    def __init__(
        self, 
        api_key: str | None = None, 
        model: str | None = None,
        base_url: str | None = None,
        **kwargs
    ):
        """Initialize OpenAI analyzer.
        
        Args:
            api_key: OpenAI API key (or compatible provider key)
            model: Model name to use
            base_url: Custom base URL for OpenAI-compatible APIs
        """
        super().__init__(api_key=api_key, model=model, **kwargs)
        self.base_url = base_url
    
    @property
    def default_model(self) -> str:
        return "gpt-4o-mini"
    
    def is_available(self) -> bool:
        """Check if OpenAI API key is available."""
        # For custom base URL, we still need an API key (could be from the provider)
        return bool(self.api_key or os.environ.get("OPENAI_API_KEY"))
    
    @property
    def name(self) -> str:
        """Return provider name, including custom endpoint info."""
        if self.base_url:
            # Extract domain for display
            from urllib.parse import urlparse
            parsed = urlparse(self.base_url)
            domain = parsed.netloc or self.base_url
            return f"OpenAI-compatible ({domain})"
        return "OpenAI"
    
    def _get_api_key(self) -> str:
        """Get API key from instance or environment."""
        key = self.api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise AnalysisAPIError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        return key
    
    async def analyze(
        self,
        transcription: TranscriptionResult,
        video_duration: float,
        max_clips: int = 5,
        min_duration: int = 45,
        max_duration: int = 180,
        language: str = "id",
        progress_callback: Callable[[str], None] | None = None
    ) -> AnalysisResult:
        """Analyze transcript using OpenAI GPT.
        
        Args:
            transcription: TranscriptionResult with text and timestamps
            video_duration: Total video duration in seconds
            max_clips: Maximum clips to identify
            min_duration: Minimum clip duration
            max_duration: Maximum clip duration
            language: Language for titles/descriptions
            progress_callback: Optional callback for progress updates
            
        Returns:
            AnalysisResult with identified clips
        """
        def update_progress(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)
        
        try:
            from openai import OpenAI
        except ImportError:
            raise AnalysisError(
                "OpenAI SDK not installed. Install with: pip install openai"
            )
        
        api_key = self._get_api_key()
        
        # Create client with optional custom base URL
        client_kwargs = {"api_key": api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        
        client = OpenAI(**client_kwargs)
        
        model = self.get_model()
        update_progress(f"Analyzing with {model}...")
        
        # Format transcript with timestamps
        formatted_transcript = format_transcript_with_timestamps(transcription)
        
        # Build prompt
        prompt = build_analysis_prompt(
            transcript=formatted_transcript,
            duration=video_duration,
            max_clips=max_clips,
            min_duration=min_duration,
            max_duration=max_duration,
            language=language
        )
        
        # Run API call in thread pool
        loop = asyncio.get_event_loop()
        
        try:
            response = await loop.run_in_executor(
                None,
                lambda: self._do_analyze(client, model, prompt)
            )
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                raise AnalysisAPIError("Invalid OpenAI API key")
            elif "429" in error_msg or "rate" in error_msg.lower():
                raise AnalysisAPIError("OpenAI rate limit exceeded. Please wait and try again.")
            else:
                raise AnalysisAPIError(f"OpenAI API error: {error_msg}")
        
        update_progress("Parsing analysis results...")
        
        # Parse response
        clips = self._parse_response(response, transcription)
        
        return AnalysisResult(
            clips=clips,
            model=model,
            provider=self.name
        )
    
    def _do_analyze(self, client, model: str, prompt: str) -> str:
        """Perform the actual analysis (synchronous).
        
        Tries with JSON mode first, falls back to regular mode if not supported.
        """
        # Try with JSON mode first (OpenAI native models support this)
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert video editor who identifies viral-worthy moments. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if content:
                return content
        except Exception as e:
            error_str = str(e).lower()
            # If JSON mode not supported, try without it
            if "json" in error_str or "response_format" in error_str or "not supported" in error_str:
                pass  # Fall through to try without JSON mode
            else:
                raise  # Re-raise other errors
        
        # Fallback: Try without response_format (for models that don't support it)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert video editor who identifies viral-worthy moments. You MUST respond with valid JSON only. No markdown, no explanation, just pure JSON."
                },
                {
                    "role": "user",
                    "content": prompt + "\n\nIMPORTANT: Respond with valid JSON only. No markdown code blocks, no explanation."
                }
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        
        content = response.choices[0].message.content
        if not content:
            raise AnalysisAPIError(f"Model {model} returned empty response. Check if the model is available and supports chat completions.")
        
        return content
    
    def _parse_response(
        self, 
        response_text: str, 
        transcription: TranscriptionResult
    ) -> list[ClipData]:
        """Parse LLM response into ClipData list."""
        if not response_text or not response_text.strip():
            raise AnalysisParseError("Empty response from model. The model may not support this task or returned no content.")
        
        # Clean up response
        text = response_text.strip()
        
        # Handle thinking models (like MiniMax-M2.1, DeepSeek R1) that output <think>...</think>
        import re
        
        # Remove <think>...</think> blocks (thinking/reasoning content)
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        text = text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        
        # Try to find JSON object in the response
        # Some models output text before/after JSON
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            text = json_match.group(0)
        
        if not text.strip():
            raise AnalysisParseError("No JSON content found in response. Model may still be 'thinking' or returned only reasoning.")
        
        try:
            data = json.loads(text)
            
            if "clips" not in data:
                raise AnalysisParseError(f"Response missing 'clips' field. Got keys: {list(data.keys())}")
            
            clips: list[ClipData] = []
            for clip_data in data["clips"]:
                start_time = float(clip_data.get("start_time", 0))
                end_time = float(clip_data.get("end_time", 0))
                
                if end_time <= start_time:
                    continue
                
                # Use shared helper function for caption extraction
                captions = get_captions_for_range(
                    transcription, start_time, end_time
                )
                
                clips.append(ClipData(
                    start_time=start_time,
                    end_time=end_time,
                    title=str(clip_data.get("title", ""))[:60],
                    description=str(clip_data.get("description", ""))[:200],
                    captions=captions
                ))
            
            return clips
            
        except json.JSONDecodeError as e:
            # Show first 200 chars of response for debugging
            preview = text[:200] + "..." if len(text) > 200 else text
            raise AnalysisParseError(f"Invalid JSON response: {e}\nResponse preview: {preview}")
