"""
Trinity Phase 3 - Trajectory Analysis
Analyze vehicle trajectories, predict paths, and calculate motion metrics
"""

import numpy as np
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass
from collections import deque
from scipy import interpolate
from scipy.signal import savgol_filter
from loguru import logger

from trinity.detection.tracker import Track


@dataclass
class TrajectoryPoint:
    """Single point in trajectory"""
    position: Tuple[float, float, float]  # x, y, z in world coordinates
    timestamp: float  # seconds
    velocity: Optional[Tuple[float, float, float]] = None
    acceleration: Optional[Tuple[float, float, float]] = None
    heading: Optional[float] = None  # radians


@dataclass
class TrajectoryMetrics:
    """Metrics calculated from trajectory"""
    total_distance: float  # meters
    average_speed: float  # m/s
    max_speed: float  # m/s
    average_acceleration: float  # m/s²
    max_acceleration: float  # m/s²
    max_deceleration: float  # m/s²
    path_curvature: float  # average curvature
    smoothness: float  # trajectory smoothness metric
    lateral_deviation: float  # deviation from straight path


@dataclass
class PredictedTrajectory:
    """Predicted future trajectory"""
    positions: List[Tuple[float, float, float]]  # Predicted positions
    timestamps: List[float]  # Prediction timestamps
    confidence: List[float]  # Confidence for each prediction
    method: str  # Prediction method used


class TrajectoryAnalyzer:
    """
    Analyze and predict vehicle trajectories
    """

    def __init__(
        self,
        max_history: int = 100,
        min_points_for_analysis: int = 10,
        smoothing_window: int = 5,
        prediction_horizon: float = 3.0  # seconds
    ):
        """
        Initialize trajectory analyzer

        Args:
            max_history: Maximum trajectory points to keep
            min_points_for_analysis: Minimum points needed for analysis
            smoothing_window: Window size for trajectory smoothing
            prediction_horizon: How far ahead to predict (seconds)
        """
        self.max_history = max_history
        self.min_points_for_analysis = min_points_for_analysis
        self.smoothing_window = smoothing_window
        self.prediction_horizon = prediction_horizon

        # Track trajectories
        self.trajectories: Dict[int, deque] = {}  # track_id -> deque of TrajectoryPoint

        logger.info("Trajectory analyzer initialized")

    def update_trajectory(
        self,
        track: Track,
        timestamp: float
    ):
        """
        Update trajectory for a track

        Args:
            track: Track object
            timestamp: Current timestamp (seconds)
        """
        track_id = track.track_id

        # Initialize trajectory if needed
        if track_id not in self.trajectories:
            self.trajectories[track_id] = deque(maxlen=self.max_history)

        # Extract position
        if hasattr(track, 'world_position') and track.world_position:
            position = track.world_position
        else:
            # Use 2D position if 3D not available
            center = track.get_center()
            position = (center[0], center[1], 0.0)

        # Extract velocity if available
        velocity = None
        if hasattr(track, 'velocity') and track.velocity:
            velocity = (*track.velocity, 0.0)

        # Calculate heading from velocity
        heading = None
        if velocity and velocity[0] != 0:
            heading = np.arctan2(velocity[1], velocity[0])

        # Create trajectory point
        point = TrajectoryPoint(
            position=position,
            timestamp=timestamp,
            velocity=velocity,
            heading=heading
        )

        self.trajectories[track_id].append(point)

    def get_trajectory(self, track_id: int) -> List[TrajectoryPoint]:
        """Get trajectory for track"""
        return list(self.trajectories.get(track_id, []))

    def smooth_trajectory(
        self,
        track_id: int,
        method: str = 'savgol'
    ) -> Optional[List[TrajectoryPoint]]:
        """
        Smooth trajectory using filtering

        Args:
            track_id: Track identifier
            method: Smoothing method ('savgol', 'spline', 'moving_average')

        Returns:
            Smoothed trajectory or None
        """
        trajectory = self.get_trajectory(track_id)

        if len(trajectory) < self.min_points_for_analysis:
            return None

        # Extract positions
        positions = np.array([p.position for p in trajectory])
        timestamps = np.array([p.timestamp for p in trajectory])

        if method == 'savgol':
            # Savitzky-Golay filter
            window_length = min(self.smoothing_window, len(positions))
            if window_length % 2 == 0:
                window_length -= 1
            if window_length < 3:
                return trajectory

            smoothed = savgol_filter(
                positions,
                window_length=window_length,
                polyorder=2,
                axis=0
            )

        elif method == 'spline':
            # Cubic spline interpolation
            t = np.arange(len(positions))
            spline_x = interpolate.UnivariateSpline(t, positions[:, 0], s=0.1)
            spline_y = interpolate.UnivariateSpline(t, positions[:, 1], s=0.1)
            spline_z = interpolate.UnivariateSpline(t, positions[:, 2], s=0.1)

            smoothed = np.column_stack([
                spline_x(t),
                spline_y(t),
                spline_z(t)
            ])

        elif method == 'moving_average':
            # Simple moving average
            window = self.smoothing_window
            smoothed = np.copy(positions)
            for i in range(len(positions)):
                start = max(0, i - window // 2)
                end = min(len(positions), i + window // 2 + 1)
                smoothed[i] = np.mean(positions[start:end], axis=0)

        else:
            return trajectory

        # Create smoothed trajectory points
        smoothed_traj = []
        for i, pos in enumerate(smoothed):
            point = TrajectoryPoint(
                position=tuple(pos),
                timestamp=timestamps[i]
            )
            smoothed_traj.append(point)

        return smoothed_traj

    def calculate_metrics(self, track_id: int) -> Optional[TrajectoryMetrics]:
        """
        Calculate trajectory metrics

        Args:
            track_id: Track identifier

        Returns:
            TrajectoryMetrics or None
        """
        trajectory = self.get_trajectory(track_id)

        if len(trajectory) < self.min_points_for_analysis:
            return None

        positions = np.array([p.position for p in trajectory])
        timestamps = np.array([p.timestamp for p in trajectory])

        # Calculate distances
        distances = np.linalg.norm(np.diff(positions, axis=0), axis=1)
        total_distance = np.sum(distances)

        # Calculate speeds
        time_diffs = np.diff(timestamps)
        time_diffs = np.maximum(time_diffs, 1e-6)  # Avoid division by zero
        speeds = distances / time_diffs

        avg_speed = np.mean(speeds) if len(speeds) > 0 else 0.0
        max_speed = np.max(speeds) if len(speeds) > 0 else 0.0

        # Calculate accelerations
        accelerations = np.diff(speeds) / time_diffs[:-1] if len(speeds) > 1 else np.array([])

        avg_acceleration = np.mean(np.abs(accelerations)) if len(accelerations) > 0 else 0.0
        max_acceleration = np.max(accelerations) if len(accelerations) > 0 else 0.0
        max_deceleration = np.abs(np.min(accelerations)) if len(accelerations) > 0 else 0.0

        # Calculate path curvature
        curvature = self._calculate_curvature(positions)

        # Calculate smoothness (jerk - rate of change of acceleration)
        smoothness = 0.0
        if len(accelerations) > 1:
            jerk = np.diff(accelerations) / time_diffs[:-2]
            smoothness = np.std(jerk)

        # Calculate lateral deviation from straight path
        if len(positions) > 2:
            # Vector from first to last point
            path_vector = positions[-1] - positions[0]
            path_length = np.linalg.norm(path_vector)

            if path_length > 0:
                # Calculate perpendicular distance for each point
                deviations = []
                for pos in positions[1:-1]:
                    # Point to line distance
                    point_vector = pos - positions[0]
                    projection = np.dot(point_vector, path_vector) / path_length
                    closest_point = positions[0] + (projection / path_length) * path_vector
                    deviation = np.linalg.norm(pos - closest_point)
                    deviations.append(deviation)

                lateral_deviation = np.mean(deviations) if deviations else 0.0
            else:
                lateral_deviation = 0.0
        else:
            lateral_deviation = 0.0

        return TrajectoryMetrics(
            total_distance=float(total_distance),
            average_speed=float(avg_speed),
            max_speed=float(max_speed),
            average_acceleration=float(avg_acceleration),
            max_acceleration=float(max_acceleration),
            max_deceleration=float(max_deceleration),
            path_curvature=float(curvature),
            smoothness=float(smoothness),
            lateral_deviation=float(lateral_deviation)
        )

    def _calculate_curvature(self, positions: np.ndarray) -> float:
        """Calculate average path curvature"""
        if len(positions) < 3:
            return 0.0

        curvatures = []

        for i in range(1, len(positions) - 1):
            # Three consecutive points
            p1 = positions[i - 1]
            p2 = positions[i]
            p3 = positions[i + 1]

            # Vectors
            v1 = p2 - p1
            v2 = p3 - p2

            # Angle between vectors
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            angle = np.arccos(cos_angle)

            # Curvature approximation
            dist = np.linalg.norm(v1) + np.linalg.norm(v2)
            curvature = angle / (dist + 1e-6)

            curvatures.append(curvature)

        return float(np.mean(curvatures)) if curvatures else 0.0

    def predict_trajectory(
        self,
        track_id: int,
        method: str = 'linear'
    ) -> Optional[PredictedTrajectory]:
        """
        Predict future trajectory

        Args:
            track_id: Track identifier
            method: Prediction method ('linear', 'polynomial', 'kalman')

        Returns:
            PredictedTrajectory or None
        """
        trajectory = self.get_trajectory(track_id)

        if len(trajectory) < self.min_points_for_analysis:
            return None

        # Use recent points for prediction
        recent_points = trajectory[-20:]
        positions = np.array([p.position for p in recent_points])
        timestamps = np.array([p.timestamp for p in recent_points])

        # Time steps for prediction
        last_time = timestamps[-1]
        dt = 0.1  # 10 Hz prediction
        future_times = np.arange(
            last_time + dt,
            last_time + self.prediction_horizon,
            dt
        )

        if method == 'linear':
            # Linear extrapolation from velocity
            last_pos = positions[-1]

            # Estimate velocity from recent positions
            if len(positions) >= 2:
                velocity = (positions[-1] - positions[-2]) / (timestamps[-1] - timestamps[-2] + 1e-6)
            else:
                velocity = np.zeros(3)

            # Predict positions
            predicted_positions = []
            for t in future_times:
                dt_pred = t - last_time
                pred_pos = last_pos + velocity * dt_pred
                predicted_positions.append(tuple(pred_pos))

            # Confidence decreases over time
            confidences = np.exp(-np.arange(len(future_times)) * 0.1)

        elif method == 'polynomial':
            # Polynomial fit and extrapolation
            time_normalized = timestamps - timestamps[0]
            degree = min(3, len(positions) - 1)

            poly_x = np.polyfit(time_normalized, positions[:, 0], degree)
            poly_y = np.polyfit(time_normalized, positions[:, 1], degree)
            poly_z = np.polyfit(time_normalized, positions[:, 2], degree)

            predicted_positions = []
            future_times_norm = future_times - timestamps[0]

            for t_norm in future_times_norm:
                pred_x = np.polyval(poly_x, t_norm)
                pred_y = np.polyval(poly_y, t_norm)
                pred_z = np.polyval(poly_z, t_norm)
                predicted_positions.append((pred_x, pred_y, pred_z))

            confidences = np.exp(-np.arange(len(future_times)) * 0.15)

        else:
            return None

        return PredictedTrajectory(
            positions=predicted_positions,
            timestamps=future_times.tolist(),
            confidence=confidences.tolist(),
            method=method
        )

    def detect_lane_change(self, track_id: int, threshold: float = 1.0) -> bool:
        """
        Detect if vehicle is performing a lane change

        Args:
            track_id: Track identifier
            threshold: Lateral movement threshold (meters)

        Returns:
            True if lane change detected
        """
        trajectory = self.get_trajectory(track_id)

        if len(trajectory) < 10:
            return False

        recent = trajectory[-10:]
        positions = np.array([p.position for p in recent])

        # Calculate lateral movement
        direction = positions[-1] - positions[0]
        direction_norm = np.linalg.norm(direction[:2])

        if direction_norm < 0.1:
            return False

        # Perpendicular direction
        perpendicular = np.array([-direction[1], direction[0], 0])
        perpendicular = perpendicular / (np.linalg.norm(perpendicular) + 1e-6)

        # Calculate lateral displacement
        lateral_movements = []
        for i in range(1, len(positions)):
            movement = positions[i] - positions[i-1]
            lateral = np.dot(movement, perpendicular)
            lateral_movements.append(abs(lateral))

        total_lateral = sum(lateral_movements)

        return total_lateral > threshold

    def detect_turn(self, track_id: int, angle_threshold: float = 30.0) -> bool:
        """
        Detect if vehicle is turning

        Args:
            track_id: Track identifier
            angle_threshold: Minimum angle change (degrees)

        Returns:
            True if turn detected
        """
        trajectory = self.get_trajectory(track_id)

        if len(trajectory) < 5:
            return False

        recent = trajectory[-5:]
        positions = np.array([p.position for p in recent])

        # Calculate direction vectors
        v1 = positions[len(positions)//2] - positions[0]
        v2 = positions[-1] - positions[len(positions)//2]

        # Calculate angle
        cos_angle = np.dot(v1[:2], v2[:2]) / (
            np.linalg.norm(v1[:2]) * np.linalg.norm(v2[:2]) + 1e-6
        )
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle_rad = np.arccos(cos_angle)
        angle_deg = np.degrees(angle_rad)

        return angle_deg > angle_threshold

    def clear_trajectory(self, track_id: int):
        """Clear trajectory for track"""
        if track_id in self.trajectories:
            del self.trajectories[track_id]

    def clear_all(self):
        """Clear all trajectories"""
        self.trajectories.clear()
        logger.info("All trajectories cleared")
