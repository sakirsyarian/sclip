"""Ollama local LLM analysis service.

Uses Ollama for local LLM inference. Runs entirely offline.

Requirements: Ollama must be installed and running locally.
https://ollama.ai
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


class OllamaAnalyzer(BaseAnalyzer):
    """Ollama local LLM analysis service.
    
    Features:
    - Runs entirely offline
    - No API key needed
    - Many model options
    - Privacy-focused
    
    Popular Models:
    - llama3.2: Meta's latest Llama
    - mistral: Mistral 7B
    - mixtral: Mistral MoE
    - gemma2: Google's Gemma 2
    - qwen2.5: Alibaba's Qwen
    """
    
    POPULAR_MODELS = [
        "llama3.2",
        "llama3.1",
        "mistral",
        "mixtral",
        "gemma2",
        "qwen2.5",
        "phi3",
    ]
    
    def __init__(
        self, 
        api_key: str | None = None, 
        model: str | None = None,
        host: str | None = None,
        **kwargs
    ):
        """Initialize Ollama analyzer.
        
        Args:
            api_key: Not used for Ollama
            model: Model name to use
            host: Ollama server host (default: http://localhost:11434)
        """
        super().__init__(api_key=api_key, model=model, **kwargs)
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    
    @property
    def name(self) -> str:
        return "Ollama"
    
    @property
    def default_model(self) -> str:
        return "llama3.2"
    
    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            import httpx
            response = httpx.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
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
        """Analyze transcript using Ollama.
        
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
            import httpx
        except ImportError:
            raise AnalysisError(
                "httpx not installed. Install with: pip install httpx"
            )
        
        # Check if Ollama is running
        if not self.is_available():
            raise AnalysisAPIError(
                f"Ollama is not running at {self.host}. "
                "Please start Ollama with: ollama serve"
            )
        
        model = self.get_model()
        update_progress(f"Analyzing with Ollama ({model})...")
        
        # Check if model is available
        await self._ensure_model_available(model, update_progress)
        
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
        
        # Run API call
        try:
            response = await self._do_analyze(model, prompt, update_progress)
        except Exception as e:
            raise AnalysisAPIError(f"Ollama error: {e}")
        
        update_progress("Parsing analysis results...")
        
        # Parse response
        clips = self._parse_response(response, transcription)
        
        return AnalysisResult(
            clips=clips,
            model=model,
            provider=self.name
        )
    
    async def _ensure_model_available(
        self, 
        model: str, 
        update_progress: Callable[[str], None]
    ) -> None:
        """Check if model is available, pull if not."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            # Check available models
            response = await client.get(f"{self.host}/api/tags")
            if response.status_code != 200:
                raise AnalysisAPIError("Failed to get Ollama models")
            
            models = response.json().get("models", [])
            model_names = [m.get("name", "").split(":")[0] for m in models]
            
            if model not in model_names and f"{model}:latest" not in [m.get("name") for m in models]:
                update_progress(f"Pulling model {model}... (this may take a while)")
                
                # Pull the model
                async with client.stream(
                    "POST",
                    f"{self.host}/api/pull",
                    json={"name": model},
                    timeout=None
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                status = data.get("status", "")
                                if "pulling" in status.lower():
                                    update_progress(f"Pulling {model}: {status}")
                            except json.JSONDecodeError:
                                pass
    
    async def _do_analyze(
        self, 
        model: str, 
        prompt: str,
        update_progress: Callable[[str], None]
    ) -> str:
        """Perform the actual analysis."""
        import httpx
        
        system_prompt = (
            "You are an expert video editor who identifies viral-worthy moments. "
            "Always respond with valid JSON only, no additional text."
        )
        
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{self.host}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 4096,
                    }
                }
            )
            
            if response.status_code != 200:
                raise AnalysisAPIError(f"Ollama returned status {response.status_code}")
            
            data = response.json()
            return data.get("response", "")
    
    def _parse_response(
        self, 
        response_text: str, 
        transcription: TranscriptionResult
    ) -> list[ClipData]:
        """Parse LLM response into ClipData list."""
        try:
            # Clean up response
            json_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if json_text.startswith("```"):
                lines = json_text.split("\n")
                lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                json_text = "\n".join(lines)
            
            data = json.loads(json_text)
            
            if "clips" not in data:
                raise AnalysisParseError("Response missing 'clips' field")
            
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
            raise AnalysisParseError(f"Invalid JSON response: {e}")
