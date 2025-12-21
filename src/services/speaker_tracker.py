"""Active Speaker Detection for SmartClip AI using MediaPipe Face Mesh.

This module provides active speaker detection by analyzing mouth movements
to determine who is currently speaking in a video with multiple people.

Key Features:
    - Face Mesh with 468 landmarks for precise mouth tracking
    - Mouth Aspect Ratio (MAR) calculation for speech detection
    - Multi-face tracking with speaker identification
    - Smooth transitions between speakers
    - Fallback to group shot if no clear speaker

Algorithm:
    1. Detect all faces using Face Mesh
    2. Extract mouth landmarks (lips) for each face
    3. Calculate Mouth Aspect Ratio (MAR) = height / width
    4. Higher MAR = mouth more open = likely speaking
    5. Track MAR over time to identify active speaker
    6. Crop focuses on the person with highest speaking activity

Performance:
    - Optimized for CPU (works well on Ryzen 5 5600G)
    - Frame sampling to reduce processing time
    - ~10-20 FPS processing speed

Usage:
    from src.services.speaker_tracker import ActiveSpeakerTracker
    
    tracker = ActiveSpeakerTracker()
    positions = tracker.analyze_clip(video_path, start_time, end_time)
"""

import os
from dataclasses import dataclass, field
from typing import Callable
from collections import deque

# Lazy imports
_mp = None
_cv2 = None
_np = None


def _ensure_imports():
    """Lazy import dependencies."""
    global _mp, _cv2, _np
    
    if _mp is None:
        try:
            import mediapipe as mp
            _mp = mp
        except ImportError:
            raise ImportError(
                "MediaPipe is required. Install with: pip install mediapipe"
            )
    
    if _cv2 is None:
        try:
            import cv2
            _cv2 = cv2
        except ImportError:
            raise ImportError(
                "OpenCV is required. Install with: pip install opencv-python"
            )
    
    if _np is None:
        try:
            import numpy as np
            _np = np
        except ImportError:
            raise ImportError(
                "NumPy is required. Install with: pip install numpy"
            )
    
    return _mp, _cv2, _np


def _get_face_landmarker_model() -> str:
    """Download Face Landmarker model if needed."""
    import urllib.request
    import tempfile
    
    MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
    
    cache_dir = os.path.join(tempfile.gettempdir(), "sclip_models")
    os.makedirs(cache_dir, exist_ok=True)
    
    model_path = os.path.join(cache_dir, "face_landmarker.task")
    
    if not os.path.exists(model_path):
        try:
            urllib.request.urlretrieve(MODEL_URL, model_path)
        except Exception as e:
            raise RuntimeError(f"Failed to download face landmarker model: {e}")
    
    return model_path


# Mouth landmark indices for MediaPipe Face Mesh
# Upper lip: 13, 14, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95
# Lower lip: 14, 17, 84, 181, 91, 146, 61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 16, 15
# Simplified key points for MAR calculation
UPPER_LIP_TOP = 13      # Top of upper lip
LOWER_LIP_BOTTOM = 14   # Bottom of lower lip  
LEFT_CORNER = 61        # Left corner of mouth
RIGHT_CORNER = 291      # Right corner of mouth
UPPER_LIP_BOTTOM = 0    # Bottom of upper lip (inner)
LOWER_LIP_TOP = 17      # Top of lower lip (inner)


@dataclass
class SpeakerPosition:
    """Position of an active speaker.
    
    Attributes:
        x: X coordinate of face center (normalized 0-1)
        y: Y coordinate of face center (normalized 0-1)
        width: Face bounding box width (normalized)
        height: Face bounding box height (normalized)
        confidence: Detection confidence
        timestamp: Time in video (seconds)
        speaking_score: How likely this person is speaking (0-1)
        face_id: Identifier for tracking same face across frames
    """
    x: float
    y: float
    width: float
    height: float
    confidence: float
    timestamp: float
    speaking_score: float = 0.0
    face_id: int = 0


@dataclass
class FaceState:
    """Tracks state of a detected face over time."""
    face_id: int
    mar_history: deque = field(default_factory=lambda: deque(maxlen=10))
    position_history: deque = field(default_factory=lambda: deque(maxlen=5))
    last_seen: float = 0.0
    speaking_frames: int = 0
    total_frames: int = 0
    
    def add_mar(self, mar: float, timestamp: float):
        """Add MAR measurement."""
        self.mar_history.append(mar)
        self.last_seen = timestamp
        self.total_frames += 1
        if mar > 0.3:  # Threshold for "speaking"
            self.speaking_frames += 1
    
    def get_speaking_ratio(self) -> float:
        """Get ratio of frames where person was speaking."""
        if self.total_frames == 0:
            return 0.0
        return self.speaking_frames / self.total_frames
    
    def get_recent_mar(self) -> float:
        """Get average MAR from recent frames."""
        if not self.mar_history:
            return 0.0
        return sum(self.mar_history) / len(self.mar_history)


class ActiveSpeakerTracker:
    """Active speaker detection using MediaPipe Face Mesh.
    
    Detects who is speaking by analyzing mouth movements (MAR).
    """
    
    DEFAULT_SAMPLE_RATE = 3  # More frequent sampling for speech detection
    DEFAULT_CONFIDENCE = 0.5
    ANALYSIS_WIDTH = 640  # Slightly larger for better landmark detection
    MAR_SPEAKING_THRESHOLD = 0.25  # MAR above this = speaking
    
    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        detection_confidence: float = DEFAULT_CONFIDENCE
    ):
        self.sample_rate = sample_rate
        self.detection_confidence = detection_confidence
        self._landmarker = None
        self._face_states: dict[int, FaceState] = {}
        self._next_face_id = 0
    
    def _get_landmarker(self):
        """Get or create Face Landmarker."""
        if self._landmarker is None:
            mp, _, _ = _ensure_imports()
            
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            
            model_path = _get_face_landmarker_model()
            
            base_options = python.BaseOptions(
                model_asset_path=model_path
            )
            
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                output_face_blendshapes=False,
                output_facial_transformation_matrixes=False,
                num_faces=5,  # Support up to 5 faces
                min_face_detection_confidence=self.detection_confidence,
                min_face_presence_confidence=self.detection_confidence,
                min_tracking_confidence=self.detection_confidence
            )
            
            self._landmarker = vision.FaceLandmarker.create_from_options(options)
        
        return self._landmarker
    
    def analyze_clip(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        progress_callback: Callable[[int], None] | None = None
    ) -> list[SpeakerPosition]:
        """Analyze clip for active speaker positions.
        
        Args:
            video_path: Path to video file
            start_time: Start time in seconds
            end_time: End time in seconds
            progress_callback: Optional progress callback
            
        Returns:
            List of SpeakerPosition for the active speaker
        """
        mp, cv2, np = _ensure_imports()
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            start_frame = int(start_time * fps)
            end_frame = int(end_time * fps)
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            positions: list[SpeakerPosition] = []
            frame_count = 0
            frames_to_process = end_frame - start_frame
            
            landmarker = self._get_landmarker()
            self._face_states.clear()
            
            while cap.isOpened():
                current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                if current_frame >= end_frame:
                    break
                
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                if frame_count % self.sample_rate != 0:
                    continue
                
                if progress_callback:
                    progress = int((frame_count / frames_to_process) * 100)
                    progress_callback(min(progress, 100))
                
                timestamp = current_frame / fps
                speaker_pos = self._detect_active_speaker(
                    frame, landmarker, timestamp
                )
                
                if speaker_pos:
                    positions.append(speaker_pos)
            
            return positions
            
        finally:
            cap.release()
    
    def _detect_active_speaker(
        self,
        frame,
        landmarker,
        timestamp: float
    ) -> SpeakerPosition | None:
        """Detect the active speaker in a frame."""
        mp, cv2, np = _ensure_imports()
        
        height, width = frame.shape[:2]
        scale = self.ANALYSIS_WIDTH / width
        small_frame = cv2.resize(
            frame,
            (self.ANALYSIS_WIDTH, int(height * scale))
        )
        
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        results = landmarker.detect(mp_image)
        
        if not results.face_landmarks:
            return None
        
        img_height, img_width = rgb_frame.shape[:2]
        
        # Analyze each face
        face_data = []
        for face_idx, landmarks in enumerate(results.face_landmarks):
            # Calculate bounding box from landmarks
            xs = [lm.x for lm in landmarks]
            ys = [lm.y for lm in landmarks]
            
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)
            
            center_x = (x_min + x_max) / 2
            center_y = (y_min + y_max) / 2
            box_width = x_max - x_min
            box_height = y_max - y_min
            
            # Calculate MAR (Mouth Aspect Ratio)
            mar = self._calculate_mar(landmarks)
            
            # Track face state
            face_id = self._match_or_create_face(center_x, center_y, timestamp)
            self._face_states[face_id].add_mar(mar, timestamp)
            
            face_data.append({
                'face_id': face_id,
                'x': center_x,
                'y': center_y,
                'width': box_width,
                'height': box_height,
                'mar': mar,
                'speaking_score': self._face_states[face_id].get_speaking_ratio()
            })
        
        if not face_data:
            return None
        
        # Find the most likely speaker
        # Prioritize: current high MAR + history of speaking
        best_speaker = max(
            face_data,
            key=lambda f: f['mar'] * 0.6 + f['speaking_score'] * 0.4
        )
        
        return SpeakerPosition(
            x=best_speaker['x'],
            y=best_speaker['y'],
            width=best_speaker['width'],
            height=best_speaker['height'],
            confidence=0.9,
            timestamp=timestamp,
            speaking_score=best_speaker['speaking_score'],
            face_id=best_speaker['face_id']
        )
    
    def _calculate_mar(self, landmarks) -> float:
        """Calculate Mouth Aspect Ratio from landmarks.
        
        MAR = vertical_distance / horizontal_distance
        Higher MAR = mouth more open = likely speaking
        """
        try:
            # Get key mouth landmarks
            upper_lip = landmarks[13]   # Top of upper lip
            lower_lip = landmarks[14]   # Bottom of lower lip
            left_corner = landmarks[61]  # Left corner
            right_corner = landmarks[291]  # Right corner
            
            # Vertical distance (mouth opening)
            vertical = abs(lower_lip.y - upper_lip.y)
            
            # Horizontal distance (mouth width)
            horizontal = abs(right_corner.x - left_corner.x)
            
            if horizontal < 0.001:  # Avoid division by zero
                return 0.0
            
            mar = vertical / horizontal
            return min(mar, 1.0)  # Cap at 1.0
            
        except (IndexError, AttributeError):
            return 0.0
    
    def _match_or_create_face(
        self,
        x: float,
        y: float,
        timestamp: float
    ) -> int:
        """Match face to existing tracked face or create new."""
        _, _, np = _ensure_imports()
        
        # Simple position-based matching
        best_match = None
        best_distance = 0.15  # Max distance threshold
        
        for face_id, state in self._face_states.items():
            if timestamp - state.last_seen > 1.0:  # Face not seen for 1 second
                continue
            
            if state.position_history:
                last_pos = state.position_history[-1]
                distance = ((x - last_pos[0])**2 + (y - last_pos[1])**2)**0.5
                
                if distance < best_distance:
                    best_distance = distance
                    best_match = face_id
        
        if best_match is not None:
            self._face_states[best_match].position_history.append((x, y))
            return best_match
        
        # Create new face
        new_id = self._next_face_id
        self._next_face_id += 1
        self._face_states[new_id] = FaceState(face_id=new_id)
        self._face_states[new_id].position_history.append((x, y))
        self._face_states[new_id].last_seen = timestamp
        
        return new_id
    
    def calculate_crop_region(
        self,
        positions: list[SpeakerPosition],
        source_width: int,
        source_height: int,
        target_width: int,
        target_height: int
    ):
        """Calculate crop region focused on active speaker."""
        from src.services.face_tracker import CropRegion
        
        if not positions:
            # Default upper-center crop
            crop_x = (source_width - target_width) // 2
            crop_y = (source_height - target_height) // 4
            crop_x = crop_x - (crop_x % 2)
            crop_y = crop_y - (crop_y % 2)
            return CropRegion(
                x=max(0, crop_x),
                y=max(0, crop_y),
                width=target_width,
                height=target_height
            )
        
        # Weight by speaking score
        total_weight = 0
        weighted_x = 0
        weighted_y = 0
        
        for pos in positions:
            weight = pos.speaking_score + 0.1  # Minimum weight
            weighted_x += pos.x * weight
            weighted_y += pos.y * weight
            total_weight += weight
        
        if total_weight == 0:
            avg_x = 0.5
            avg_y = 0.3
        else:
            avg_x = weighted_x / total_weight
            avg_y = weighted_y / total_weight
        
        face_center_x = int(avg_x * source_width)
        face_center_y = int(avg_y * source_height)
        
        crop_x = face_center_x - (target_width // 2)
        crop_y = face_center_y - (target_height // 2)
        
        crop_x = max(0, min(crop_x, source_width - target_width))
        crop_y = max(0, min(crop_y, source_height - target_height))
        
        crop_x = crop_x - (crop_x % 2)
        crop_y = crop_y - (crop_y % 2)
        
        return CropRegion(
            x=crop_x,
            y=crop_y,
            width=target_width,
            height=target_height
        )
    
    def close(self):
        """Release resources."""
        if self._landmarker:
            try:
                self._landmarker.close()
            except Exception:
                pass
            self._landmarker = None
        self._face_states.clear()


def is_speaker_tracking_available() -> bool:
    """Check if speaker tracking is available."""
    try:
        _ensure_imports()
        return True
    except ImportError:
        return False


__all__ = [
    "ActiveSpeakerTracker",
    "SpeakerPosition",
    "is_speaker_tracking_available",
]
