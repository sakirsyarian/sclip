"""DeepSeek LLM analysis service.

Uses DeepSeek's API for viral moment analysis.
Very affordable pricing ($0.028-0.28/M tokens).
OpenAI-compatible API.

API Documentation: https://api-docs.deepseek.com/
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
)


class DeepSeekAnalyzer(BaseAnalyzer):
    """DeepSeek LLM analysis service.
    
    Features:
    - Very affordable pricing
    - OpenAI-compatible API
    - High quality reasoning (DeepSeek-V3)
    - Reasoning model available (deepseek-reasoner)
    
    Models:
    - deepseek-chat: Latest V3 model, best for general use (default)
    - deepseek-reasoner: R1 reasoning model, for complex analysis
    """
    
    SUPPORTED_MODELS = [
        "deepseek-chat",      # DeepSeek-V3, general purpose
        "deepseek-reasoner",  # DeepSeek-R1, reasoning
    ]
    
    API_BASE_URL = "https://api.deepseek.com"
    
    @property
    def name(self) -> str:
        return "DeepSeek"
    
    @property
    def default_model(self) -> str:
        return "deepseek-chat"
    
    def is_available(self) -> bool:
        """Check if DeepSeek API key is available."""
        return bool(self.api_key or os.environ.get("DEEPSEEK_API_KEY"))
    
    def _get_api_key(self) -> str:
        """Get API key from instance or environment."""
        key = self.api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise AnalysisAPIError(
                "DeepSeek API key not found. Set DEEPSEEK_API_KEY environment variable "
                "or pass api_key parameter. Get API key at https://platform.deepseek.com"
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
        """Analyze transcript using DeepSeek LLM.
        
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
        
        # DeepSeek uses OpenAI-compatible API
        client = OpenAI(
            api_key=api_key,
            base_url=self.API_BASE_URL
        )
        
        model = self.get_model()
        update_progress(f"Analyzing with DeepSeek {model}...")
        
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
                raise AnalysisAPIError("Invalid DeepSeek API key")
            elif "429" in error_msg or "rate" in error_msg.lower():
                raise AnalysisAPIError("DeepSeek rate limit exceeded. Please wait and try again.")
            elif "insufficient" in error_msg.lower() or "balance" in error_msg.lower():
                raise AnalysisAPIError("DeepSeek account has insufficient balance.")
            else:
                raise AnalysisAPIError(f"DeepSeek API error: {error_msg}")
        
        update_progress("Parsing analysis results...")
        
        # Parse response
        clips = self._parse_response(response, transcription)
        
        return AnalysisResult(
            clips=clips,
            model=model,
            provider=self.name
        )
    
    def _do_analyze(self, client, model: str, prompt: str) -> str:
        """Perform the actual analysis (synchronous)."""
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
        )
        
        return response.choices[0].message.content

    def _parse_response(
        self, 
        response_text: str, 
        transcription: TranscriptionResult
    ) -> list[ClipData]:
        """Parse LLM response into ClipData list."""
        try:
            # Clean up response - extract JSON
            json_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if json_text.startswith("```"):
                lines = json_text.split("\n")
                lines = lines[1:]  # Remove first line
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                json_text = "\n".join(lines)
            
            # Fix common JSON issues
            json_text = self._fix_json(json_text)
            
            data = json.loads(json_text)
            
            if "clips" not in data:
                raise AnalysisParseError("Response missing 'clips' field")
            
            clips: list[ClipData] = []
            for clip_data in data["clips"]:
                # Get timestamps
                start_time = float(clip_data.get("start_time", 0))
                end_time = float(clip_data.get("end_time", 0))
                
                # Validate timestamps
                if end_time <= start_time:
                    continue
                
                # Get captions from transcription for this time range
                captions = self._get_captions_for_range(
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
            raise AnalysisParseError(f"Invalid JSON response: {e}")
    
    def _fix_json(self, json_text: str) -> str:
        """Fix common JSON issues."""
        # Remove invalid escape sequences
        result = []
        i = 0
        while i < len(json_text):
            if json_text[i] == '\\' and i + 1 < len(json_text):
                next_char = json_text[i + 1]
                if next_char in '"\\bfnrt/':
                    result.append(json_text[i:i+2])
                    i += 2
                elif next_char == 'u' and i + 5 < len(json_text):
                    result.append(json_text[i:i+6])
                    i += 6
                else:
                    result.append(next_char)
                    i += 2
            else:
                result.append(json_text[i])
                i += 1
        
        return ''.join(result)
    
    def _get_captions_for_range(
        self,
        transcription: TranscriptionResult,
        start_time: float,
        end_time: float
    ) -> list[CaptionSegment]:
        """Extract captions for a specific time range."""
        captions: list[CaptionSegment] = []
        
        for word in transcription.words:
            # Include words that overlap with the time range
            # A word overlaps if it starts before end_time AND ends after start_time
            if word.start < end_time and word.end > start_time:
                # Clamp word times to clip boundaries
                word_start = max(word.start, start_time)
                word_end = min(word.end, end_time)
                
                captions.append(CaptionSegment(
                    start=word_start - start_time,
                    end=word_end - start_time,
                    text=word.word
                ))
        
        return captions
