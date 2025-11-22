"""
Trinity Phase 2 - Integrated Detection & Tracking System
Combines detection, tracking, and 3D position estimation
"""

import time
import numpy as np
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

from trinity.core.camera_manager import SynchronizedFrames, CameraFrame
from trinity.detection.detector import ObjectDetector, Detection, DetectionResult
from trinity.detection.tracker import MultiObjectTracker, MultiCameraTracker, Track
from trinity.detection.position_3d import PositionEstimator3D
from trinity.detection.visualization import DetectionVisualizer


@dataclass
class DetectionSystemResult:
    """Results from detection system"""
    frame_number: int
    timestamp: datetime
    detections_per_camera: List[List[Detection]]
    tracks_per_camera: List[List[Track]]
    global_tracks: List[Track]  # Tracks with 3D positions
    processing_time_ms: float
    detector_time_ms: float
    tracker_time_ms: float
    position_estimation_time_ms: float


class DetectionTrackingSystem:
    """
    Integrated detection and tracking system
    Combines YOLOv8 detection, DeepSORT tracking, and 3D position estimation
    """

    def __init__(
        self,
        config: Dict,
        num_cameras: int = 3,
        enable_detection: bool = True,
        enable_tracking: bool = True,
        enable_3d_estimation: bool = False  # Requires calibration
    ):
        """
        Initialize detection & tracking system

        Args:
            config: Configuration dictionary
            num_cameras: Number of cameras
            enable_detection: Enable object detection
            enable_tracking: Enable object tracking
            enable_3d_estimation: Enable 3D position estimation
        """
        self.config = config
        self.num_cameras = num_cameras
        self.enable_detection = enable_detection
        self.enable_tracking = enable_tracking
        self.enable_3d_estimation = enable_3d_estimation

        # Initialize detector
        self.detector: Optional[ObjectDetector] = None
        if self.enable_detection:
            try:
                from trinity.detection.detector import create_detector_from_config
                self.detector = create_detector_from_config(config)
                logger.success("Object detector initialized")
            except Exception as e:
                logger.error(f"Failed to initialize detector: {e}")
                self.enable_detection = False

        # Initialize tracker
        self.tracker: Optional[MultiCameraTracker] = None
        if self.enable_tracking:
            try:
                tracking_config = config.get('tracking', {}).get('deepsort', {})
                self.tracker = MultiCameraTracker(
                    num_cameras=num_cameras,
                    association_threshold=0.5
                )
                logger.success("Multi-object tracker initialized")
            except Exception as e:
                logger.error(f"Failed to initialize tracker: {e}")
                self.enable_tracking = False

        # Initialize 3D position estimator
        self.position_estimator: Optional[PositionEstimator3D] = None
        if self.enable_3d_estimation:
            try:
                # This would require camera calibration data
                # For now, we'll initialize it when calibration is available
                logger.info("3D position estimation enabled (requires calibration)")
            except Exception as e:
                logger.error(f"Failed to initialize 3D estimator: {e}")
                self.enable_3d_estimation = False

        # Visualizer
        self.visualizer = DetectionVisualizer(
            show_labels=True,
            show_confidence=True,
            show_track_ids=True,
            show_trajectories=True,
            trajectory_length=50
        )

        # Frame counter
        self.frame_count = 0

        # Callbacks
        self.detection_callbacks: List[Callable] = []
        self.tracking_callbacks: List[Callable] = []

        logger.success("Detection & tracking system initialized")

    def process_frames(
        self,
        synchronized_frames: SynchronizedFrames
    ) -> DetectionSystemResult:
        """
        Process synchronized frames from all cameras

        Args:
            synchronized_frames: Synchronized frames from all cameras

        Returns:
            DetectionSystemResult with all processed data
        """
        start_time = time.time()
        self.frame_count += 1

        # Extract frames
        frames = [cf.frame for cf in synchronized_frames.frames]
        timestamp = synchronized_frames.timestamp

        # Detection phase
        detector_start = time.time()
        detections_per_camera = []

        if self.enable_detection and self.detector:
            # Batch detection for efficiency
            detection_results = self.detector.detect_batch(frames)
            detections_per_camera = [result.detections for result in detection_results]

            # Trigger callbacks
            for callback in self.detection_callbacks:
                callback(detections_per_camera)
        else:
            detections_per_camera = [[] for _ in frames]

        detector_time = (time.time() - detector_start) * 1000

        # Tracking phase
        tracker_start = time.time()
        tracks_per_camera = {}

        if self.enable_tracking and self.tracker:
            tracks_per_camera = self.tracker.update(
                detections_per_camera,
                timestamp
            )

            # Trigger callbacks
            for callback in self.tracking_callbacks:
                callback(tracks_per_camera)
        else:
            tracks_per_camera = {i: [] for i in range(len(frames))}

        tracker_time = (time.time() - tracker_start) * 1000

        # 3D position estimation phase
        position_start = time.time()
        global_tracks = []

        if self.enable_3d_estimation and self.position_estimator:
            # Estimate 3D positions for tracks
            # This would match tracks across cameras and triangulate
            pass
        else:
            # For now, just use tracks from first camera as "global"
            if 0 in tracks_per_camera:
                global_tracks = tracks_per_camera[0]

        position_time = (time.time() - position_start) * 1000

        total_time = (time.time() - start_time) * 1000

        return DetectionSystemResult(
            frame_number=self.frame_count,
            timestamp=timestamp,
            detections_per_camera=detections_per_camera,
            tracks_per_camera=list(tracks_per_camera.values()),
            global_tracks=global_tracks,
            processing_time_ms=total_time,
            detector_time_ms=detector_time,
            tracker_time_ms=tracker_time,
            position_estimation_time_ms=position_time
        )

    def visualize_results(
        self,
        frames: List[np.ndarray],
        result: DetectionSystemResult,
        show_detections: bool = False,
        show_tracks: bool = True
    ) -> List[np.ndarray]:
        """
        Visualize detection and tracking results on frames

        Args:
            frames: List of camera frames
            result: Detection system result
            show_detections: Show raw detections
            show_tracks: Show tracks with IDs

        Returns:
            List of visualized frames
        """
        visualized = []

        for i, frame in enumerate(frames):
            vis_frame = frame.copy()

            # Draw detections
            if show_detections and i < len(result.detections_per_camera):
                vis_frame = self.visualizer.draw_detections(
                    vis_frame,
                    result.detections_per_camera[i]
                )

            # Draw tracks
            if show_tracks and i < len(result.tracks_per_camera):
                vis_frame = self.visualizer.draw_tracks(
                    vis_frame,
                    result.tracks_per_camera[i]
                )

            # Draw info overlay
            if i == 0:  # Only on first camera
                info = self.get_system_info()
                vis_frame = self.visualizer.draw_info_overlay(vis_frame, info)

            visualized.append(vis_frame)

        return visualized

    def get_bird_eye_view(
        self,
        result: DetectionSystemResult
    ) -> np.ndarray:
        """
        Generate bird's eye view visualization

        Args:
            result: Detection system result

        Returns:
            Bird's eye view image
        """
        return self.visualizer.create_bird_eye_view(
            result.global_tracks,
            world_size=(50.0, 50.0),
            image_size=(500, 500),
            show_ids=True
        )

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information for display"""
        info = {
            'Frame': self.frame_count,
            'Detection': 'ON' if self.enable_detection else 'OFF',
            'Tracking': 'ON' if self.enable_tracking else 'OFF',
            '3D Est.': 'ON' if self.enable_3d_estimation else 'OFF',
        }

        if self.detector:
            stats = self.detector.get_statistics()
            info['Avg Inference'] = f"{stats['avg_inference_time_ms']:.1f}ms"

        if self.tracker:
            stats = self.tracker.get_statistics()
            total_tracks = sum(
                cam_stats['active_tracks']
                for cam_stats in stats['per_camera_stats'].values()
            )
            info['Active Tracks'] = total_tracks

        return info

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        stats = {
            'frame_count': self.frame_count,
            'detection_enabled': self.enable_detection,
            'tracking_enabled': self.enable_tracking,
            '3d_estimation_enabled': self.enable_3d_estimation,
        }

        if self.detector:
            stats['detector'] = self.detector.get_statistics()

        if self.tracker:
            stats['tracker'] = self.tracker.get_statistics()

        return stats

    def register_detection_callback(self, callback: Callable):
        """Register callback for new detections"""
        self.detection_callbacks.append(callback)

    def register_tracking_callback(self, callback: Callable):
        """Register callback for track updates"""
        self.tracking_callbacks.append(callback)

    def reset(self):
        """Reset system state"""
        if self.detector:
            self.detector.reset_statistics()

        if self.tracker:
            self.tracker.reset()

        self.frame_count = 0

        logger.info("Detection & tracking system reset")

    def enable_feature(self, feature: str, enabled: bool):
        """
        Enable or disable features dynamically

        Args:
            feature: 'detection', 'tracking', or '3d_estimation'
            enabled: True to enable, False to disable
        """
        if feature == 'detection':
            self.enable_detection = enabled and self.detector is not None
        elif feature == 'tracking':
            self.enable_tracking = enabled and self.tracker is not None
        elif feature == '3d_estimation':
            self.enable_3d_estimation = enabled and self.position_estimator is not None
        else:
            logger.warning(f"Unknown feature: {feature}")

        logger.info(f"Feature '{feature}' {'enabled' if enabled else 'disabled'}")
