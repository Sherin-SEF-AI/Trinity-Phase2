"""
Trinity Phase 3 - Integrated AV Monitoring System
Complete system integrating AV identification, trajectory analysis, safety metrics, and event detection
"""

import time
from typing import List, Optional, Dict, Callable
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

from trinity.core.camera_manager import SynchronizedFrames
from trinity.detection.tracker import Track
from trinity.av_monitoring.av_identification import (
    AVIdentificationSystem, ArUcoDetector, AVVehicle
)
from trinity.av_monitoring.trajectory_analysis import (
    TrajectoryAnalyzer, TrajectoryMetrics, PredictedTrajectory
)
from trinity.av_monitoring.safety_metrics import (
    SafetyMetricsCalculator, SafetyMetrics, TTCResult, SafetyEvent
)
from trinity.av_monitoring.event_detection import (
    EventDetectionSystem, DetectedEvent
)


@dataclass
class AVMonitoringResult:
    """Complete AV monitoring result for a frame"""
    frame_number: int
    timestamp: datetime
    processing_time_ms: float

    # AV identification
    av_tracks: Dict[str, Track]  # av_id -> Track
    detected_markers: List  # AVMarker objects

    # Trajectory analysis
    trajectory_metrics: Dict[int, TrajectoryMetrics]  # track_id -> metrics
    predicted_trajectories: Dict[int, PredictedTrajectory]  # track_id -> prediction

    # Safety metrics
    safety_metrics: Dict[int, SafetyMetrics]  # track_id -> metrics
    ttc_results: List[TTCResult]
    safety_events: List[SafetyEvent]

    # Event detection
    detected_events: List[DetectedEvent]


class AVMonitoringSystem:
    """
    Integrated AV monitoring system
    Combines identification, trajectory analysis, safety metrics, and event detection
    """

    def __init__(
        self,
        config: Dict,
        enable_marker_detection: bool = True,
        enable_trajectory_analysis: bool = True,
        enable_safety_metrics: bool = True,
        enable_event_detection: bool = True
    ):
        """
        Initialize AV monitoring system

        Args:
            config: Configuration dictionary
            enable_marker_detection: Enable ArUco marker detection
            enable_trajectory_analysis: Enable trajectory analysis
            enable_safety_metrics: Enable safety metrics calculation
            enable_event_detection: Enable automatic event detection
        """
        self.config = config
        self.enable_marker_detection = enable_marker_detection
        self.enable_trajectory_analysis = enable_trajectory_analysis
        self.enable_safety_metrics = enable_safety_metrics
        self.enable_event_detection = enable_event_detection

        # Initialize components
        self.av_identification = AVIdentificationSystem()
        self.trajectory_analyzer = TrajectoryAnalyzer()
        self.safety_calculator = SafetyMetricsCalculator()
        self.event_detector = EventDetectionSystem(
            self.safety_calculator,
            self.trajectory_analyzer
        )

        # Frame counter
        self.frame_count = 0
        self.session_start_time = time.time()

        # Callbacks
        self.av_detected_callbacks: List[Callable] = []
        self.event_callbacks: List[Callable] = []

        logger.success("AV monitoring system initialized")

    def register_av_vehicles(self, av_configs: List[Dict]):
        """
        Register AV vehicles in the system

        Args:
            av_configs: List of AV configuration dictionaries
                Format: {
                    'av_id': str,
                    'marker_ids': List[int],
                    'vehicle_type': str,
                    'notes': str
                }
        """
        for config in av_configs:
            self.av_identification.register_av(
                av_id=config['av_id'],
                marker_ids=config['marker_ids'],
                vehicle_type=config.get('vehicle_type', 'car'),
                notes=config.get('notes', '')
            )

        logger.info(f"Registered {len(av_configs)} AV vehicles")

    def process_frame(
        self,
        images: List,  # List of camera images
        tracks: List[Track],
        timestamp: Optional[float] = None
    ) -> AVMonitoringResult:
        """
        Process frame with complete AV monitoring pipeline

        Args:
            images: List of camera images for marker detection
            tracks: List of detected tracks
            timestamp: Frame timestamp (uses current time if None)

        Returns:
            AVMonitoringResult with all analysis
        """
        start_time = time.time()
        self.frame_count += 1

        if timestamp is None:
            timestamp = time.time() - self.session_start_time

        # Initialize result
        result = AVMonitoringResult(
            frame_number=self.frame_count,
            timestamp=datetime.now(),
            processing_time_ms=0.0,
            av_tracks={},
            detected_markers=[],
            trajectory_metrics={},
            predicted_trajectories={},
            safety_metrics={},
            ttc_results=[],
            safety_events=[],
            detected_events=[]
        )

        # 1. AV Identification
        if self.enable_marker_detection:
            # Detect markers in all cameras
            markers_per_camera = self.av_identification.detect_markers(images)
            result.detected_markers = [m for camera_markers in markers_per_camera for m in camera_markers]

            # Assign tracks to AVs
            result.av_tracks = self.av_identification.update_av_tracks(
                tracks,
                markers_per_camera
            )

            # Trigger callbacks for newly identified AVs
            for av_id, track in result.av_tracks.items():
                for callback in self.av_detected_callbacks:
                    callback(av_id, track)

        # Get AV track list
        av_track_list = list(result.av_tracks.values())

        # 2. Trajectory Analysis
        if self.enable_trajectory_analysis:
            for track in tracks:
                # Update trajectory
                self.trajectory_analyzer.update_trajectory(track, timestamp)

                # Calculate metrics
                metrics = self.trajectory_analyzer.calculate_metrics(track.track_id)
                if metrics:
                    result.trajectory_metrics[track.track_id] = metrics

                # Predict trajectory (for AV tracks)
                if self.av_identification.is_av_track(track.track_id):
                    prediction = self.trajectory_analyzer.predict_trajectory(
                        track.track_id,
                        method='linear'
                    )
                    if prediction:
                        result.predicted_trajectories[track.track_id] = prediction

        # 3. Safety Metrics
        if self.enable_safety_metrics:
            # Calculate TTC for all pairs
            result.ttc_results = self.safety_calculator.calculate_all_ttc(tracks)

            # Detect near-misses
            result.safety_events = self.safety_calculator.detect_near_miss(tracks)

            # Calculate per-track safety metrics (for AV tracks)
            for track in av_track_list:
                metrics = self.safety_calculator.calculate_track_safety_metrics(
                    track,
                    tracks
                )
                result.safety_metrics[track.track_id] = metrics

        # 4. Event Detection
        if self.enable_event_detection:
            result.detected_events = self.event_detector.process_frame(
                all_tracks=tracks,
                av_tracks=av_track_list,
                frame_number=self.frame_count
            )

            # Trigger event callbacks
            for event in result.detected_events:
                for callback in self.event_callbacks:
                    callback(event)

        # Calculate processing time
        result.processing_time_ms = (time.time() - start_time) * 1000

        return result

    def get_av_status(self) -> Dict:
        """Get status of all registered AVs"""
        stats = self.av_identification.get_statistics()

        # Add trajectory info
        for av_id, av_details in stats['av_details'].items():
            track_id = av_details.get('track_id')
            if track_id:
                trajectory = self.trajectory_analyzer.get_trajectory(track_id)
                av_details['trajectory_points'] = len(trajectory)

                metrics = self.trajectory_analyzer.calculate_metrics(track_id)
                if metrics:
                    av_details['trajectory_metrics'] = {
                        'total_distance': metrics.total_distance,
                        'avg_speed': metrics.average_speed,
                        'max_speed': metrics.max_speed
                    }

        return stats

    def get_safety_summary(self) -> Dict:
        """Get safety summary statistics"""
        return {
            'safety_events': self.safety_calculator.get_statistics(),
            'detected_events': self.event_detector.get_statistics()
        }

    def get_event_history(
        self,
        hours: int = 24,
        severity_filter: Optional[str] = None
    ) -> List[DetectedEvent]:
        """Get event history with filtering"""
        from trinity.av_monitoring.safety_metrics import SeverityLevel

        severity = None
        if severity_filter:
            severity = SeverityLevel(severity_filter)

        return self.event_detector.get_events(
            severity_filter=severity,
            limit=1000
        )

    def register_av_detected_callback(self, callback: Callable):
        """Register callback for AV detection"""
        self.av_detected_callbacks.append(callback)

    def register_event_callback(self, callback: Callable):
        """Register callback for event detection"""
        self.event_callbacks.append(callback)
        self.event_detector.register_callback(callback)

    def enable_feature(self, feature: str, enabled: bool):
        """
        Enable or disable features

        Args:
            feature: 'marker_detection', 'trajectory', 'safety', 'events'
            enabled: True to enable, False to disable
        """
        if feature == 'marker_detection':
            self.enable_marker_detection = enabled
        elif feature == 'trajectory':
            self.enable_trajectory_analysis = enabled
        elif feature == 'safety':
            self.enable_safety_metrics = enabled
        elif feature == 'events':
            self.enable_event_detection = enabled
        else:
            logger.warning(f"Unknown feature: {feature}")
            return

        logger.info(f"Feature '{feature}' {'enabled' if enabled else 'disabled'}")

    def reset(self):
        """Reset all monitoring systems"""
        self.av_identification.reset()
        self.trajectory_analyzer.clear_all()
        self.safety_calculator.clear_events()
        self.event_detector.clear_events()
        self.frame_count = 0
        self.session_start_time = time.time()

        logger.info("AV monitoring system reset")

    def get_statistics(self) -> Dict:
        """Get comprehensive system statistics"""
        return {
            'frame_count': self.frame_count,
            'session_duration': time.time() - self.session_start_time,
            'av_identification': self.av_identification.get_statistics(),
            'safety_metrics': self.safety_calculator.get_statistics(),
            'event_detection': self.event_detector.get_statistics(),
            'features_enabled': {
                'marker_detection': self.enable_marker_detection,
                'trajectory_analysis': self.enable_trajectory_analysis,
                'safety_metrics': self.enable_safety_metrics,
                'event_detection': self.enable_event_detection
            }
        }


def create_av_monitoring_from_config(config: Dict) -> AVMonitoringSystem:
    """
    Create AV monitoring system from configuration

    Args:
        config: Configuration dictionary

    Returns:
        Configured AVMonitoringSystem
    """
    av_config = config.get('av_monitoring', {})

    system = AVMonitoringSystem(
        config=config,
        enable_marker_detection=av_config.get('enable_marker_detection', True),
        enable_trajectory_analysis=av_config.get('enable_trajectory_analysis', True),
        enable_safety_metrics=av_config.get('enable_safety_metrics', True),
        enable_event_detection=av_config.get('enable_event_detection', True)
    )

    # Register AVs if configured
    av_vehicles = av_config.get('registered_vehicles', [])
    if av_vehicles:
        system.register_av_vehicles(av_vehicles)

    return system
