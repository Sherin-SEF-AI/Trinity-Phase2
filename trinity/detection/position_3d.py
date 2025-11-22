"""
Trinity Phase 2 - 3D Position Estimation
Estimate 3D positions of detected objects using multi-view geometry
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from loguru import logger

from trinity.detection.detector import Detection
from trinity.detection.tracker import Track
from trinity.utils.coordinate_transform import (
    CoordinateTransformer,
    MultiViewTriangulation,
    CameraPose
)


@dataclass
class Position3D:
    """3D position estimate"""
    world_position: Tuple[float, float, float]  # x, y, z in world coordinates
    confidence: float
    estimation_method: str  # 'triangulation', 'ground_plane', 'single_camera'
    num_cameras: int  # Number of cameras used for estimation
    reprojection_error: Optional[float] = None


class PositionEstimator3D:
    """
    3D position estimator using multi-view geometry
    """

    # Default object heights (in meters)
    DEFAULT_HEIGHTS = {
        'person': 1.7,
        'car': 1.5,
        'truck': 3.0,
        'bus': 3.5,
        'bicycle': 1.2,
        'motorcycle': 1.3,
        'dog': 0.6,
        'cat': 0.3,
    }

    def __init__(
        self,
        transformers: List[CoordinateTransformer],
        camera_names: Optional[List[str]] = None,
        ground_plane_z: float = 0.0,
        use_triangulation: bool = True,
        triangulation_min_cameras: int = 2
    ):
        """
        Initialize 3D position estimator

        Args:
            transformers: List of CoordinateTransformer objects (one per camera)
            camera_names: Names of cameras (for logging)
            ground_plane_z: Z-coordinate of ground plane in world frame
            use_triangulation: Use multi-view triangulation when possible
            triangulation_min_cameras: Minimum cameras needed for triangulation
        """
        self.transformers = transformers
        self.camera_names = camera_names or [f"Camera {i}" for i in range(len(transformers))]
        self.ground_plane_z = ground_plane_z
        self.use_triangulation = use_triangulation
        self.triangulation_min_cameras = triangulation_min_cameras

        # Multi-view triangulation
        self.triangulator = MultiViewTriangulation(transformers)

        logger.info(f"3D position estimator initialized with {len(transformers)} cameras")

    def estimate_position(
        self,
        detections_per_camera: List[Optional[Detection]],
        object_class: str
    ) -> Optional[Position3D]:
        """
        Estimate 3D position from detections across multiple cameras

        Args:
            detections_per_camera: List of detections (one per camera, None if not detected)
            object_class: Object class name

        Returns:
            Position3D object or None if estimation failed
        """
        # Filter valid detections
        valid_detections = [
            (i, det) for i, det in enumerate(detections_per_camera)
            if det is not None
        ]

        if not valid_detections:
            return None

        # Try triangulation if multiple cameras see the object
        if self.use_triangulation and len(valid_detections) >= self.triangulation_min_cameras:
            return self._triangulate_position(valid_detections, object_class)

        # Fall back to ground plane projection from single camera
        camera_idx, detection = valid_detections[0]
        return self._estimate_from_ground_plane(camera_idx, detection, object_class)

    def _triangulate_position(
        self,
        valid_detections: List[Tuple[int, Detection]],
        object_class: str
    ) -> Optional[Position3D]:
        """Estimate position using multi-view triangulation"""
        try:
            # Get center points of bounding boxes
            camera_indices = [idx for idx, _ in valid_detections]
            pixel_coords = [
                np.array(det.get_center()) for _, det in valid_detections
            ]

            # Triangulate
            world_pos = self.triangulator.triangulate_point(
                pixel_coords,
                camera_indices
            )

            # Average confidence
            avg_confidence = np.mean([det.confidence for _, det in valid_detections])

            # Calculate reprojection error
            reprojection_error = self._calculate_reprojection_error(
                world_pos, camera_indices, pixel_coords
            )

            return Position3D(
                world_position=tuple(world_pos),
                confidence=avg_confidence,
                estimation_method='triangulation',
                num_cameras=len(valid_detections),
                reprojection_error=reprojection_error
            )

        except Exception as e:
            logger.warning(f"Triangulation failed: {e}. Falling back to ground plane.")
            camera_idx, detection = valid_detections[0]
            return self._estimate_from_ground_plane(camera_idx, detection, object_class)

    def _estimate_from_ground_plane(
        self,
        camera_idx: int,
        detection: Detection,
        object_class: str
    ) -> Position3D:
        """Estimate position assuming object is on ground plane"""
        transformer = self.transformers[camera_idx]

        # Get bottom center of bounding box (foot point)
        x, y, w, h = detection.bbox
        foot_point = np.array([x + w/2, y + h])

        # Project to ground plane
        world_pos_2d = transformer.pixel_to_ground_plane(
            foot_point,
            self.ground_plane_z
        )

        # Add estimated height
        object_height = self.DEFAULT_HEIGHTS.get(object_class, 1.5)
        world_pos = (
            world_pos_2d[0],
            world_pos_2d[1],
            world_pos_2d[2] + object_height / 2  # Center of object
        )

        return Position3D(
            world_position=world_pos,
            confidence=detection.confidence,
            estimation_method='ground_plane',
            num_cameras=1,
            reprojection_error=None
        )

    def _calculate_reprojection_error(
        self,
        world_pos: np.ndarray,
        camera_indices: List[int],
        pixel_coords_observed: List[np.ndarray]
    ) -> float:
        """Calculate reprojection error"""
        errors = []

        for cam_idx, pixel_obs in zip(camera_indices, pixel_coords_observed):
            transformer = self.transformers[cam_idx]

            # Project world position back to image
            pixel_proj, _ = transformer.world_to_pixel_coords(world_pos)

            # Calculate error
            error = np.linalg.norm(pixel_proj - pixel_obs)
            errors.append(error)

        return float(np.mean(errors))

    def estimate_velocity(
        self,
        track: Track,
        time_delta: float
    ) -> Tuple[float, float, float]:
        """
        Estimate 3D velocity from track trajectory

        Args:
            track: Track with trajectory
            time_delta: Time between frames (seconds)

        Returns:
            3D velocity (vx, vy, vz) in m/s
        """
        if not hasattr(track, 'world_trajectory') or len(track.world_trajectory) < 2:
            return (0.0, 0.0, 0.0)

        # Get last two positions
        pos1 = np.array(track.world_trajectory[-2])
        pos2 = np.array(track.world_trajectory[-1])

        # Calculate velocity
        velocity = (pos2 - pos1) / time_delta

        return tuple(velocity)

    def update_track_with_3d_position(
        self,
        track: Track,
        detections_per_camera: List[Optional[Detection]]
    ) -> Track:
        """
        Update track with 3D position estimate

        Args:
            track: Track to update
            detections_per_camera: Detections from all cameras

        Returns:
            Updated track
        """
        # Estimate 3D position
        pos_3d = self.estimate_position(detections_per_camera, track.class_name)

        if pos_3d:
            # Add world position to track
            track.world_position = pos_3d.world_position
            track.position_confidence = pos_3d.confidence
            track.estimation_method = pos_3d.estimation_method

            # Add to world trajectory if it exists
            if not hasattr(track, 'world_trajectory'):
                track.world_trajectory = []

            track.world_trajectory.append(pos_3d.world_position)

            # Keep only recent history
            if len(track.world_trajectory) > 100:
                track.world_trajectory = track.world_trajectory[-100:]

        return track


class HeightEstimator:
    """
    Estimate object height from bounding box
    """

    def __init__(
        self,
        transformer: CoordinateTransformer,
        ground_plane_z: float = 0.0
    ):
        """
        Initialize height estimator

        Args:
            transformer: Coordinate transformer for camera
            ground_plane_z: Ground plane Z coordinate
        """
        self.transformer = transformer
        self.ground_plane_z = ground_plane_z

    def estimate_height(
        self,
        detection: Detection,
        world_position_2d: Optional[Tuple[float, float]] = None
    ) -> float:
        """
        Estimate object height from bounding box

        Args:
            detection: Detection object
            world_position_2d: Known 2D world position (optional)

        Returns:
            Estimated height in meters
        """
        x, y, w, h = detection.bbox

        # Get top and bottom points of bounding box
        top_point = np.array([x + w/2, y])
        bottom_point = np.array([x + w/2, y + h])

        # If world position known, use it
        if world_position_2d:
            # This would require more complex calculation
            # For now, use simple pixel-based estimate
            pass

        # Project points to ground plane
        bottom_world = self.transformer.pixel_to_ground_plane(
            bottom_point,
            self.ground_plane_z
        )

        # Estimate depth from ground plane projection
        depth = np.linalg.norm(bottom_world[:2])

        # Use similar triangles to estimate height
        # This is a simplified approach
        focal_length = self.transformer.camera_matrix[1, 1]
        image_height = h

        estimated_height = (image_height * depth) / focal_length

        return float(estimated_height)


def create_position_estimators_from_cameras(
    cameras: List[Dict],
    ground_plane_z: float = 0.0
) -> PositionEstimator3D:
    """
    Create position estimator from camera configurations

    Args:
        cameras: List of camera configuration dictionaries
        ground_plane_z: Ground plane Z coordinate

    Returns:
        PositionEstimator3D instance
    """
    from trinity.utils.coordinate_transform import create_extrinsic_matrix

    transformers = []
    camera_names = []

    for cam in cameras:
        # Load calibration data
        if 'intrinsic_matrix' in cam and 'distortion_coeffs' in cam:
            camera_matrix = np.array(cam['intrinsic_matrix'])
            dist_coeffs = np.array(cam['distortion_coeffs'])

            # Create camera pose
            position = tuple(cam.get('position', [0, 0, 0]))
            orientation = tuple(cam.get('orientation', [0, 0, 0]))

            from trinity.utils.coordinate_transform import CoordinateTransformer
            R = CoordinateTransformer.euler_to_rotation_matrix(*orientation)

            camera_pose = CameraPose(
                position=np.array(position),
                rotation=R,
                translation=np.array(position).reshape(-1, 1)
            )

            transformer = CoordinateTransformer(
                camera_matrix=camera_matrix,
                dist_coeffs=dist_coeffs,
                camera_pose=camera_pose
            )

            transformers.append(transformer)
            camera_names.append(cam.get('name', f"Camera {len(transformers)}"))

    return PositionEstimator3D(
        transformers=transformers,
        camera_names=camera_names,
        ground_plane_z=ground_plane_z
    )
