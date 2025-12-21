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
)


class OpenAIAnalyzer(BaseAnalyzer):
    """OpenAI LLM analysis service.
    
    Features:
    - High quality analysis
    - Large context windows
    - Paid service
    
    Models:
    - gpt-4o: Best quality
    - gpt-4o-mini: Good balance of quality and cost
    - gpt-4-turbo: Previous generation
    """
    
    SUPPORTED_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ]
    
    @property
    def name(self) -> str:
        return "OpenAI"
    
    @property
    def default_model(self) -> str:
        return "gpt-4o-mini"
    
    def is_available(self) -> bool:
        """Check if OpenAI API key is available."""
        return bool(self.api_key or os.environ.get("OPENAI_API_KEY"))
    
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
        client = OpenAI(api_key=api_key)
        
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
            response_format={"type": "json_object"}
        )
        
        return response.choices[0].message.content
    
    def _parse_response(
        self, 
        response_text: str, 
        transcription: TranscriptionResult
    ) -> list[ClipData]:
        """Parse LLM response into ClipData list."""
        try:
            data = json.loads(response_text)
            
            if "clips" not in data:
                raise AnalysisParseError("Response missing 'clips' field")
            
            clips: list[ClipData] = []
            for clip_data in data["clips"]:
                start_time = float(clip_data.get("start_time", 0))
                end_time = float(clip_data.get("end_time", 0))
                
                if end_time <= start_time:
                    continue
                
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
