"""
Trinity Phase 3 - Safety Metrics
Calculate safety metrics for autonomous vehicle testing including TTC, near-misses, and safe distances
"""

import numpy as np
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from loguru import logger

from trinity.detection.tracker import Track


class SeverityLevel(Enum):
    """Severity levels for safety events"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SafetyEvent:
    """Safety event detected"""
    event_type: str  # 'near_miss', 'hard_brake', 'rapid_acceleration', etc.
    severity: SeverityLevel
    timestamp: datetime
    involved_track_ids: List[int]
    description: str
    metrics: Dict  # Additional metrics specific to event type
    frame_number: Optional[int] = None


@dataclass
class TTCResult:
    """Time-to-collision calculation result"""
    ttc: float  # seconds (inf if no collision predicted)
    collision_point: Optional[Tuple[float, float, float]]
    track1_id: int
    track2_id: int
    relative_velocity: float  # m/s


@dataclass
class SafetyMetrics:
    """Comprehensive safety metrics for a track"""
    track_id: int
    timestamp: datetime

    # Speed metrics
    current_speed: float  # m/s
    max_speed: float  # m/s
    speed_limit_exceeded: bool

    # Acceleration metrics
    current_acceleration: float  # m/s²
    max_acceleration: float  # m/s²
    hard_braking_detected: bool

    # Distance metrics
    min_distance_to_obstacle: float  # meters
    safe_distance_maintained: bool

    # Collision metrics
    min_ttc: Optional[float]  # seconds
    collision_risk_level: SeverityLevel


class SafetyMetricsCalculator:
    """
    Calculate safety metrics for autonomous vehicle testing
    """

    def __init__(
        self,
        speed_limit: float = 13.89,  # m/s (50 km/h)
        safe_distance_time: float = 2.0,  # seconds
        hard_brake_threshold: float = -4.0,  # m/s²
        rapid_accel_threshold: float = 3.0,  # m/s²
        ttc_warning_threshold: float = 3.0,  # seconds
        ttc_critical_threshold: float = 1.5,  # seconds
        near_miss_distance: float = 2.0  # meters
    ):
        """
        Initialize safety metrics calculator

        Args:
            speed_limit: Maximum safe speed (m/s)
            safe_distance_time: Safe following distance in time (seconds)
            hard_brake_threshold: Deceleration threshold for hard braking (m/s²)
            rapid_accel_threshold: Acceleration threshold (m/s²)
            ttc_warning_threshold: TTC threshold for warnings (seconds)
            ttc_critical_threshold: TTC threshold for critical alerts (seconds)
            near_miss_distance: Distance threshold for near-miss (meters)
        """
        self.speed_limit = speed_limit
        self.safe_distance_time = safe_distance_time
        self.hard_brake_threshold = hard_brake_threshold
        self.rapid_accel_threshold = rapid_accel_threshold
        self.ttc_warning_threshold = ttc_warning_threshold
        self.ttc_critical_threshold = ttc_critical_threshold
        self.near_miss_distance = near_miss_distance

        # Event history
        self.safety_events: List[SafetyEvent] = []

        # Track history for metric calculation
        self.track_history: Dict[int, List[Dict]] = {}

        logger.info("Safety metrics calculator initialized")

    def calculate_ttc(
        self,
        track1: Track,
        track2: Track
    ) -> Optional[TTCResult]:
        """
        Calculate time-to-collision between two tracks

        Args:
            track1: First track
            track2: Second track

        Returns:
            TTCResult or None if no collision predicted
        """
        # Get positions
        if hasattr(track1, 'world_position') and track1.world_position:
            pos1 = np.array(track1.world_position)
        else:
            center1 = track1.get_center()
            pos1 = np.array([center1[0], center1[1], 0.0])

        if hasattr(track2, 'world_position') and track2.world_position:
            pos2 = np.array(track2.world_position)
        else:
            center2 = track2.get_center()
            pos2 = np.array([center2[0], center2[1], 0.0])

        # Get velocities
        if hasattr(track1, 'velocity') and track1.velocity:
            vel1 = np.array([*track1.velocity, 0.0])
        else:
            vel1 = np.zeros(3)

        if hasattr(track2, 'velocity') and track2.velocity:
            vel2 = np.array([*track2.velocity, 0.0])
        else:
            vel2 = np.zeros(3)

        # Relative position and velocity
        rel_pos = pos2 - pos1
        rel_vel = vel2 - vel1

        # Distance
        distance = np.linalg.norm(rel_pos)

        # Relative speed
        rel_speed = np.linalg.norm(rel_vel)

        # Check if objects are approaching
        if rel_speed < 0.1:  # Moving too slowly or parallel
            return None

        # Calculate if trajectories will intersect
        # Using simple linear extrapolation
        t_collision = distance / rel_speed if rel_speed > 0 else float('inf')

        # Check if collision point is in front of both vehicles
        collision_point = pos1 + vel1 * t_collision

        # Simplified check - just use distance-based TTC
        ttc = t_collision

        # Only return if TTC is reasonable (not too far in future)
        if ttc > 10.0:
            return None

        return TTCResult(
            ttc=ttc,
            collision_point=tuple(collision_point),
            track1_id=track1.track_id,
            track2_id=track2.track_id,
            relative_velocity=rel_speed
        )

    def calculate_all_ttc(
        self,
        tracks: List[Track]
    ) -> List[TTCResult]:
        """
        Calculate TTC for all track pairs

        Args:
            tracks: List of tracks

        Returns:
            List of TTC results
        """
        ttc_results = []

        for i, track1 in enumerate(tracks):
            for track2 in tracks[i+1:]:
                ttc = self.calculate_ttc(track1, track2)
                if ttc:
                    ttc_results.append(ttc)

        return ttc_results

    def detect_near_miss(
        self,
        tracks: List[Track]
    ) -> List[SafetyEvent]:
        """
        Detect near-miss events

        Args:
            tracks: List of tracks

        Returns:
            List of near-miss safety events
        """
        events = []

        for i, track1 in enumerate(tracks):
            for track2 in tracks[i+1:]:
                # Calculate distance
                if hasattr(track1, 'world_position') and hasattr(track2, 'world_position'):
                    if track1.world_position and track2.world_position:
                        pos1 = np.array(track1.world_position)
                        pos2 = np.array(track2.world_position)
                        distance = np.linalg.norm(pos1 - pos2)
                    else:
                        continue
                else:
                    # Use 2D distance
                    center1 = np.array(track1.get_center())
                    center2 = np.array(track2.get_center())
                    distance = np.linalg.norm(center1 - center2)

                # Check for near miss
                if distance < self.near_miss_distance:
                    # Check relative velocity
                    vel1 = track1.speed if hasattr(track1, 'speed') else 0
                    vel2 = track2.speed if hasattr(track2, 'speed') else 0

                    severity = SeverityLevel.MEDIUM
                    if distance < self.near_miss_distance / 2:
                        severity = SeverityLevel.HIGH

                    event = SafetyEvent(
                        event_type='near_miss',
                        severity=severity,
                        timestamp=datetime.now(),
                        involved_track_ids=[track1.track_id, track2.track_id],
                        description=f"Near miss: {distance:.2f}m separation",
                        metrics={
                            'distance': distance,
                            'track1_class': track1.class_name,
                            'track2_class': track2.class_name,
                            'track1_speed': vel1,
                            'track2_speed': vel2
                        }
                    )

                    events.append(event)
                    self.safety_events.append(event)

        return events

    def detect_hard_braking(
        self,
        track: Track,
        previous_speed: Optional[float] = None,
        dt: float = 0.033  # 30 FPS
    ) -> Optional[SafetyEvent]:
        """
        Detect hard braking event

        Args:
            track: Track to check
            previous_speed: Previous speed (m/s)
            dt: Time delta (seconds)

        Returns:
            SafetyEvent if hard braking detected, None otherwise
        """
        if not hasattr(track, 'speed') or previous_speed is None:
            return None

        current_speed = track.speed
        deceleration = (current_speed - previous_speed) / dt

        if deceleration < self.hard_brake_threshold:
            severity = SeverityLevel.MEDIUM
            if deceleration < self.hard_brake_threshold * 1.5:
                severity = SeverityLevel.HIGH

            event = SafetyEvent(
                event_type='hard_braking',
                severity=severity,
                timestamp=datetime.now(),
                involved_track_ids=[track.track_id],
                description=f"Hard braking detected: {deceleration:.2f} m/s²",
                metrics={
                    'deceleration': deceleration,
                    'initial_speed': previous_speed,
                    'final_speed': current_speed,
                    'track_class': track.class_name
                }
            )

            self.safety_events.append(event)
            return event

        return None

    def detect_rapid_acceleration(
        self,
        track: Track,
        previous_speed: Optional[float] = None,
        dt: float = 0.033
    ) -> Optional[SafetyEvent]:
        """
        Detect rapid acceleration event

        Args:
            track: Track to check
            previous_speed: Previous speed (m/s)
            dt: Time delta (seconds)

        Returns:
            SafetyEvent if rapid acceleration detected
        """
        if not hasattr(track, 'speed') or previous_speed is None:
            return None

        current_speed = track.speed
        acceleration = (current_speed - previous_speed) / dt

        if acceleration > self.rapid_accel_threshold:
            severity = SeverityLevel.LOW
            if acceleration > self.rapid_accel_threshold * 1.5:
                severity = SeverityLevel.MEDIUM

            event = SafetyEvent(
                event_type='rapid_acceleration',
                severity=severity,
                timestamp=datetime.now(),
                involved_track_ids=[track.track_id],
                description=f"Rapid acceleration: {acceleration:.2f} m/s²",
                metrics={
                    'acceleration': acceleration,
                    'initial_speed': previous_speed,
                    'final_speed': current_speed,
                    'track_class': track.class_name
                }
            )

            self.safety_events.append(event)
            return event

        return None

    def check_safe_following_distance(
        self,
        track: Track,
        tracks: List[Track]
    ) -> Tuple[bool, float]:
        """
        Check if safe following distance is maintained

        Args:
            track: Track to check
            tracks: All tracks (to find vehicle ahead)

        Returns:
            (is_safe, distance_to_front)
        """
        if not hasattr(track, 'world_position') or not track.world_position:
            return True, float('inf')

        track_pos = np.array(track.world_position)

        # Get velocity direction
        if hasattr(track, 'velocity') and track.velocity:
            vel = np.array([*track.velocity, 0.0])
            vel_norm = np.linalg.norm(vel)
            if vel_norm > 0:
                direction = vel / vel_norm
            else:
                return True, float('inf')
        else:
            return True, float('inf')

        # Find closest vehicle in front
        min_distance = float('inf')

        for other_track in tracks:
            if other_track.track_id == track.track_id:
                continue

            if not hasattr(other_track, 'world_position') or not other_track.world_position:
                continue

            other_pos = np.array(other_track.world_position)
            to_other = other_pos - track_pos

            # Check if in front (dot product with direction)
            if np.dot(to_other, direction) > 0:
                distance = np.linalg.norm(to_other)
                min_distance = min(min_distance, distance)

        # Calculate safe distance
        speed = track.speed if hasattr(track, 'speed') else 0
        safe_distance = speed * self.safe_distance_time

        is_safe = min_distance >= safe_distance

        return is_safe, min_distance

    def calculate_track_safety_metrics(
        self,
        track: Track,
        all_tracks: List[Track]
    ) -> SafetyMetrics:
        """
        Calculate comprehensive safety metrics for a track

        Args:
            track: Track to analyze
            all_tracks: All tracks for context

        Returns:
            SafetyMetrics object
        """
        # Speed metrics
        current_speed = track.speed if hasattr(track, 'speed') else 0.0
        max_speed = current_speed  # Would need history for true max
        speed_limit_exceeded = current_speed > self.speed_limit

        # Acceleration (would need history)
        current_acceleration = 0.0
        max_acceleration = 0.0
        hard_braking_detected = False

        # Distance metrics
        safe_dist_ok, min_distance = self.check_safe_following_distance(track, all_tracks)

        # TTC metrics
        ttc_results = []
        for other_track in all_tracks:
            if other_track.track_id != track.track_id:
                ttc = self.calculate_ttc(track, other_track)
                if ttc:
                    ttc_results.append(ttc.ttc)

        min_ttc = min(ttc_results) if ttc_results else None

        # Determine collision risk level
        if min_ttc and min_ttc < self.ttc_critical_threshold:
            risk_level = SeverityLevel.CRITICAL
        elif min_ttc and min_ttc < self.ttc_warning_threshold:
            risk_level = SeverityLevel.HIGH
        elif not safe_dist_ok:
            risk_level = SeverityLevel.MEDIUM
        elif speed_limit_exceeded:
            risk_level = SeverityLevel.LOW
        else:
            risk_level = SeverityLevel.INFO

        return SafetyMetrics(
            track_id=track.track_id,
            timestamp=datetime.now(),
            current_speed=current_speed,
            max_speed=max_speed,
            speed_limit_exceeded=speed_limit_exceeded,
            current_acceleration=current_acceleration,
            max_acceleration=max_acceleration,
            hard_braking_detected=hard_braking_detected,
            min_distance_to_obstacle=min_distance,
            safe_distance_maintained=safe_dist_ok,
            min_ttc=min_ttc,
            collision_risk_level=risk_level
        )

    def get_safety_events(
        self,
        severity_filter: Optional[SeverityLevel] = None,
        event_type_filter: Optional[str] = None,
        limit: int = 100
    ) -> List[SafetyEvent]:
        """
        Get safety events with optional filtering

        Args:
            severity_filter: Filter by severity level
            event_type_filter: Filter by event type
            limit: Maximum events to return

        Returns:
            List of safety events
        """
        events = self.safety_events

        if severity_filter:
            events = [e for e in events if e.severity == severity_filter]

        if event_type_filter:
            events = [e for e in events if e.event_type == event_type_filter]

        return events[-limit:]

    def clear_events(self):
        """Clear all safety events"""
        self.safety_events.clear()
        logger.info("Safety events cleared")

    def get_statistics(self) -> Dict:
        """Get safety statistics"""
        if not self.safety_events:
            return {
                'total_events': 0,
                'by_type': {},
                'by_severity': {}
            }

        by_type = {}
        by_severity = {}

        for event in self.safety_events:
            by_type[event.event_type] = by_type.get(event.event_type, 0) + 1
            by_severity[event.severity.value] = by_severity.get(event.severity.value, 0) + 1

        return {
            'total_events': len(self.safety_events),
            'by_type': by_type,
            'by_severity': by_severity
        }
