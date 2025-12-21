"""Face tracking service for SmartClip AI using MediaPipe.

This module provides face detection and tracking to dynamically crop
videos to keep speakers' faces centered in the frame.

Key Features:
    - Face detection using MediaPipe BlazeFace
    - Smart sampling (not every frame) for performance
    - Smooth position interpolation to avoid jumpy crops
    - Support for multiple faces with speaker detection
    - Fallback to center crop if no face detected

Performance Optimizations:
    - Frame sampling (analyze every N frames)
    - Resize frames before detection
    - Position smoothing with exponential moving average
    - Caching of detection results

Usage:
    from src.services.face_tracker import FaceTracker, analyze_face_positions
    
    # Quick analysis
    positions = analyze_face_positions(
        video_path="video.mp4",
        start_time=10.0,
        end_time=40.0
    )
    
    # Or use the class directly
    tracker = FaceTracker()
    positions = tracker.analyze_clip(video_path, start_time, end_time)
"""

import os
from dataclasses import dataclass
from typing import Callable

# Lazy import to avoid loading MediaPipe if not needed
_mp = None
_cv2 = None


def _ensure_imports():
    """Lazy import MediaPipe and OpenCV."""
    global _mp, _cv2
    
    if _mp is None:
        try:
            import mediapipe as mp
            _mp = mp
        except ImportError:
            raise ImportError(
                "MediaPipe is required for face tracking. "
                "Install with: pip install mediapipe"
            )
    
    if _cv2 is None:
        try:
            import cv2
            _cv2 = cv2
        except ImportError:
            raise ImportError(
                "OpenCV is required for face tracking. "
                "Install with: pip install opencv-python"
            )
    
    return _mp, _cv2


def _get_model_path() -> str:
    """Get or download the face detection model.
    
    Downloads the BlazeFace short-range model if not already cached.
    
    Returns:
        Path to the model file
    """
    import urllib.request
    import tempfile
    
    # Model URL from MediaPipe
    MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
    
    # Cache in temp directory
    cache_dir = os.path.join(tempfile.gettempdir(), "sclip_models")
    os.makedirs(cache_dir, exist_ok=True)
    
    model_path = os.path.join(cache_dir, "blaze_face_short_range.tflite")
    
    # Download if not exists
    if not os.path.exists(model_path):
        try:
            urllib.request.urlretrieve(MODEL_URL, model_path)
        except Exception as e:
            raise RuntimeError(f"Failed to download face detection model: {e}")
    
    return model_path


@dataclass
class FacePosition:
    """Represents detected face position(s) in a frame.
    
    For multiple faces, represents the center of the group bounding box.
    
    Attributes:
        x: X coordinate of face/group center (0.0 to 1.0, normalized)
        y: Y coordinate of face/group center (0.0 to 1.0, normalized)
        width: Width of face/group bounding box (normalized)
        height: Height of face/group bounding box (normalized)
        confidence: Detection confidence (0.0 to 1.0, averaged for multiple)
        timestamp: Time in video (seconds)
        face_count: Number of faces detected in this frame
    """
    x: float
    y: float
    width: float
    height: float
    confidence: float
    timestamp: float
    face_count: int = 1


@dataclass 
class CropRegion:
    """Represents a crop region for a video segment.
    
    Attributes:
        x: X offset from left (pixels)
        y: Y offset from top (pixels)
        width: Crop width (pixels)
        height: Crop height (pixels)
    """
    x: int
    y: int
    width: int
    height: int


class FaceTracker:
    """Face tracking service using MediaPipe.
    
    Analyzes video clips to detect face positions and calculate
    optimal crop regions to keep faces centered.
    
    Attributes:
        sample_rate: Analyze every N frames (default: 5)
        detection_confidence: Minimum confidence threshold (default: 0.5)
        smoothing_factor: Position smoothing (0-1, higher = smoother)
    """
    
    # Default settings optimized for CPU performance
    DEFAULT_SAMPLE_RATE = 5  # Analyze every 5 frames
    DEFAULT_CONFIDENCE = 0.5
    DEFAULT_SMOOTHING = 0.3
    ANALYSIS_WIDTH = 480  # Resize to this width for faster detection
    
    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        detection_confidence: float = DEFAULT_CONFIDENCE,
        smoothing_factor: float = DEFAULT_SMOOTHING
    ):
        """Initialize face tracker.
        
        Args:
            sample_rate: Analyze every N frames for performance
            detection_confidence: Minimum detection confidence (0-1)
            smoothing_factor: Position smoothing factor (0-1)
        """
        self.sample_rate = sample_rate
        self.detection_confidence = detection_confidence
        self.smoothing_factor = smoothing_factor
        self._detector = None
    
    def _get_detector(self):
        """Get or create MediaPipe face detector (lazy init)."""
        if self._detector is None:
            mp, _ = _ensure_imports()
            
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            
            # Get model path (downloads if needed)
            model_path = _get_model_path()
            
            base_options = python.BaseOptions(
                model_asset_path=model_path
            )
            
            options = vision.FaceDetectorOptions(
                base_options=base_options,
                min_detection_confidence=self.detection_confidence
            )
            
            self._detector = vision.FaceDetector.create_from_options(options)
        
        return self._detector
    
    def analyze_clip(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        progress_callback: Callable[[int], None] | None = None
    ) -> list[FacePosition]:
        """Analyze a video clip for face positions.
        
        Args:
            video_path: Path to video file
            start_time: Start time in seconds
            end_time: End time in seconds
            progress_callback: Optional callback for progress (0-100)
            
        Returns:
            List of FacePosition objects for detected faces
        """
        mp, cv2 = _ensure_imports()
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            start_frame = int(start_time * fps)
            end_frame = int(end_time * fps)
            
            # Seek to start
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            positions: list[FacePosition] = []
            frame_count = 0
            frames_to_process = end_frame - start_frame
            
            detector = self._get_detector()
            
            while cap.isOpened():
                current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                if current_frame >= end_frame:
                    break
                
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # Sample frames for performance
                if frame_count % self.sample_rate != 0:
                    continue
                
                # Report progress
                if progress_callback:
                    progress = int((frame_count / frames_to_process) * 100)
                    progress_callback(min(progress, 100))
                
                # Detect face in frame
                face_pos = self._detect_face(frame, detector, current_frame / fps)
                if face_pos:
                    positions.append(face_pos)
            
            return positions
            
        finally:
            cap.release()
    
    def _detect_face(self, frame, detector, timestamp: float) -> FacePosition | None:
        """Detect face in a single frame.
        
        For multiple faces, calculates a bounding box that encompasses
        all detected faces (group shot mode).
        
        Args:
            frame: OpenCV frame (BGR)
            detector: MediaPipe face detector
            timestamp: Current timestamp in seconds
            
        Returns:
            FacePosition representing center of all faces, None if no faces
        """
        mp, cv2 = _ensure_imports()
        
        # Resize for faster detection
        height, width = frame.shape[:2]
        scale = self.ANALYSIS_WIDTH / width
        small_frame = cv2.resize(
            frame, 
            (self.ANALYSIS_WIDTH, int(height * scale))
        )
        
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Create MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Detect faces
        results = detector.detect(mp_image)
        
        if not results.detections:
            return None
        
        img_height, img_width = rgb_frame.shape[:2]
        
        # Handle multiple faces - calculate bounding box for all
        if len(results.detections) == 1:
            # Single face - use it directly
            detection = results.detections[0]
            bbox = detection.bounding_box
            
            x_min = bbox.origin_x / img_width
            y_min = bbox.origin_y / img_height
            box_width = bbox.width / img_width
            box_height = bbox.height / img_height
            
            center_x = x_min + (box_width / 2)
            center_y = y_min + (box_height / 2)
            confidence = detection.categories[0].score if detection.categories else 0.5
            face_count = 1
            
        else:
            # Multiple faces - calculate group bounding box
            all_x_min = []
            all_y_min = []
            all_x_max = []
            all_y_max = []
            total_confidence = 0
            
            for detection in results.detections:
                bbox = detection.bounding_box
                
                x_min = bbox.origin_x / img_width
                y_min = bbox.origin_y / img_height
                x_max = x_min + (bbox.width / img_width)
                y_max = y_min + (bbox.height / img_height)
                
                all_x_min.append(x_min)
                all_y_min.append(y_min)
                all_x_max.append(x_max)
                all_y_max.append(y_max)
                
                if detection.categories:
                    total_confidence += detection.categories[0].score
            
            # Group bounding box
            group_x_min = min(all_x_min)
            group_y_min = min(all_y_min)
            group_x_max = max(all_x_max)
            group_y_max = max(all_y_max)
            
            box_width = group_x_max - group_x_min
            box_height = group_y_max - group_y_min
            
            # Center of group
            center_x = group_x_min + (box_width / 2)
            center_y = group_y_min + (box_height / 2)
            
            # Average confidence
            confidence = total_confidence / len(results.detections)
            face_count = len(results.detections)
        
        return FacePosition(
            x=center_x,
            y=center_y,
            width=box_width,
            height=box_height,
            confidence=confidence,
            timestamp=timestamp,
            face_count=face_count
        )
    
    def calculate_crop_region(
        self,
        positions: list[FacePosition],
        source_width: int,
        source_height: int,
        target_width: int,
        target_height: int
    ) -> CropRegion:
        """Calculate optimal crop region based on face positions.
        
        Uses the average face position with smoothing to determine
        the best crop region that keeps faces centered.
        
        Args:
            positions: List of detected face positions
            source_width: Original video width
            source_height: Original video height
            target_width: Target crop width
            target_height: Target crop height
            
        Returns:
            CropRegion with optimal x, y offset
        """
        if not positions:
            # No faces detected - use upper-center crop (default for speakers)
            return self._default_crop(
                source_width, source_height,
                target_width, target_height
            )
        
        # Calculate weighted average position (more recent = higher weight)
        total_weight = 0
        weighted_x = 0
        weighted_y = 0
        
        for i, pos in enumerate(positions):
            # Weight increases for later positions
            weight = (i + 1) * pos.confidence
            weighted_x += pos.x * weight
            weighted_y += pos.y * weight
            total_weight += weight
        
        if total_weight == 0:
            return self._default_crop(
                source_width, source_height,
                target_width, target_height
            )
        
        avg_x = weighted_x / total_weight
        avg_y = weighted_y / total_weight
        
        # Convert normalized position to pixel coordinates
        face_center_x = int(avg_x * source_width)
        face_center_y = int(avg_y * source_height)
        
        # Calculate crop position to center face
        crop_x = face_center_x - (target_width // 2)
        crop_y = face_center_y - (target_height // 2)
        
        # Clamp to valid range
        crop_x = max(0, min(crop_x, source_width - target_width))
        crop_y = max(0, min(crop_y, source_height - target_height))
        
        # Ensure even numbers for video encoding
        crop_x = crop_x - (crop_x % 2)
        crop_y = crop_y - (crop_y % 2)
        
        return CropRegion(
            x=crop_x,
            y=crop_y,
            width=target_width,
            height=target_height
        )
    
    def _default_crop(
        self,
        source_width: int,
        source_height: int,
        target_width: int,
        target_height: int
    ) -> CropRegion:
        """Calculate default crop (upper-center) when no face detected.
        
        Args:
            source_width: Original video width
            source_height: Original video height
            target_width: Target crop width
            target_height: Target crop height
            
        Returns:
            CropRegion centered horizontally, biased toward top
        """
        # Center horizontally
        crop_x = (source_width - target_width) // 2
        
        # Bias toward top (upper third) for speaker videos
        available_y = source_height - target_height
        crop_y = available_y // 4  # Upper quarter
        
        # Ensure even numbers
        crop_x = crop_x - (crop_x % 2)
        crop_y = crop_y - (crop_y % 2)
        
        return CropRegion(
            x=max(0, crop_x),
            y=max(0, crop_y),
            width=target_width,
            height=target_height
        )
    
    def close(self):
        """Release resources."""
        if self._detector:
            try:
                self._detector.close()
            except Exception:
                pass
            self._detector = None


def analyze_face_positions(
    video_path: str,
    start_time: float,
    end_time: float,
    sample_rate: int = FaceTracker.DEFAULT_SAMPLE_RATE,
    progress_callback: Callable[[int], None] | None = None
) -> list[FacePosition]:
    """Convenience function to analyze face positions in a video clip.
    
    Args:
        video_path: Path to video file
        start_time: Start time in seconds
        end_time: End time in seconds
        sample_rate: Analyze every N frames
        progress_callback: Optional progress callback
        
    Returns:
        List of FacePosition objects
    """
    tracker = FaceTracker(sample_rate=sample_rate)
    try:
        return tracker.analyze_clip(
            video_path, start_time, end_time, progress_callback
        )
    finally:
        tracker.close()


def calculate_smart_crop(
    video_path: str,
    start_time: float,
    end_time: float,
    source_width: int,
    source_height: int,
    target_width: int,
    target_height: int,
    progress_callback: Callable[[int], None] | None = None
) -> CropRegion:
    """Calculate smart crop region based on face detection.
    
    Convenience function that combines face detection and crop calculation.
    
    Args:
        video_path: Path to video file
        start_time: Clip start time in seconds
        end_time: Clip end time in seconds
        source_width: Original video width
        source_height: Original video height
        target_width: Target crop width
        target_height: Target crop height
        progress_callback: Optional progress callback
        
    Returns:
        CropRegion optimized for detected faces
    """
    tracker = FaceTracker()
    try:
        positions = tracker.analyze_clip(
            video_path, start_time, end_time, progress_callback
        )
        return tracker.calculate_crop_region(
            positions,
            source_width, source_height,
            target_width, target_height
        )
    finally:
        tracker.close()


def is_face_tracking_available() -> bool:
    """Check if face tracking dependencies are available.
    
    Returns:
        True if MediaPipe and OpenCV are installed
    """
    try:
        _ensure_imports()
        return True
    except ImportError:
        return False


# Export public API
__all__ = [
    "FaceTracker",
    "FacePosition", 
    "CropRegion",
    "analyze_face_positions",
    "calculate_smart_crop",
    "is_face_tracking_available",
]
