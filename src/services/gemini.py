"""Gemini AI service for video analysis and clip identification.

This module provides the GeminiClient class for interacting with Google's
Gemini API to analyze videos and identify viral-worthy moments.

Key Features:
    - Video upload and analysis via Gemini API
    - Automatic chunking for videos > 30 minutes
    - Retry logic with exponential backoff
    - JSON response parsing and validation
    - Word-level caption extraction

API Usage:
    The module uses the google-genai SDK to:
    1. Upload video files to Gemini's file storage
    2. Wait for video processing to complete
    3. Send analysis prompt with the video
    4. Parse JSON response with clip data

Chunking Strategy:
    For videos longer than 30 minutes (Gemini's context limit):
    1. Split video into overlapping chunks
    2. Analyze each chunk separately
    3. Merge and deduplicate results
    4. Return top clips by engagement potential

Usage:
    from src.services.gemini import GeminiClient, analyze_video
    
    # Using the client directly
    client = GeminiClient(api_key="...", model="gemini-2.0-flash")
    response = await client.analyze_video(
        video_path="video.mp4",
        max_clips=5,
        min_duration=45,
        max_duration=180,
        language="en"
    )
    
    # Using the convenience function
    response = await analyze_video(
        api_key="...",
        video_path="video.mp4"
    )
"""

import asyncio
import json
import os
import re
import tempfile
from typing import Callable

from google import genai
from google.genai import types

from src.types import GeminiResponse, ClipData, CaptionSegment
from src.utils.logger import get_logger


# Analysis prompt template for Gemini
# This prompt instructs Gemini to analyze the video and identify viral moments
# The response format is strictly JSON for reliable parsing
ANALYSIS_PROMPT = """
Analyze this video and identify the most engaging, viral-worthy moments.

Requirements:
- Find up to {max_clips} clips
- Each clip should be {min_duration}-{max_duration} seconds long
- Focus on moments with high engagement potential:
  - Surprising statements or revelations
  - Emotional peaks (humor, inspiration, controversy)
  - Quotable soundbites
  - Story climaxes or plot twists
  - Expert insights or unique perspectives

For each clip, provide:
1. Precise start and end timestamps (in seconds, with decimals)
2. A catchy, clickbait-style title (max 60 chars)
3. An SEO-optimized description (max 200 chars)
4. ACCURATE word-by-word captions with precise timestamps

CRITICAL CAPTION RULES:
- Transcribe EXACTLY what is spoken - do not paraphrase or summarize
- Each caption segment should contain ONLY 1-2 words maximum
- Timestamps must be precise to match when each word is spoken
- Listen carefully to the audio and transcribe accurately
- Every single word must have its own timing

Language for captions: {language}

Return ONLY valid JSON in this exact format:
{{
  "clips": [
    {{
      "start_time": 125.5,
      "end_time": 185.2,
      "title": "Catchy title here",
      "description": "SEO description here",
      "captions": [
        {{"start": 125.5, "end": 125.9, "text": "Hello"}},
        {{"start": 125.9, "end": 126.3, "text": "everyone"}},
        {{"start": 126.3, "end": 126.8, "text": "today"}},
        {{"start": 126.8, "end": 127.2, "text": "we"}},
        {{"start": 127.2, "end": 127.6, "text": "will"}}
      ]
    }}
  ]
}}
"""


# Custom exception classes for specific error conditions
# These allow callers to handle different error types appropriately

class GeminiError(Exception):
    """Base exception for Gemini service errors."""
    pass


class GeminiAPIError(GeminiError):
    """Error from Gemini API (rate limit, invalid key, network issues, etc)."""
    pass


class GeminiParseError(GeminiError):
    """Error parsing Gemini response (invalid JSON, missing fields, etc)."""
    pass


class GeminiUploadError(GeminiError):
    """Error uploading video to Gemini (file too large, unsupported format, etc)."""
    pass


def build_analysis_prompt(
    max_clips: int,
    min_duration: int,
    max_duration: int,
    language: str
) -> str:
    """Build prompt for Gemini analysis.
    
    Args:
        max_clips: Maximum number of clips to identify
        min_duration: Minimum clip duration in seconds
        max_duration: Maximum clip duration in seconds
        language: Language code for captions (e.g., 'en', 'id')
        
    Returns:
        Formatted prompt string
    """
    return ANALYSIS_PROMPT.format(
        max_clips=max_clips,
        min_duration=min_duration,
        max_duration=max_duration,
        language=language
    )


def _fix_json_escapes(json_text: str) -> str:
    """Fix common invalid JSON escape sequences from Gemini.
    
    Gemini sometimes returns JSON with invalid escape sequences like:
    - \\x (should be \\\\x or removed)
    - \\' (should be ' in JSON)
    - Unescaped backslashes before non-escape characters
    
    Args:
        json_text: Raw JSON text that may contain invalid escapes
        
    Returns:
        Fixed JSON text with valid escape sequences
    """
    # Fix invalid escape sequences by replacing single backslash 
    # followed by invalid escape chars with double backslash or removing
    # Valid JSON escapes: \", \\, \/, \b, \f, \n, \r, \t, \uXXXX
    
    result = []
    i = 0
    while i < len(json_text):
        if json_text[i] == '\\' and i + 1 < len(json_text):
            next_char = json_text[i + 1]
            # Valid JSON escape characters
            if next_char in '"\\bfnrt/':
                result.append(json_text[i:i+2])
                i += 2
            # Unicode escape \uXXXX
            elif next_char == 'u' and i + 5 < len(json_text):
                result.append(json_text[i:i+6])
                i += 6
            # Invalid escapes - remove the backslash, keep the character
            else:
                result.append(next_char)
                i += 2
        else:
            result.append(json_text[i])
            i += 1
    
    return ''.join(result)


def parse_response(response_text: str) -> GeminiResponse:
    """Parse JSON response from Gemini into GeminiResponse.
    
    Args:
        response_text: Raw JSON text from Gemini API
        
    Returns:
        Parsed GeminiResponse with clips data
        
    Raises:
        GeminiParseError: If response cannot be parsed
    """
    logger = get_logger()
    
    try:
        # Try to extract JSON from response (handle markdown code blocks)
        json_text = response_text.strip()
        
        # Remove markdown code blocks if present
        if json_text.startswith("```"):
            # Find the end of the code block
            lines = json_text.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            json_text = "\n".join(lines)
        
        # Fix common JSON escape issues from Gemini
        # Replace invalid escape sequences with valid ones
        json_text = _fix_json_escapes(json_text)
        
        data = json.loads(json_text)
        
        # Validate structure
        if "clips" not in data:
            raise GeminiParseError("Response missing 'clips' field")
        
        if not isinstance(data["clips"], list):
            raise GeminiParseError("'clips' field must be a list")
        
        # Validate and normalize each clip
        clips: list[ClipData] = []
        for i, clip in enumerate(data["clips"]):
            try:
                validated_clip = _validate_clip(clip, i)
                clips.append(validated_clip)
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(f"Skipping invalid clip {i}: {e}")
                continue
        
        return GeminiResponse(clips=clips)
        
    except json.JSONDecodeError as e:
        raise GeminiParseError(f"Invalid JSON response: {e}")


def _validate_clip(clip: dict, index: int) -> ClipData:
    """Validate and normalize a single clip from Gemini response.
    
    Args:
        clip: Raw clip dictionary from response
        index: Clip index for error messages
        
    Returns:
        Validated ClipData
        
    Raises:
        KeyError: If required field is missing
        TypeError: If field has wrong type
        ValueError: If field value is invalid
    """
    # Required fields
    start_time = float(clip["start_time"])
    end_time = float(clip["end_time"])
    title = str(clip["title"])
    description = str(clip["description"])
    
    # Validate timestamps
    if start_time < 0:
        raise ValueError(f"start_time must be >= 0, got {start_time}")
    if end_time <= start_time:
        raise ValueError(f"end_time ({end_time}) must be > start_time ({start_time})")
    
    # Validate and normalize captions
    captions: list[CaptionSegment] = []
    raw_captions = clip.get("captions", [])
    
    if isinstance(raw_captions, list):
        for cap in raw_captions:
            if isinstance(cap, dict) and "start" in cap and "end" in cap and "text" in cap:
                captions.append(CaptionSegment(
                    start=float(cap["start"]),
                    end=float(cap["end"]),
                    text=str(cap["text"])
                ))
    
    return ClipData(
        start_time=start_time,
        end_time=end_time,
        title=title[:60],  # Truncate to max length
        description=description[:200],  # Truncate to max length
        captions=captions
    )


class GeminiClient:
    """Client for interacting with Google Gemini API for video analysis.
    
    Uses the google-genai SDK to upload videos and analyze them for
    viral-worthy moments. Supports both single-shot analysis and
    chunked analysis for long videos.
    
    Attributes:
        client: The google-genai Client instance
        model: Gemini model name to use (e.g., "gemini-2.0-flash")
    
    Example:
        client = GeminiClient(api_key="...", model="gemini-2.0-flash")
        
        # Analyze a short video
        response = await client.analyze_video("video.mp4", max_clips=5)
        
        # Analyze a long video with chunking
        response = await client.analyze_video_chunked(
            "long_video.mp4",
            video_duration=7200,  # 2 hours
            max_clips=10
        )
    """
    
    # Default chunk duration for long videos (30 minutes in seconds)
    # This is based on Gemini's context window limitations
    DEFAULT_CHUNK_DURATION = 1800
    
    # Overlap between chunks to catch moments at boundaries (2 minutes)
    # This prevents missing clips that span chunk boundaries
    CHUNK_OVERLAP = 120
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        """Initialize Gemini client.
        
        Args:
            api_key: Google Gemini API key
            model: Model name to use (default: gemini-2.0-flash)
        """
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self._logger = get_logger()
    
    async def analyze_video(
        self,
        video_path: str,
        max_clips: int = 5,
        min_duration: int = 45,
        max_duration: int = 180,
        language: str = "id",
        progress_callback: Callable[[str], None] | None = None
    ) -> GeminiResponse:
        """Upload video to Gemini and analyze for viral moments.
        
        Args:
            video_path: Path to video file
            max_clips: Maximum number of clips to identify
            min_duration: Minimum clip duration in seconds
            max_duration: Maximum clip duration in seconds
            language: Language code for captions
            progress_callback: Optional callback for progress updates
            
        Returns:
            GeminiResponse with identified clips
            
        Raises:
            GeminiUploadError: If video upload fails
            GeminiAPIError: If API call fails
            GeminiParseError: If response parsing fails
        """
        def update_progress(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)
            self._logger.debug(msg)
        
        # Upload video file
        update_progress("Uploading video to Gemini...")
        try:
            video_file = await self._upload_video(video_path)
        except Exception as e:
            raise GeminiUploadError(f"Failed to upload video: {e}")
        
        # Wait for processing
        update_progress("Waiting for video processing...")
        try:
            video_file = await self._wait_for_processing(video_file)
        except Exception as e:
            raise GeminiAPIError(f"Video processing failed: {e}")
        
        # Generate content with video
        update_progress("Analyzing video for viral moments...")
        prompt = build_analysis_prompt(max_clips, min_duration, max_duration, language)
        
        try:
            response = await self._generate_content(video_file, prompt)
        except Exception as e:
            raise GeminiAPIError(f"Content generation failed: {e}")
        
        # Parse response
        update_progress("Parsing analysis results...")
        return parse_response(response)
    
    async def _upload_video(self, video_path: str):
        """Upload video file to Gemini.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Uploaded file object
        """
        # Run synchronous upload in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.client.files.upload(file=video_path)
        )
    
    async def _wait_for_processing(self, video_file, timeout: int = 300):
        """Wait for video to finish processing.
        
        Args:
            video_file: Uploaded file object
            timeout: Maximum wait time in seconds
            
        Returns:
            Processed file object
            
        Raises:
            GeminiAPIError: If processing times out or fails
        """
        elapsed = 0
        poll_interval = 2
        
        while elapsed < timeout:
            # Check file state
            loop = asyncio.get_event_loop()
            video_file = await loop.run_in_executor(
                None,
                lambda: self.client.files.get(name=video_file.name)
            )
            
            state = getattr(video_file, 'state', None)
            if state is None:
                # No state attribute means processing is complete
                return video_file
            
            state_str = str(state).upper()
            if "ACTIVE" in state_str or "COMPLETED" in state_str:
                return video_file
            elif "FAILED" in state_str:
                raise GeminiAPIError("Video processing failed")
            elif "PROCESSING" in state_str:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
            else:
                # Unknown state, assume complete
                return video_file
        
        raise GeminiAPIError(f"Video processing timed out after {timeout}s")
    
    async def _generate_content(self, video_file, prompt: str) -> str:
        """Generate content using Gemini with video and prompt.
        
        Args:
            video_file: Processed video file object
            prompt: Analysis prompt
            
        Returns:
            Response text from Gemini
        """
        loop = asyncio.get_event_loop()
        
        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=self.model,
                contents=[video_file, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
        )
        
        return response.text

    async def analyze_video_chunked(
        self,
        video_path: str,
        video_duration: float,
        max_clips: int = 5,
        min_duration: int = 45,
        max_duration: int = 180,
        language: str = "id",
        chunk_duration: int | None = None,
        progress_callback: Callable[[str], None] | None = None
    ) -> GeminiResponse:
        """Process long video in chunks for videos exceeding context window limits.
        
        For videos longer than 30 minutes, this method splits the video into
        overlapping chunks, analyzes each chunk separately, then merges and
        deduplicates the results.
        
        Args:
            video_path: Path to video file
            video_duration: Total duration of the video in seconds
            max_clips: Maximum number of clips to identify (total across all chunks)
            min_duration: Minimum clip duration in seconds
            max_duration: Maximum clip duration in seconds
            language: Language code for captions
            chunk_duration: Duration of each chunk in seconds (default: 1800 = 30 min)
            progress_callback: Optional callback for progress updates
            
        Returns:
            GeminiResponse with identified clips (merged and deduplicated)
            
        Raises:
            GeminiUploadError: If video upload fails
            GeminiAPIError: If API call fails
            GeminiParseError: If response parsing fails
        """
        from src.utils.ffmpeg import run_ffmpeg, find_ffmpeg
        
        chunk_duration = chunk_duration or self.DEFAULT_CHUNK_DURATION
        
        def update_progress(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)
            self._logger.debug(msg)
        
        # Calculate chunks needed
        chunks = self._calculate_chunks(video_duration, chunk_duration)
        num_chunks = len(chunks)
        
        if num_chunks == 1:
            # Video fits in single chunk, use regular analysis
            update_progress("Video fits in single chunk, using standard analysis...")
            return await self.analyze_video(
                video_path=video_path,
                max_clips=max_clips,
                min_duration=min_duration,
                max_duration=max_duration,
                language=language,
                progress_callback=progress_callback
            )
        
        update_progress(f"Video requires {num_chunks} chunks for analysis...")
        
        # Calculate clips per chunk (distribute evenly, with extra for merging)
        clips_per_chunk = max(3, (max_clips * 2) // num_chunks + 1)
        
        all_clips: list[ClipData] = []
        temp_files: list[str] = []
        
        try:
            ffmpeg_path = find_ffmpeg()
            
            for i, (start_time, end_time) in enumerate(chunks):
                chunk_num = i + 1
                update_progress(f"Processing chunk {chunk_num}/{num_chunks} ({start_time:.0f}s - {end_time:.0f}s)...")
                
                # Extract chunk to temp file
                temp_chunk_path = await self._extract_chunk(
                    video_path=video_path,
                    start_time=start_time,
                    end_time=end_time,
                    chunk_index=i,
                    ffmpeg_path=ffmpeg_path
                )
                temp_files.append(temp_chunk_path)
                
                # Analyze chunk
                update_progress(f"Analyzing chunk {chunk_num}/{num_chunks}...")
                try:
                    chunk_response = await self.analyze_video(
                        video_path=temp_chunk_path,
                        max_clips=clips_per_chunk,
                        min_duration=min_duration,
                        max_duration=max_duration,
                        language=language,
                        progress_callback=None  # Suppress nested progress
                    )
                    
                    # Adjust timestamps to original video timeline
                    adjusted_clips = self._adjust_clip_timestamps(
                        chunk_response["clips"],
                        offset=start_time
                    )
                    all_clips.extend(adjusted_clips)
                    
                except (GeminiAPIError, GeminiParseError) as e:
                    self._logger.warning(f"Chunk {chunk_num} analysis failed: {e}")
                    # Continue with other chunks
                    continue
            
            if not all_clips:
                raise GeminiAPIError("All chunk analyses failed")
            
            # Merge and deduplicate clips
            update_progress("Merging and deduplicating clips...")
            merged_clips = self._merge_and_deduplicate_clips(all_clips, max_clips)
            
            return GeminiResponse(clips=merged_clips)
            
        finally:
            # Cleanup temp chunk files
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except OSError:
                    pass
    
    def _calculate_chunks(
        self,
        video_duration: float,
        chunk_duration: int
    ) -> list[tuple[float, float]]:
        """Calculate chunk boundaries with overlap.
        
        Args:
            video_duration: Total video duration in seconds
            chunk_duration: Target duration for each chunk
            
        Returns:
            List of (start_time, end_time) tuples for each chunk
        """
        chunks: list[tuple[float, float]] = []
        current_start = 0.0
        
        while current_start < video_duration:
            # Calculate end time for this chunk
            chunk_end = min(current_start + chunk_duration, video_duration)
            chunks.append((current_start, chunk_end))
            
            # Move to next chunk with overlap
            # Don't overlap if this is the last chunk
            if chunk_end >= video_duration:
                break
            
            current_start = chunk_end - self.CHUNK_OVERLAP
            
            # Ensure we don't create tiny final chunks
            remaining = video_duration - current_start
            if remaining < chunk_duration * 0.3:  # Less than 30% of chunk size
                # Extend previous chunk to end instead
                if chunks:
                    chunks[-1] = (chunks[-1][0], video_duration)
                break
        
        return chunks
    
    async def _extract_chunk(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        chunk_index: int,
        ffmpeg_path: str | None = None
    ) -> str:
        """Extract a chunk from the video using FFmpeg.
        
        Args:
            video_path: Path to source video
            start_time: Start time in seconds
            end_time: End time in seconds
            chunk_index: Index of this chunk (for temp file naming)
            ffmpeg_path: Optional path to FFmpeg executable
            
        Returns:
            Path to extracted chunk file
            
        Raises:
            GeminiAPIError: If extraction fails
        """
        from src.utils.ffmpeg import run_ffmpeg
        
        # Create temp file for chunk
        temp_dir = tempfile.gettempdir()
        chunk_filename = f"sclip_chunk_{chunk_index}_{os.getpid()}.mp4"
        chunk_path = os.path.join(temp_dir, chunk_filename)
        
        duration = end_time - start_time
        
        # FFmpeg command to extract chunk
        # Using -ss before -i for fast seeking, then -t for duration
        args = [
            "-y",  # Overwrite output
            "-ss", str(start_time),
            "-i", video_path,
            "-t", str(duration),
            "-c", "copy",  # Copy streams without re-encoding (fast)
            "-avoid_negative_ts", "make_zero",
            chunk_path
        ]
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: run_ffmpeg(args, ffmpeg_path=ffmpeg_path, timeout=300)
        )
        
        if not result.success:
            # Try with re-encoding if copy fails
            args = [
                "-y",
                "-ss", str(start_time),
                "-i", video_path,
                "-t", str(duration),
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-c:a", "aac",
                chunk_path
            ]
            
            result = await loop.run_in_executor(
                None,
                lambda: run_ffmpeg(args, ffmpeg_path=ffmpeg_path, timeout=600)
            )
            
            if not result.success:
                raise GeminiAPIError(f"Failed to extract video chunk: {result.stderr}")
        
        return chunk_path
    
    def _adjust_clip_timestamps(
        self,
        clips: list[ClipData],
        offset: float
    ) -> list[ClipData]:
        """Adjust clip timestamps by adding an offset.
        
        Args:
            clips: List of clips with timestamps relative to chunk
            offset: Time offset to add (chunk start time in original video)
            
        Returns:
            List of clips with adjusted timestamps
        """
        adjusted: list[ClipData] = []
        
        for clip in clips:
            adjusted_clip = ClipData(
                start_time=clip["start_time"] + offset,
                end_time=clip["end_time"] + offset,
                title=clip["title"],
                description=clip["description"],
                captions=[
                    CaptionSegment(
                        start=cap["start"] + offset,
                        end=cap["end"] + offset,
                        text=cap["text"]
                    )
                    for cap in clip.get("captions", [])
                ]
            )
            adjusted.append(adjusted_clip)
        
        return adjusted
    
    def _merge_and_deduplicate_clips(
        self,
        clips: list[ClipData],
        max_clips: int
    ) -> list[ClipData]:
        """Merge overlapping clips and deduplicate results.
        
        Clips are considered duplicates if they overlap significantly
        (more than 50% overlap). When duplicates are found, the one
        with the longer duration is kept.
        
        Args:
            clips: List of all clips from all chunks
            max_clips: Maximum number of clips to return
            
        Returns:
            Deduplicated and sorted list of clips
        """
        if not clips:
            return []
        
        # Sort by start time
        sorted_clips = sorted(clips, key=lambda c: c["start_time"])
        
        # Deduplicate overlapping clips
        deduplicated: list[ClipData] = []
        
        for clip in sorted_clips:
            is_duplicate = False
            
            for i, existing in enumerate(deduplicated):
                overlap = self._calculate_overlap(clip, existing)
                
                # If more than 50% overlap, consider it a duplicate
                clip_duration = clip["end_time"] - clip["start_time"]
                existing_duration = existing["end_time"] - existing["start_time"]
                min_duration = min(clip_duration, existing_duration)
                
                if overlap > min_duration * 0.5:
                    is_duplicate = True
                    # Keep the longer clip
                    if clip_duration > existing_duration:
                        deduplicated[i] = clip
                    break
            
            if not is_duplicate:
                deduplicated.append(clip)
        
        # Sort by start time and limit to max_clips
        deduplicated.sort(key=lambda c: c["start_time"])
        
        return deduplicated[:max_clips]
    
    def _calculate_overlap(self, clip1: ClipData, clip2: ClipData) -> float:
        """Calculate the overlap duration between two clips.
        
        Args:
            clip1: First clip
            clip2: Second clip
            
        Returns:
            Overlap duration in seconds (0 if no overlap)
        """
        start1, end1 = clip1["start_time"], clip1["end_time"]
        start2, end2 = clip2["start_time"], clip2["end_time"]
        
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)
        
        if overlap_start < overlap_end:
            return overlap_end - overlap_start
        return 0.0


async def with_retry(
    func: Callable,
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (GeminiAPIError,)
):
    """Execute async function with exponential backoff retry.
    
    Args:
        func: Async function to execute
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for wait time between retries
        retryable_exceptions: Tuple of exception types to retry on
        
    Returns:
        Result from successful function execution
        
    Raises:
        Exception: The last exception if all retries fail
    """
    logger = get_logger()
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func()
        except retryable_exceptions as e:
            last_exception = e
            if attempt == max_retries - 1:
                raise
            
            wait_time = backoff_factor ** attempt
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)
    
    raise last_exception


# Convenience function for simple usage
async def analyze_video(
    api_key: str,
    video_path: str,
    max_clips: int = 5,
    min_duration: int = 45,
    max_duration: int = 180,
    language: str = "id",
    model: str = "gemini-2.0-flash",
    progress_callback: Callable[[str], None] | None = None
) -> GeminiResponse:
    """Analyze video for viral moments using Gemini AI.
    
    Convenience function that creates a client and analyzes the video.
    
    Args:
        api_key: Google Gemini API key
        video_path: Path to video file
        max_clips: Maximum number of clips to identify
        min_duration: Minimum clip duration in seconds
        max_duration: Maximum clip duration in seconds
        language: Language code for captions
        model: Gemini model to use
        progress_callback: Optional callback for progress updates
        
    Returns:
        GeminiResponse with identified clips
    """
    client = GeminiClient(api_key=api_key, model=model)
    return await client.analyze_video(
        video_path=video_path,
        max_clips=max_clips,
        min_duration=min_duration,
        max_duration=max_duration,
        language=language,
        progress_callback=progress_callback
    )


async def analyze_video_chunked(
    api_key: str,
    video_path: str,
    video_duration: float,
    max_clips: int = 5,
    min_duration: int = 45,
    max_duration: int = 180,
    language: str = "en",
    model: str = "gemini-2.0-flash",
    chunk_duration: int | None = None,
    progress_callback: Callable[[str], None] | None = None
) -> GeminiResponse:
    """Analyze long video for viral moments using chunked processing.
    
    Convenience function that creates a client and analyzes a long video
    by splitting it into chunks.
    
    Args:
        api_key: Google Gemini API key
        video_path: Path to video file
        video_duration: Total duration of the video in seconds
        max_clips: Maximum number of clips to identify
        min_duration: Minimum clip duration in seconds
        max_duration: Maximum clip duration in seconds
        language: Language code for captions
        model: Gemini model to use
        chunk_duration: Duration of each chunk in seconds (default: 1800 = 30 min)
        progress_callback: Optional callback for progress updates
        
    Returns:
        GeminiResponse with identified clips (merged and deduplicated)
    """
    client = GeminiClient(api_key=api_key, model=model)
    return await client.analyze_video_chunked(
        video_path=video_path,
        video_duration=video_duration,
        max_clips=max_clips,
        min_duration=min_duration,
        max_duration=max_duration,
        language=language,
        chunk_duration=chunk_duration,
        progress_callback=progress_callback
    )


__all__ = [
    "GeminiClient",
    "GeminiError",
    "GeminiAPIError",
    "GeminiParseError",
    "GeminiUploadError",
    "build_analysis_prompt",
    "parse_response",
    "analyze_video",
    "analyze_video_chunked",
    "with_retry",
]
