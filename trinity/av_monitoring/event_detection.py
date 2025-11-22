"""
Trinity Phase 3 - Event Detection and Logging
Automatic event detection, classification, and clip extraction for AV testing
"""

import numpy as np
from typing import List, Optional, Dict, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

from trinity.detection.tracker import Track
from trinity.av_monitoring.safety_metrics import (
    SafetyEvent, SeverityLevel, SafetyMetricsCalculator
)
from trinity.av_monitoring.trajectory_analysis import TrajectoryAnalyzer


@dataclass
class EventRule:
    """Rule for automatic event detection"""
    name: str
    description: str
    condition: Callable  # Function that takes context and returns bool
    severity: SeverityLevel
    pre_roll: float = 5.0  # seconds
    post_roll: float = 10.0  # seconds
    enabled: bool = True


@dataclass
class DetectedEvent:
    """Detected event with context"""
    event_id: str
    rule_name: str
    timestamp: datetime
    severity: SeverityLevel
    description: str
    involved_track_ids: List[int]
    frame_number: int

    # Metrics and context
    metrics: Dict = field(default_factory=dict)
    safety_events: List[SafetyEvent] = field(default_factory=list)

    # Recording info
    should_record: bool = True
    pre_roll_seconds: float = 5.0
    post_roll_seconds: float = 10.0
    clip_path: Optional[str] = None

    # Database reference
    database_id: Optional[int] = None


class EventDetectionSystem:
    """
    Automatic event detection and logging system
    """

    def __init__(
        self,
        safety_calculator: SafetyMetricsCalculator,
        trajectory_analyzer: TrajectoryAnalyzer,
        auto_clip_extraction: bool = True
    ):
        """
        Initialize event detection system

        Args:
            safety_calculator: Safety metrics calculator
            trajectory_analyzer: Trajectory analyzer
            auto_clip_extraction: Automatically extract clips for events
        """
        self.safety_calculator = safety_calculator
        self.trajectory_analyzer = trajectory_analyzer
        self.auto_clip_extraction = auto_clip_extraction

        # Event rules
        self.rules: List[EventRule] = []
        self._setup_default_rules()

        # Detected events
        self.detected_events: List[DetectedEvent] = []

        # Event callbacks
        self.event_callbacks: List[Callable] = []

        # Frame counter
        self.frame_number = 0

        logger.info("Event detection system initialized")

    def _setup_default_rules(self):
        """Setup default event detection rules"""

        # Rule 1: Near-miss detection
        def near_miss_condition(context: Dict) -> bool:
            near_misses = context.get('near_miss_events', [])
            return len(near_misses) > 0

        self.add_rule(EventRule(
            name='near_miss',
            description='Objects came dangerously close',
            condition=near_miss_condition,
            severity=SeverityLevel.HIGH,
            pre_roll=5.0,
            post_roll=10.0
        ))

        # Rule 2: High-speed approach
        def high_speed_condition(context: Dict) -> bool:
            ttc_results = context.get('ttc_results', [])
            for ttc in ttc_results:
                if ttc.ttc < 2.0 and ttc.relative_velocity > 5.0:
                    return True
            return False

        self.add_rule(EventRule(
            name='high_speed_approach',
            description='High-speed vehicle approach detected',
            condition=high_speed_condition,
            severity=SeverityLevel.CRITICAL,
            pre_roll=5.0,
            post_roll=15.0
        ))

        # Rule 3: Hard braking
        def hard_braking_condition(context: Dict) -> bool:
            safety_events = context.get('safety_events', [])
            return any(e.event_type == 'hard_braking' for e in safety_events)

        self.add_rule(EventRule(
            name='hard_braking',
            description='Hard braking detected',
            condition=hard_braking_condition,
            severity=SeverityLevel.MEDIUM,
            pre_roll=3.0,
            post_roll=5.0
        ))

        # Rule 4: Lane change
        def lane_change_condition(context: Dict) -> bool:
            av_tracks = context.get('av_tracks', [])
            for track in av_tracks:
                if self.trajectory_analyzer.detect_lane_change(track.track_id):
                    return True
            return False

        self.add_rule(EventRule(
            name='lane_change',
            description='Lane change maneuver',
            condition=lane_change_condition,
            severity=SeverityLevel.INFO,
            pre_roll=2.0,
            post_roll=3.0
        ))

        # Rule 5: Sharp turn
        def sharp_turn_condition(context: Dict) -> bool:
            av_tracks = context.get('av_tracks', [])
            for track in av_tracks:
                if self.trajectory_analyzer.detect_turn(track.track_id, angle_threshold=45.0):
                    return True
            return False

        self.add_rule(EventRule(
            name='sharp_turn',
            description='Sharp turn detected',
            condition=sharp_turn_condition,
            severity=SeverityLevel.LOW,
            pre_roll=2.0,
            post_roll=3.0
        ))

        # Rule 6: Speed limit violation
        def speed_violation_condition(context: Dict) -> bool:
            av_tracks = context.get('av_tracks', [])
            for track in av_tracks:
                if hasattr(track, 'speed') and track.speed > 15.0:  # ~54 km/h
                    return True
            return False

        self.add_rule(EventRule(
            name='speed_violation',
            description='Speed limit exceeded',
            condition=speed_violation_condition,
            severity=SeverityLevel.LOW,
            pre_roll=2.0,
            post_roll=2.0
        ))

        # Rule 7: Pedestrian interaction
        def pedestrian_interaction_condition(context: Dict) -> bool:
            av_tracks = context.get('av_tracks', [])
            all_tracks = context.get('all_tracks', [])

            for av_track in av_tracks:
                if not hasattr(av_track, 'world_position') or not av_track.world_position:
                    continue

                av_pos = np.array(av_track.world_position)

                for other_track in all_tracks:
                    if other_track.class_name == 'person':
                        if hasattr(other_track, 'world_position') and other_track.world_position:
                            person_pos = np.array(other_track.world_position)
                            distance = np.linalg.norm(av_pos - person_pos)

                            if distance < 5.0:  # Within 5 meters
                                return True
            return False

        self.add_rule(EventRule(
            name='pedestrian_interaction',
            description='AV near pedestrian',
            condition=pedestrian_interaction_condition,
            severity=SeverityLevel.MEDIUM,
            pre_roll=3.0,
            post_roll=5.0
        ))

        logger.info(f"Loaded {len(self.rules)} default event detection rules")

    def add_rule(self, rule: EventRule):
        """Add custom event detection rule"""
        self.rules.append(rule)
        logger.info(f"Added event rule: {rule.name}")

    def remove_rule(self, rule_name: str) -> bool:
        """Remove event detection rule"""
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                self.rules.pop(i)
                logger.info(f"Removed event rule: {rule_name}")
                return True
        return False

    def enable_rule(self, rule_name: str, enabled: bool = True):
        """Enable or disable a rule"""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = enabled
                logger.info(f"Rule '{rule_name}' {'enabled' if enabled else 'disabled'}")
                return

    def process_frame(
        self,
        all_tracks: List[Track],
        av_tracks: Optional[List[Track]] = None,
        frame_number: Optional[int] = None
    ) -> List[DetectedEvent]:
        """
        Process frame and detect events

        Args:
            all_tracks: All detected tracks
            av_tracks: AV-specific tracks
            frame_number: Current frame number

        Returns:
            List of detected events
        """
        if frame_number is not None:
            self.frame_number = frame_number
        else:
            self.frame_number += 1

        detected = []

        # Calculate safety metrics
        ttc_results = self.safety_calculator.calculate_all_ttc(all_tracks)
        near_miss_events = self.safety_calculator.detect_near_miss(all_tracks)

        # Collect all safety events
        safety_events = []
        for track in all_tracks:
            # Check for hard braking, rapid acceleration, etc.
            # Would need track history for this
            pass

        # Build context for rule evaluation
        context = {
            'all_tracks': all_tracks,
            'av_tracks': av_tracks or [],
            'ttc_results': ttc_results,
            'near_miss_events': near_miss_events,
            'safety_events': safety_events,
            'frame_number': self.frame_number
        }

        # Evaluate each rule
        for rule in self.rules:
            if not rule.enabled:
                continue

            try:
                if rule.condition(context):
                    # Create event
                    event_id = f"{rule.name}_{self.frame_number}_{datetime.now().timestamp()}"

                    # Collect involved track IDs
                    involved_ids = []
                    if rule.name == 'near_miss' and near_miss_events:
                        involved_ids = near_miss_events[0].involved_track_ids
                    elif av_tracks:
                        involved_ids = [t.track_id for t in av_tracks]

                    event = DetectedEvent(
                        event_id=event_id,
                        rule_name=rule.name,
                        timestamp=datetime.now(),
                        severity=rule.severity,
                        description=rule.description,
                        involved_track_ids=involved_ids,
                        frame_number=self.frame_number,
                        pre_roll_seconds=rule.pre_roll,
                        post_roll_seconds=rule.post_roll,
                        safety_events=safety_events
                    )

                    # Add metrics
                    event.metrics['ttc_results'] = [
                        {
                            'ttc': ttc.ttc,
                            'track1_id': ttc.track1_id,
                            'track2_id': ttc.track2_id,
                            'relative_velocity': ttc.relative_velocity
                        }
                        for ttc in ttc_results
                    ]

                    detected.append(event)
                    self.detected_events.append(event)

                    # Trigger callbacks
                    for callback in self.event_callbacks:
                        callback(event)

                    logger.info(
                        f"Event detected: {rule.name} "
                        f"(severity: {rule.severity.value}, frame: {self.frame_number})"
                    )

            except Exception as e:
                logger.error(f"Error evaluating rule '{rule.name}': {e}")

        return detected

    def register_callback(self, callback: Callable):
        """Register callback for event detection"""
        self.event_callbacks.append(callback)

    def get_events(
        self,
        severity_filter: Optional[SeverityLevel] = None,
        rule_filter: Optional[str] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        limit: int = 100
    ) -> List[DetectedEvent]:
        """
        Get detected events with filtering

        Args:
            severity_filter: Filter by severity
            rule_filter: Filter by rule name
            time_range: Filter by time range (start, end)
            limit: Maximum events to return

        Returns:
            Filtered list of events
        """
        events = self.detected_events

        if severity_filter:
            events = [e for e in events if e.severity == severity_filter]

        if rule_filter:
            events = [e for e in events if e.rule_name == rule_filter]

        if time_range:
            start, end = time_range
            events = [e for e in events if start <= e.timestamp <= end]

        return events[-limit:]

    def get_critical_events(self, hours: int = 24) -> List[DetectedEvent]:
        """Get critical events from last N hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            e for e in self.detected_events
            if e.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]
            and e.timestamp >= cutoff
        ]

    def export_events_to_dict(self) -> List[Dict]:
        """Export events to dictionary format for database storage"""
        return [
            {
                'event_id': e.event_id,
                'rule_name': e.rule_name,
                'timestamp': e.timestamp.isoformat(),
                'severity': e.severity.value,
                'description': e.description,
                'involved_track_ids': e.involved_track_ids,
                'frame_number': e.frame_number,
                'metrics': e.metrics,
                'clip_path': e.clip_path
            }
            for e in self.detected_events
        ]

    def clear_events(self):
        """Clear all detected events"""
        self.detected_events.clear()
        logger.info("All detected events cleared")

    def get_statistics(self) -> Dict:
        """Get event detection statistics"""
        if not self.detected_events:
            return {
                'total_events': 0,
                'by_rule': {},
                'by_severity': {},
                'by_hour': {}
            }

        by_rule = {}
        by_severity = {}
        by_hour = {}

        for event in self.detected_events:
            # By rule
            by_rule[event.rule_name] = by_rule.get(event.rule_name, 0) + 1

            # By severity
            by_severity[event.severity.value] = by_severity.get(event.severity.value, 0) + 1

            # By hour
            hour_key = event.timestamp.strftime('%Y-%m-%d %H:00')
            by_hour[hour_key] = by_hour.get(hour_key, 0) + 1

        return {
            'total_events': len(self.detected_events),
            'by_rule': by_rule,
            'by_severity': by_severity,
            'by_hour': by_hour,
            'enabled_rules': sum(1 for r in self.rules if r.enabled),
            'total_rules': len(self.rules)
        }
