"""
Trinity Phase 2 - Multi-Object Tracker
DeepSORT-based tracking with re-identification
"""

import numpy as np
from typing import List, Optional, Dict, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
from loguru import logger

from trinity.detection.detector import Detection


@dataclass
class Track:
    """Single object track"""
    track_id: int
    class_name: str
    class_id: int

    # Current state
    bbox: Tuple[float, float, float, float]  # x, y, w, h
    confidence: float
    age: int = 0
    hits: int = 0
    time_since_update: int = 0

    # Trajectory (limited history)
    trajectory: deque = field(default_factory=lambda: deque(maxlen=100))

    # Velocity
    velocity: Tuple[float, float] = (0.0, 0.0)
    speed: float = 0.0

    # State flags
    is_confirmed: bool = False
    is_tentative: bool = True

    # Feature vector for re-identification
    feature: Optional[np.ndarray] = None

    # Timestamps
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    def update(
        self,
        detection: Detection,
        frame_timestamp: Optional[datetime] = None
    ):
        """Update track with new detection"""
        # Update bounding box
        old_center = self.get_center()
        self.bbox = detection.bbox
        new_center = self.get_center()

        # Update velocity
        if len(self.trajectory) > 0:
            dx = new_center[0] - old_center[0]
            dy = new_center[1] - old_center[1]
            self.velocity = (dx, dy)
            self.speed = np.sqrt(dx**2 + dy**2)

        # Update confidence
        self.confidence = detection.confidence

        # Update counters
        self.hits += 1
        self.time_since_update = 0

        # Add to trajectory
        if frame_timestamp is None:
            frame_timestamp = datetime.now()

        self.trajectory.append({
            'bbox': self.bbox,
            'center': new_center,
            'timestamp': frame_timestamp,
            'velocity': self.velocity,
            'speed': self.speed
        })

        # Update last seen
        self.last_seen = frame_timestamp

        # Check if confirmed
        if not self.is_confirmed and self.hits >= 3:
            self.is_confirmed = True
            self.is_tentative = False

    def predict(self):
        """Predict next position based on velocity"""
        x, y, w, h = self.bbox
        vx, vy = self.velocity

        # Simple linear prediction
        predicted_x = x + vx
        predicted_y = y + vy

        self.bbox = (predicted_x, predicted_y, w, h)
        self.time_since_update += 1

    def get_center(self) -> Tuple[float, float]:
        """Get bounding box center"""
        x, y, w, h = self.bbox
        return (x + w/2, y + h/2)

    def get_trajectory_points(self, max_points: int = 50) -> List[Tuple[float, float]]:
        """Get trajectory as list of center points"""
        return [
            t['center'] for t in list(self.trajectory)[-max_points:]
        ]

    def get_predicted_position(self, steps_ahead: int = 1) -> Tuple[float, float]:
        """Predict future position"""
        cx, cy = self.get_center()
        vx, vy = self.velocity

        pred_x = cx + vx * steps_ahead
        pred_y = cy + vy * steps_ahead

        return (pred_x, pred_y)


class MultiObjectTracker:
    """
    Multi-object tracker using DeepSORT-like algorithm
    """

    def __init__(
        self,
        max_age: int = 30,
        min_hits: int = 3,
        iou_threshold: float = 0.3,
        max_iou_distance: float = 0.7
    ):
        """
        Initialize tracker

        Args:
            max_age: Maximum frames to keep track alive without detection
            min_hits: Minimum detections before track is confirmed
            iou_threshold: Minimum IoU for matching
            max_iou_distance: Maximum IoU distance for matching
        """
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.max_iou_distance = max_iou_distance

        self.tracks: List[Track] = []
        self.next_track_id = 1
        self.frame_count = 0

        # Statistics
        self.total_tracks_created = 0
        self.total_tracks_deleted = 0

        logger.info("Multi-object tracker initialized")

    def update(
        self,
        detections: List[Detection],
        frame_timestamp: Optional[datetime] = None
    ) -> List[Track]:
        """
        Update tracks with new detections

        Args:
            detections: List of detections from current frame
            frame_timestamp: Timestamp of current frame

        Returns:
            List of active tracks
        """
        self.frame_count += 1

        if frame_timestamp is None:
            frame_timestamp = datetime.now()

        # Predict new locations for existing tracks
        for track in self.tracks:
            track.predict()
            track.age += 1

        # Match detections to existing tracks
        matched_tracks, matched_detections, unmatched_tracks, unmatched_detections = \
            self._match_detections_to_tracks(detections)

        # Update matched tracks
        for track_idx, det_idx in zip(matched_tracks, matched_detections):
            self.tracks[track_idx].update(detections[det_idx], frame_timestamp)

        # Create new tracks for unmatched detections
        for det_idx in unmatched_detections:
            self._create_new_track(detections[det_idx], frame_timestamp)

        # Remove old tracks
        self._remove_old_tracks()

        # Return only confirmed tracks
        return [t for t in self.tracks if t.is_confirmed]

    def _match_detections_to_tracks(
        self,
        detections: List[Detection]
    ) -> Tuple[List[int], List[int], List[int], List[int]]:
        """
        Match detections to existing tracks using IoU

        Returns:
            (matched_track_indices, matched_detection_indices,
             unmatched_track_indices, unmatched_detection_indices)
        """
        if len(self.tracks) == 0:
            return [], [], [], list(range(len(detections)))

        if len(detections) == 0:
            return [], [], list(range(len(self.tracks))), []

        # Compute IoU matrix
        iou_matrix = np.zeros((len(self.tracks), len(detections)))

        for t_idx, track in enumerate(self.tracks):
            for d_idx, detection in enumerate(detections):
                # Only match same class
                if track.class_id == detection.class_id:
                    iou = self._compute_iou(track.bbox, detection.bbox)
                    iou_matrix[t_idx, d_idx] = iou

        # Use greedy matching (can be improved with Hungarian algorithm)
        matched_tracks = []
        matched_detections = []

        for _ in range(min(len(self.tracks), len(detections))):
            # Find best match
            max_iou = iou_matrix.max()

            if max_iou < self.iou_threshold:
                break

            t_idx, d_idx = np.unravel_index(iou_matrix.argmax(), iou_matrix.shape)

            matched_tracks.append(t_idx)
            matched_detections.append(d_idx)

            # Mark as matched
            iou_matrix[t_idx, :] = 0
            iou_matrix[:, d_idx] = 0

        # Find unmatched
        unmatched_tracks = [
            i for i in range(len(self.tracks))
            if i not in matched_tracks
        ]

        unmatched_detections = [
            i for i in range(len(detections))
            if i not in matched_detections
        ]

        return matched_tracks, matched_detections, unmatched_tracks, unmatched_detections

    def _compute_iou(
        self,
        bbox1: Tuple[float, float, float, float],
        bbox2: Tuple[float, float, float, float]
    ) -> float:
        """Compute Intersection over Union between two boxes"""
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2

        # Compute intersection
        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(x1 + w1, x2 + w2)
        yi2 = min(y1 + h1, y2 + h2)

        inter_width = max(0, xi2 - xi1)
        inter_height = max(0, yi2 - yi1)
        inter_area = inter_width * inter_height

        # Compute union
        box1_area = w1 * h1
        box2_area = w2 * h2
        union_area = box1_area + box2_area - inter_area

        # Compute IoU
        if union_area > 0:
            return inter_area / union_area
        return 0.0

    def _create_new_track(
        self,
        detection: Detection,
        frame_timestamp: datetime
    ):
        """Create a new track from detection"""
        track = Track(
            track_id=self.next_track_id,
            class_name=detection.class_name,
            class_id=detection.class_id,
            bbox=detection.bbox,
            confidence=detection.confidence,
            first_seen=frame_timestamp,
            last_seen=frame_timestamp,
            hits=1
        )

        # Add initial trajectory point
        track.trajectory.append({
            'bbox': track.bbox,
            'center': track.get_center(),
            'timestamp': frame_timestamp,
            'velocity': (0.0, 0.0),
            'speed': 0.0
        })

        self.tracks.append(track)
        self.next_track_id += 1
        self.total_tracks_created += 1

    def _remove_old_tracks(self):
        """Remove tracks that haven't been updated recently"""
        tracks_to_keep = []

        for track in self.tracks:
            # Remove if too old or if tentative and not updated
            if track.time_since_update >= self.max_age:
                self.total_tracks_deleted += 1
                continue

            if track.is_tentative and track.time_since_update > 5:
                self.total_tracks_deleted += 1
                continue

            tracks_to_keep.append(track)

        self.tracks = tracks_to_keep

    def get_track_by_id(self, track_id: int) -> Optional[Track]:
        """Get track by ID"""
        for track in self.tracks:
            if track.track_id == track_id:
                return track
        return None

    def get_active_tracks(self) -> List[Track]:
        """Get all active confirmed tracks"""
        return [t for t in self.tracks if t.is_confirmed]

    def get_tracks_by_class(self, class_name: str) -> List[Track]:
        """Get all tracks of specific class"""
        return [
            t for t in self.tracks
            if t.is_confirmed and t.class_name == class_name
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get tracker statistics"""
        active_tracks = self.get_active_tracks()

        return {
            'frame_count': self.frame_count,
            'active_tracks': len(active_tracks),
            'total_tracks': len(self.tracks),
            'confirmed_tracks': len([t for t in self.tracks if t.is_confirmed]),
            'tentative_tracks': len([t for t in self.tracks if t.is_tentative]),
            'total_created': self.total_tracks_created,
            'total_deleted': self.total_tracks_deleted,
            'tracks_by_class': self._get_tracks_by_class_count(active_tracks),
            'avg_track_age': np.mean([t.age for t in active_tracks]) if active_tracks else 0
        }

    def _get_tracks_by_class_count(self, tracks: List[Track]) -> Dict[str, int]:
        """Count tracks by class"""
        counts = {}
        for track in tracks:
            counts[track.class_name] = counts.get(track.class_name, 0) + 1
        return counts

    def reset(self):
        """Reset tracker"""
        self.tracks = []
        self.next_track_id = 1
        self.frame_count = 0
        self.total_tracks_created = 0
        self.total_tracks_deleted = 0


class MultiCameraTracker:
    """
    Tracker that associates objects across multiple cameras
    """

    def __init__(
        self,
        num_cameras: int,
        association_threshold: float = 0.5
    ):
        """
        Initialize multi-camera tracker

        Args:
            num_cameras: Number of cameras
            association_threshold: Threshold for cross-camera association
        """
        self.num_cameras = num_cameras
        self.association_threshold = association_threshold

        # One tracker per camera
        self.trackers = [MultiObjectTracker() for _ in range(num_cameras)]

        # Global track mapping: {global_id: {camera_id: local_track_id}}
        self.global_tracks: Dict[int, Dict[int, int]] = {}
        self.next_global_id = 1

        logger.info(f"Multi-camera tracker initialized with {num_cameras} cameras")

    def update(
        self,
        detections_per_camera: List[List[Detection]],
        frame_timestamp: Optional[datetime] = None
    ) -> Dict[int, List[Track]]:
        """
        Update all camera trackers

        Args:
            detections_per_camera: List of detection lists (one per camera)
            frame_timestamp: Frame timestamp

        Returns:
            Dictionary mapping camera_id to list of tracks
        """
        # Update each camera's tracker
        tracks_per_camera = {}

        for camera_id, detections in enumerate(detections_per_camera):
            tracks = self.trackers[camera_id].update(detections, frame_timestamp)
            tracks_per_camera[camera_id] = tracks

        # Associate tracks across cameras
        self._associate_tracks_across_cameras(tracks_per_camera)

        return tracks_per_camera

    def _associate_tracks_across_cameras(
        self,
        tracks_per_camera: Dict[int, List[Track]]
    ):
        """
        Associate tracks across cameras using spatial proximity and class matching

        This is a simplified version. A full implementation would use:
        - Camera calibration for 3D position
        - Appearance features for re-identification
        - Temporal consistency
        """
        # Placeholder for multi-camera association
        # In Phase 2.3, this will use the coordinate transformation utilities
        # to project tracks to 3D world coordinates for matching
        pass

    def get_global_track_id(self, camera_id: int, local_track_id: int) -> Optional[int]:
        """Get global track ID for a local track"""
        for global_id, camera_tracks in self.global_tracks.items():
            if camera_id in camera_tracks and camera_tracks[camera_id] == local_track_id:
                return global_id
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get multi-camera tracking statistics"""
        stats = {
            'num_cameras': self.num_cameras,
            'per_camera_stats': {}
        }

        for cam_id, tracker in enumerate(self.trackers):
            stats['per_camera_stats'][f'camera_{cam_id}'] = tracker.get_statistics()

        return stats
