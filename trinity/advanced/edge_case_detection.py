"""
Trinity Phase 4 - Edge Case Detection
Automatic detection and classification of edge cases for autonomous vehicle testing
"""

import numpy as np
from typing import List, Optional, Dict, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import deque
from loguru import logger

from trinity.detection.tracker import Track
from trinity.av_monitoring.safety_metrics import SafetyMetricsCalculator, SafetyEvent, TTCResult
from trinity.av_monitoring.trajectory_analysis import TrajectoryAnalyzer
from trinity.av_monitoring.event_detection import DetectedEvent


class EdgeCaseCategory(Enum):
    """Categories of edge cases"""
    # Safety-critical
    NEAR_COLLISION = "near_collision"
    PEDESTRIAN_RISK = "pedestrian_risk"
    HIGH_SPEED_CONFLICT = "high_speed_conflict"

    # Perception challenges
    OCCLUSION = "occlusion"
    WEATHER_DEGRADATION = "weather_degradation"
    LOW_VISIBILITY = "low_visibility"
    UNUSUAL_OBJECT = "unusual_object"

    # Scenario complexity
    DENSE_TRAFFIC = "dense_traffic"
    INTERSECTION_COMPLEXITY = "intersection_complexity"
    MULTI_AGENT_INTERACTION = "multi_agent_interaction"

    # Behavioral anomalies
    ERRATIC_BEHAVIOR = "erratic_behavior"
    RULE_VIOLATION = "rule_violation"
    SUDDEN_APPEARANCE = "sudden_appearance"
    TRAJECTORY_DEVIATION = "trajectory_deviation"

    # Infrastructure
    CONSTRUCTION_ZONE = "construction_zone"
    ROAD_DAMAGE = "road_damage"
    MISSING_SIGNAGE = "missing_signage"

    # Other
    UNKNOWN = "unknown"


class EdgeCaseSeverity(Enum):
    """Severity levels for edge cases"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class EdgeCaseScore:
    """Composite score for edge case severity"""
    ttc_score: float = 0.0  # Time-to-collision contribution
    speed_score: float = 0.0  # Speed contribution
    proximity_score: float = 0.0  # Proximity contribution
    complexity_score: float = 0.0  # Scenario complexity
    uncertainty_score: float = 0.0  # Detection uncertainty

    # Weights (should sum to 1.0)
    ttc_weight: float = 0.3
    speed_weight: float = 0.2
    proximity_weight: float = 0.2
    complexity_weight: float = 0.15
    uncertainty_weight: float = 0.15

    def calculate_total(self) -> float:
        """Calculate weighted total score"""
        return (
            self.ttc_score * self.ttc_weight +
            self.speed_score * self.speed_weight +
            self.proximity_score * self.proximity_weight +
            self.complexity_score * self.complexity_weight +
            self.uncertainty_score * self.uncertainty_weight
        )


@dataclass
class EdgeCase:
    """Detected edge case"""
    edge_case_id: str
    category: EdgeCaseCategory
    severity: EdgeCaseSeverity
    timestamp: datetime
    frame_number: int

    # Description and context
    description: str
    involved_track_ids: List[int]
    av_track_ids: List[int] = field(default_factory=list)

    # Scoring
    score: EdgeCaseScore = field(default_factory=EdgeCaseScore)
    total_score: float = 0.0

    # Related events and metrics
    safety_events: List[SafetyEvent] = field(default_factory=list)
    detected_events: List[DetectedEvent] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)

    # Recording metadata
    clip_start_frame: Optional[int] = None
    clip_end_frame: Optional[int] = None
    clip_path: Optional[str] = None

    # Database reference
    database_id: Optional[int] = None

    # Review status
    reviewed: bool = False
    reviewer_notes: str = ""
    ground_truth_verified: bool = False


class EdgeCaseDetector:
    """
    Automatic edge case detection for AV testing
    """

    def __init__(
        self,
        safety_calculator: SafetyMetricsCalculator,
        trajectory_analyzer: TrajectoryAnalyzer,
        config: Optional[Dict] = None
    ):
        """
        Initialize edge case detector

        Args:
            safety_calculator: Safety metrics calculator
            trajectory_analyzer: Trajectory analyzer
            config: Configuration dictionary
        """
        self.safety_calculator = safety_calculator
        self.trajectory_analyzer = trajectory_analyzer

        # Load configuration
        self.config = config or {}
        edge_config = self.config.get('edge_case_detection', {})

        # Detection thresholds
        criteria = edge_config.get('criteria', {})
        self.ttc_threshold = criteria.get('ttc_threshold', 2.0)
        self.sudden_appearance_time = criteria.get('sudden_appearance_time', 1.0)
        self.trajectory_deviation_sigma = criteria.get('trajectory_deviation_sigma', 2.0)
        self.dense_traffic_threshold = criteria.get('dense_traffic_threshold', 10)
        self.min_proximity_distance = criteria.get('min_proximity_distance', 3.0)

        # Severity scoring weights
        severity_config = edge_config.get('severity', {})
        self.score_weights = {
            'ttc_weight': severity_config.get('ttc_weight', 0.3),
            'speed_weight': severity_config.get('speed_weight', 0.2),
            'proximity_weight': severity_config.get('proximity_weight', 0.2),
            'complexity_weight': severity_config.get('complexity_weight', 0.15),
            'uncertainty_weight': severity_config.get('uncertainty_weight', 0.15)
        }

        # Edge case storage
        self.edge_cases: List[EdgeCase] = []

        # Track history for analysis
        self.track_first_seen: Dict[int, int] = {}  # track_id -> frame_number
        self.track_trajectories: Dict[int, deque] = {}  # track_id -> position history

        # Frame counter
        self.frame_number = 0

        logger.info("Edge case detector initialized")

    def process_frame(
        self,
        all_tracks: List[Track],
        av_tracks: Optional[List[Track]] = None,
        safety_events: Optional[List[SafetyEvent]] = None,
        detected_events: Optional[List[DetectedEvent]] = None,
        ttc_results: Optional[List[TTCResult]] = None,
        frame_number: Optional[int] = None
    ) -> List[EdgeCase]:
        """
        Process frame and detect edge cases

        Args:
            all_tracks: All detected tracks
            av_tracks: AV-specific tracks
            safety_events: Safety events from current frame
            detected_events: Detected events from current frame
            ttc_results: TTC calculations
            frame_number: Current frame number

        Returns:
            List of detected edge cases
        """
        if frame_number is not None:
            self.frame_number = frame_number
        else:
            self.frame_number += 1

        av_tracks = av_tracks or []
        safety_events = safety_events or []
        detected_events = detected_events or []
        ttc_results = ttc_results or []

        detected_edge_cases = []

        # Update track history
        self._update_track_history(all_tracks)

        # 1. Check for near-collision scenarios
        near_collision_cases = self._detect_near_collision(
            all_tracks, av_tracks, ttc_results, safety_events
        )
        detected_edge_cases.extend(near_collision_cases)

        # 2. Check for pedestrian risk scenarios
        pedestrian_cases = self._detect_pedestrian_risk(
            all_tracks, av_tracks
        )
        detected_edge_cases.extend(pedestrian_cases)

        # 3. Check for sudden appearances
        sudden_appearance_cases = self._detect_sudden_appearance(all_tracks)
        detected_edge_cases.extend(sudden_appearance_cases)

        # 4. Check for trajectory deviations
        trajectory_deviation_cases = self._detect_trajectory_deviation(all_tracks)
        detected_edge_cases.extend(trajectory_deviation_cases)

        # 5. Check for dense traffic scenarios
        dense_traffic_cases = self._detect_dense_traffic(all_tracks, av_tracks)
        detected_edge_cases.extend(dense_traffic_cases)

        # 6. Check for erratic behavior
        erratic_behavior_cases = self._detect_erratic_behavior(all_tracks)
        detected_edge_cases.extend(erratic_behavior_cases)

        # 7. Check for multi-agent interactions
        multi_agent_cases = self._detect_multi_agent_interaction(
            all_tracks, av_tracks
        )
        detected_edge_cases.extend(multi_agent_cases)

        # Calculate scores and severity for all edge cases
        for edge_case in detected_edge_cases:
            self._calculate_severity_score(edge_case, all_tracks, ttc_results)
            edge_case.total_score = edge_case.score.calculate_total()
            edge_case.severity = self._score_to_severity(edge_case.total_score)

            # Add to storage
            self.edge_cases.append(edge_case)

        if detected_edge_cases:
            logger.info(
                f"Detected {len(detected_edge_cases)} edge cases at frame {self.frame_number}"
            )

        return detected_edge_cases

    def _update_track_history(self, tracks: List[Track]):
        """Update track history for analysis"""
        current_track_ids = set()

        for track in tracks:
            track_id = track.track_id
            current_track_ids.add(track_id)

            # Record first seen
            if track_id not in self.track_first_seen:
                self.track_first_seen[track_id] = self.frame_number

            # Record trajectory
            if track_id not in self.track_trajectories:
                self.track_trajectories[track_id] = deque(maxlen=50)

            # Get position
            if hasattr(track, 'world_position') and track.world_position:
                pos = track.world_position
            else:
                center = track.get_center()
                pos = (center[0], center[1], 0.0)

            self.track_trajectories[track_id].append(pos)

    def _detect_near_collision(
        self,
        all_tracks: List[Track],
        av_tracks: List[Track],
        ttc_results: List[TTCResult],
        safety_events: List[SafetyEvent]
    ) -> List[EdgeCase]:
        """Detect near-collision edge cases"""
        cases = []

        # Check for critical TTC values
        critical_ttc = [ttc for ttc in ttc_results if ttc.ttc < self.ttc_threshold]

        if critical_ttc:
            # Group by involved tracks
            for ttc in critical_ttc:
                # Check if AV is involved
                av_involved = any(
                    av.track_id in [ttc.track1_id, ttc.track2_id]
                    for av in av_tracks
                )

                if av_involved:
                    edge_case = EdgeCase(
                        edge_case_id=f"near_collision_{self.frame_number}_{ttc.track1_id}_{ttc.track2_id}",
                        category=EdgeCaseCategory.NEAR_COLLISION,
                        severity=EdgeCaseSeverity.CRITICAL,  # Will be recalculated
                        timestamp=datetime.now(),
                        frame_number=self.frame_number,
                        description=f"Near collision detected: TTC={ttc.ttc:.2f}s",
                        involved_track_ids=[ttc.track1_id, ttc.track2_id],
                        av_track_ids=[av.track_id for av in av_tracks],
                        safety_events=safety_events,
                        metrics={
                            'ttc': ttc.ttc,
                            'relative_velocity': ttc.relative_velocity
                        }
                    )

                    cases.append(edge_case)

        return cases

    def _detect_pedestrian_risk(
        self,
        all_tracks: List[Track],
        av_tracks: List[Track]
    ) -> List[EdgeCase]:
        """Detect pedestrian risk scenarios"""
        cases = []

        # Find all pedestrians
        pedestrians = [t for t in all_tracks if t.class_name == 'person']

        for av in av_tracks:
            if not hasattr(av, 'world_position') or not av.world_position:
                continue

            av_pos = np.array(av.world_position)

            for ped in pedestrians:
                if not hasattr(ped, 'world_position') or not ped.world_position:
                    continue

                ped_pos = np.array(ped.world_position)
                distance = np.linalg.norm(av_pos - ped_pos)

                # Critical distance threshold
                if distance < self.min_proximity_distance:
                    edge_case = EdgeCase(
                        edge_case_id=f"pedestrian_risk_{self.frame_number}_{av.track_id}_{ped.track_id}",
                        category=EdgeCaseCategory.PEDESTRIAN_RISK,
                        severity=EdgeCaseSeverity.HIGH,
                        timestamp=datetime.now(),
                        frame_number=self.frame_number,
                        description=f"Pedestrian at critical distance: {distance:.2f}m",
                        involved_track_ids=[av.track_id, ped.track_id],
                        av_track_ids=[av.track_id],
                        metrics={
                            'distance': distance,
                            'av_speed': getattr(av, 'speed', 0.0),
                            'pedestrian_speed': getattr(ped, 'speed', 0.0)
                        }
                    )

                    cases.append(edge_case)

        return cases

    def _detect_sudden_appearance(self, tracks: List[Track]) -> List[EdgeCase]:
        """Detect sudden object appearances"""
        cases = []

        for track in tracks:
            track_id = track.track_id

            if track_id in self.track_first_seen:
                frames_since_first = self.frame_number - self.track_first_seen[track_id]

                # If object just appeared (within threshold frames)
                # and has significant speed, it's a sudden appearance
                if frames_since_first <= self.sudden_appearance_time * 30:  # Assuming 30 FPS
                    if hasattr(track, 'speed') and track.speed > 2.0:  # m/s
                        edge_case = EdgeCase(
                            edge_case_id=f"sudden_appearance_{self.frame_number}_{track_id}",
                            category=EdgeCaseCategory.SUDDEN_APPEARANCE,
                            severity=EdgeCaseSeverity.MEDIUM,
                            timestamp=datetime.now(),
                            frame_number=self.frame_number,
                            description=f"Sudden appearance of {track.class_name}",
                            involved_track_ids=[track_id],
                            metrics={
                                'frames_since_first': frames_since_first,
                                'speed': track.speed,
                                'class': track.class_name
                            }
                        )

                        cases.append(edge_case)

        return cases

    def _detect_trajectory_deviation(self, tracks: List[Track]) -> List[EdgeCase]:
        """Detect unusual trajectory deviations"""
        cases = []

        for track in tracks:
            track_id = track.track_id

            if track_id not in self.track_trajectories:
                continue

            trajectory = list(self.track_trajectories[track_id])

            if len(trajectory) < 10:
                continue

            # Calculate trajectory smoothness
            positions = np.array(trajectory)

            # Calculate acceleration changes (jerk)
            velocities = np.diff(positions, axis=0)
            accelerations = np.diff(velocities, axis=0)
            jerks = np.diff(accelerations, axis=0)

            if len(jerks) > 0:
                jerk_magnitude = np.linalg.norm(jerks, axis=1)
                jerk_std = np.std(jerk_magnitude)
                jerk_mean = np.mean(jerk_magnitude)

                # Detect significant deviations
                if jerk_std > self.trajectory_deviation_sigma * jerk_mean and jerk_mean > 0.1:
                    edge_case = EdgeCase(
                        edge_case_id=f"trajectory_deviation_{self.frame_number}_{track_id}",
                        category=EdgeCaseCategory.TRAJECTORY_DEVIATION,
                        severity=EdgeCaseSeverity.MEDIUM,
                        timestamp=datetime.now(),
                        frame_number=self.frame_number,
                        description=f"Erratic trajectory pattern for {track.class_name}",
                        involved_track_ids=[track_id],
                        metrics={
                            'jerk_std': float(jerk_std),
                            'jerk_mean': float(jerk_mean),
                            'class': track.class_name
                        }
                    )

                    cases.append(edge_case)

        return cases

    def _detect_dense_traffic(
        self,
        all_tracks: List[Track],
        av_tracks: List[Track]
    ) -> List[EdgeCase]:
        """Detect dense traffic scenarios"""
        cases = []

        # Count vehicles near AV
        for av in av_tracks:
            if not hasattr(av, 'world_position') or not av.world_position:
                continue

            av_pos = np.array(av.world_position)

            # Count nearby vehicles
            nearby_count = 0
            nearby_ids = []

            for track in all_tracks:
                if track.track_id == av.track_id:
                    continue

                if not hasattr(track, 'world_position') or not track.world_position:
                    continue

                track_pos = np.array(track.world_position)
                distance = np.linalg.norm(av_pos - track_pos)

                # Within 20 meters
                if distance < 20.0:
                    nearby_count += 1
                    nearby_ids.append(track.track_id)

            # Check if dense traffic
            if nearby_count >= self.dense_traffic_threshold:
                edge_case = EdgeCase(
                    edge_case_id=f"dense_traffic_{self.frame_number}_{av.track_id}",
                    category=EdgeCaseCategory.DENSE_TRAFFIC,
                    severity=EdgeCaseSeverity.MEDIUM,
                    timestamp=datetime.now(),
                    frame_number=self.frame_number,
                    description=f"Dense traffic scenario: {nearby_count} vehicles nearby",
                    involved_track_ids=nearby_ids,
                    av_track_ids=[av.track_id],
                    metrics={
                        'nearby_count': nearby_count,
                        'search_radius': 20.0
                    }
                )

                cases.append(edge_case)

        return cases

    def _detect_erratic_behavior(self, tracks: List[Track]) -> List[EdgeCase]:
        """Detect erratic driving behavior"""
        cases = []

        for track in tracks:
            # Only check vehicles
            if track.class_name not in ['car', 'truck', 'bus', 'motorcycle']:
                continue

            # Check for rapid direction changes (from trajectory analyzer)
            if self.trajectory_analyzer.detect_turn(track.track_id, angle_threshold=60.0):
                # Very sharp turn
                edge_case = EdgeCase(
                    edge_case_id=f"erratic_behavior_{self.frame_number}_{track.track_id}",
                    category=EdgeCaseCategory.ERRATIC_BEHAVIOR,
                    severity=EdgeCaseSeverity.MEDIUM,
                    timestamp=datetime.now(),
                    frame_number=self.frame_number,
                    description=f"Erratic behavior: sharp turn by {track.class_name}",
                    involved_track_ids=[track.track_id],
                    metrics={
                        'class': track.class_name,
                        'turn_detected': True
                    }
                )

                cases.append(edge_case)

        return cases

    def _detect_multi_agent_interaction(
        self,
        all_tracks: List[Track],
        av_tracks: List[Track]
    ) -> List[EdgeCase]:
        """Detect complex multi-agent interactions"""
        cases = []

        for av in av_tracks:
            if not hasattr(av, 'world_position') or not av.world_position:
                continue

            av_pos = np.array(av.world_position)

            # Find all agents within interaction range (10m)
            interacting_agents = []

            for track in all_tracks:
                if track.track_id == av.track_id:
                    continue

                if not hasattr(track, 'world_position') or not track.world_position:
                    continue

                track_pos = np.array(track.world_position)
                distance = np.linalg.norm(av_pos - track_pos)

                if distance < 10.0:
                    interacting_agents.append(track)

            # Check for complex interaction (multiple agents of different types)
            if len(interacting_agents) >= 3:
                agent_types = set(t.class_name for t in interacting_agents)

                # Complex if multiple different types
                if len(agent_types) >= 2:
                    edge_case = EdgeCase(
                        edge_case_id=f"multi_agent_{self.frame_number}_{av.track_id}",
                        category=EdgeCaseCategory.MULTI_AGENT_INTERACTION,
                        severity=EdgeCaseSeverity.MEDIUM,
                        timestamp=datetime.now(),
                        frame_number=self.frame_number,
                        description=f"Complex multi-agent interaction: {len(interacting_agents)} agents",
                        involved_track_ids=[t.track_id for t in interacting_agents],
                        av_track_ids=[av.track_id],
                        metrics={
                            'agent_count': len(interacting_agents),
                            'agent_types': list(agent_types)
                        }
                    )

                    cases.append(edge_case)

        return cases

    def _calculate_severity_score(
        self,
        edge_case: EdgeCase,
        all_tracks: List[Track],
        ttc_results: List[TTCResult]
    ):
        """Calculate comprehensive severity score"""
        score = EdgeCaseScore(**self.score_weights)

        # 1. TTC score
        involved_ttc = [
            ttc for ttc in ttc_results
            if ttc.track1_id in edge_case.involved_track_ids
            or ttc.track2_id in edge_case.involved_track_ids
        ]

        if involved_ttc:
            min_ttc = min(ttc.ttc for ttc in involved_ttc)
            # Normalize: 0s = 1.0, 5s+ = 0.0
            score.ttc_score = max(0.0, min(1.0, 1.0 - min_ttc / 5.0))

        # 2. Speed score
        involved_tracks = [
            t for t in all_tracks
            if t.track_id in edge_case.involved_track_ids
        ]

        if involved_tracks:
            speeds = [getattr(t, 'speed', 0.0) for t in involved_tracks]
            max_speed = max(speeds) if speeds else 0.0
            # Normalize: 0 m/s = 0.0, 20+ m/s = 1.0
            score.speed_score = min(1.0, max_speed / 20.0)

        # 3. Proximity score
        if 'distance' in edge_case.metrics:
            distance = edge_case.metrics['distance']
            # Normalize: 0m = 1.0, 10m+ = 0.0
            score.proximity_score = max(0.0, min(1.0, 1.0 - distance / 10.0))

        # 4. Complexity score
        num_agents = len(edge_case.involved_track_ids)
        # Normalize: 1 agent = 0.0, 10+ agents = 1.0
        score.complexity_score = min(1.0, (num_agents - 1) / 9.0)

        # 5. Uncertainty score (based on detection confidence)
        if involved_tracks:
            confidences = [t.confidence for t in involved_tracks]
            avg_confidence = np.mean(confidences) if confidences else 1.0
            # Lower confidence = higher uncertainty
            score.uncertainty_score = 1.0 - avg_confidence

        edge_case.score = score

    def _score_to_severity(self, score: float) -> EdgeCaseSeverity:
        """Convert numerical score to severity level"""
        if score >= 0.75:
            return EdgeCaseSeverity.CRITICAL
        elif score >= 0.5:
            return EdgeCaseSeverity.HIGH
        elif score >= 0.25:
            return EdgeCaseSeverity.MEDIUM
        else:
            return EdgeCaseSeverity.LOW

    def get_edge_cases(
        self,
        category_filter: Optional[EdgeCaseCategory] = None,
        severity_filter: Optional[EdgeCaseSeverity] = None,
        min_score: Optional[float] = None,
        limit: int = 100
    ) -> List[EdgeCase]:
        """Get edge cases with filtering"""
        cases = self.edge_cases

        if category_filter:
            cases = [c for c in cases if c.category == category_filter]

        if severity_filter:
            cases = [c for c in cases if c.severity == severity_filter]

        if min_score is not None:
            cases = [c for c in cases if c.total_score >= min_score]

        # Sort by score (descending)
        cases = sorted(cases, key=lambda c: c.total_score, reverse=True)

        return cases[:limit]

    def get_statistics(self) -> Dict:
        """Get edge case statistics"""
        if not self.edge_cases:
            return {
                'total_cases': 0,
                'by_category': {},
                'by_severity': {},
                'avg_score': 0.0
            }

        by_category = {}
        by_severity = {}

        for case in self.edge_cases:
            # By category
            cat_name = case.category.value
            by_category[cat_name] = by_category.get(cat_name, 0) + 1

            # By severity
            sev_name = case.severity.name
            by_severity[sev_name] = by_severity.get(sev_name, 0) + 1

        avg_score = np.mean([c.total_score for c in self.edge_cases])

        return {
            'total_cases': len(self.edge_cases),
            'by_category': by_category,
            'by_severity': by_severity,
            'avg_score': float(avg_score),
            'critical_cases': len([c for c in self.edge_cases if c.severity == EdgeCaseSeverity.CRITICAL])
        }

    def export_for_dataset(
        self,
        min_severity: EdgeCaseSeverity = EdgeCaseSeverity.MEDIUM
    ) -> List[Dict]:
        """Export edge cases for dataset curation"""
        filtered_cases = [
            c for c in self.edge_cases
            if c.severity.value >= min_severity.value
        ]

        return [
            {
                'edge_case_id': c.edge_case_id,
                'category': c.category.value,
                'severity': c.severity.name,
                'timestamp': c.timestamp.isoformat(),
                'frame_number': c.frame_number,
                'description': c.description,
                'total_score': c.total_score,
                'clip_start_frame': c.clip_start_frame,
                'clip_end_frame': c.clip_end_frame,
                'clip_path': c.clip_path,
                'metrics': c.metrics
            }
            for c in filtered_cases
        ]

    def clear(self):
        """Clear all edge cases"""
        self.edge_cases.clear()
        self.track_first_seen.clear()
        self.track_trajectories.clear()
        logger.info("Edge case detector cleared")
