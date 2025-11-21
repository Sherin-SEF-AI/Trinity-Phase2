"""
Trinity Phase 2 - Coordinate Transformation Utilities
Handles transformations between camera, image, and world coordinates
"""

import numpy as np
import cv2
from typing import Tuple, List, Optional
from dataclasses import dataclass


@dataclass
class CameraPose:
    """Camera pose in world coordinates"""
    position: np.ndarray  # [x, y, z]
    rotation: np.ndarray  # Rotation matrix 3x3
    translation: np.ndarray  # Translation vector 3x1


class CoordinateTransformer:
    """
    Handles coordinate transformations between different reference frames
    """

    def __init__(
        self,
        camera_matrix: np.ndarray,
        dist_coeffs: np.ndarray,
        camera_pose: Optional[CameraPose] = None
    ):
        """
        Initialize coordinate transformer

        Args:
            camera_matrix: Camera intrinsic matrix (3x3)
            dist_coeffs: Distortion coefficients
            camera_pose: Camera pose in world coordinates (optional)
        """
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
        self.camera_pose = camera_pose

    @staticmethod
    def euler_to_rotation_matrix(roll: float, pitch: float, yaw: float) -> np.ndarray:
        """
        Convert Euler angles to rotation matrix

        Args:
            roll: Roll angle in degrees
            pitch: Pitch angle in degrees
            yaw: Yaw angle in degrees

        Returns:
            3x3 rotation matrix
        """
        # Convert to radians
        roll = np.radians(roll)
        pitch = np.radians(pitch)
        yaw = np.radians(yaw)

        # Rotation around X axis (roll)
        Rx = np.array([
            [1, 0, 0],
            [0, np.cos(roll), -np.sin(roll)],
            [0, np.sin(roll), np.cos(roll)]
        ])

        # Rotation around Y axis (pitch)
        Ry = np.array([
            [np.cos(pitch), 0, np.sin(pitch)],
            [0, 1, 0],
            [-np.sin(pitch), 0, np.cos(pitch)]
        ])

        # Rotation around Z axis (yaw)
        Rz = np.array([
            [np.cos(yaw), -np.sin(yaw), 0],
            [np.sin(yaw), np.cos(yaw), 0],
            [0, 0, 1]
        ])

        # Combined rotation: R = Rz * Ry * Rx
        R = Rz @ Ry @ Rx
        return R

    @staticmethod
    def rotation_matrix_to_euler(R: np.ndarray) -> Tuple[float, float, float]:
        """
        Convert rotation matrix to Euler angles

        Args:
            R: 3x3 rotation matrix

        Returns:
            (roll, pitch, yaw) in degrees
        """
        sy = np.sqrt(R[0, 0]**2 + R[1, 0]**2)

        singular = sy < 1e-6

        if not singular:
            roll = np.arctan2(R[2, 1], R[2, 2])
            pitch = np.arctan2(-R[2, 0], sy)
            yaw = np.arctan2(R[1, 0], R[0, 0])
        else:
            roll = np.arctan2(-R[1, 2], R[1, 1])
            pitch = np.arctan2(-R[2, 0], sy)
            yaw = 0

        return np.degrees(roll), np.degrees(pitch), np.degrees(yaw)

    def pixel_to_camera_coords(
        self,
        pixel_coords: np.ndarray,
        depth: float
    ) -> np.ndarray:
        """
        Convert pixel coordinates to camera coordinates

        Args:
            pixel_coords: 2D pixel coordinates [u, v]
            depth: Depth (Z coordinate) in camera frame

        Returns:
            3D point in camera coordinates [X, Y, Z]
        """
        # Extract camera parameters
        fx = self.camera_matrix[0, 0]
        fy = self.camera_matrix[1, 1]
        cx = self.camera_matrix[0, 2]
        cy = self.camera_matrix[1, 2]

        # Convert to camera coordinates
        u, v = pixel_coords
        X = (u - cx) * depth / fx
        Y = (v - cy) * depth / fy
        Z = depth

        return np.array([X, Y, Z])

    def camera_to_pixel_coords(
        self,
        camera_coords: np.ndarray
    ) -> Tuple[np.ndarray, float]:
        """
        Convert camera coordinates to pixel coordinates

        Args:
            camera_coords: 3D point in camera coordinates [X, Y, Z]

        Returns:
            (pixel_coords, depth) - 2D pixel coordinates and depth
        """
        # Extract camera parameters
        fx = self.camera_matrix[0, 0]
        fy = self.camera_matrix[1, 1]
        cx = self.camera_matrix[0, 2]
        cy = self.camera_matrix[1, 2]

        X, Y, Z = camera_coords

        # Project to image plane
        u = fx * X / Z + cx
        v = fy * Y / Z + cy

        return np.array([u, v]), Z

    def camera_to_world_coords(
        self,
        camera_coords: np.ndarray
    ) -> np.ndarray:
        """
        Convert camera coordinates to world coordinates

        Args:
            camera_coords: 3D point in camera coordinates

        Returns:
            3D point in world coordinates
        """
        if self.camera_pose is None:
            raise ValueError("Camera pose not set")

        # Apply rotation and translation
        world_coords = self.camera_pose.rotation @ camera_coords + self.camera_pose.position

        return world_coords

    def world_to_camera_coords(
        self,
        world_coords: np.ndarray
    ) -> np.ndarray:
        """
        Convert world coordinates to camera coordinates

        Args:
            world_coords: 3D point in world coordinates

        Returns:
            3D point in camera coordinates
        """
        if self.camera_pose is None:
            raise ValueError("Camera pose not set")

        # Apply inverse transformation
        camera_coords = self.camera_pose.rotation.T @ (world_coords - self.camera_pose.position)

        return camera_coords

    def pixel_to_world_coords(
        self,
        pixel_coords: np.ndarray,
        depth: float
    ) -> np.ndarray:
        """
        Convert pixel coordinates directly to world coordinates

        Args:
            pixel_coords: 2D pixel coordinates [u, v]
            depth: Depth in camera frame

        Returns:
            3D point in world coordinates
        """
        camera_coords = self.pixel_to_camera_coords(pixel_coords, depth)
        world_coords = self.camera_to_world_coords(camera_coords)
        return world_coords

    def world_to_pixel_coords(
        self,
        world_coords: np.ndarray
    ) -> Tuple[np.ndarray, float]:
        """
        Convert world coordinates to pixel coordinates

        Args:
            world_coords: 3D point in world coordinates

        Returns:
            (pixel_coords, depth)
        """
        camera_coords = self.world_to_camera_coords(world_coords)
        pixel_coords, depth = self.camera_to_pixel_coords(camera_coords)
        return pixel_coords, depth

    def compute_homography_to_ground(
        self,
        ground_plane_z: float = 0.0
    ) -> np.ndarray:
        """
        Compute homography matrix from image plane to ground plane

        Args:
            ground_plane_z: Z coordinate of ground plane in world frame

        Returns:
            3x3 homography matrix
        """
        if self.camera_pose is None:
            raise ValueError("Camera pose not set")

        # Get rotation and translation
        R = self.camera_pose.rotation
        t = self.camera_pose.position

        # Ground plane normal (assuming Z-up)
        n = np.array([0, 0, 1])
        d = -ground_plane_z

        # Compute homography: H = K * (R - t*n'/d)
        H = self.camera_matrix @ (R - np.outer(t, n) / d)

        return H

    def pixel_to_ground_plane(
        self,
        pixel_coords: np.ndarray,
        ground_plane_z: float = 0.0
    ) -> np.ndarray:
        """
        Project pixel coordinates to ground plane

        Args:
            pixel_coords: 2D pixel coordinates [u, v]
            ground_plane_z: Z coordinate of ground plane

        Returns:
            3D point on ground plane in world coordinates
        """
        H = self.compute_homography_to_ground(ground_plane_z)

        # Convert pixel to homogeneous coordinates
        pixel_h = np.array([pixel_coords[0], pixel_coords[1], 1])

        # Apply homography
        ground_h = np.linalg.inv(H) @ pixel_h

        # Convert from homogeneous
        ground_coords = ground_h[:2] / ground_h[2]

        return np.array([ground_coords[0], ground_coords[1], ground_plane_z])

    def undistort_points(
        self,
        points: np.ndarray
    ) -> np.ndarray:
        """
        Undistort image points

        Args:
            points: Nx2 array of distorted pixel coordinates

        Returns:
            Nx2 array of undistorted pixel coordinates
        """
        points = points.reshape(-1, 1, 2).astype(np.float32)
        undistorted = cv2.undistortPoints(
            points, self.camera_matrix, self.dist_coeffs,
            P=self.camera_matrix
        )
        return undistorted.reshape(-1, 2)


class MultiViewTriangulation:
    """
    Triangulate 3D points from multiple camera views
    """

    def __init__(self, transformers: List[CoordinateTransformer]):
        """
        Initialize multi-view triangulation

        Args:
            transformers: List of CoordinateTransformer objects for each camera
        """
        self.transformers = transformers

    def triangulate_point(
        self,
        pixel_coords_list: List[np.ndarray],
        camera_indices: Optional[List[int]] = None
    ) -> np.ndarray:
        """
        Triangulate 3D point from multiple 2D observations

        Args:
            pixel_coords_list: List of 2D pixel coordinates from each camera
            camera_indices: Indices of cameras to use (None = use all)

        Returns:
            3D point in world coordinates
        """
        if camera_indices is None:
            camera_indices = list(range(len(pixel_coords_list)))

        if len(camera_indices) < 2:
            raise ValueError("Need at least 2 camera views for triangulation")

        # Prepare projection matrices
        P_matrices = []
        points_2d = []

        for idx in camera_indices:
            if idx >= len(self.transformers):
                continue

            transformer = self.transformers[idx]
            if transformer.camera_pose is None:
                continue

            # Construct projection matrix P = K * [R | t]
            R = transformer.camera_pose.rotation
            t = transformer.camera_pose.position.reshape(-1, 1)
            Rt = np.hstack([R, -R @ t])  # Camera-to-world transform
            P = transformer.camera_matrix @ Rt

            P_matrices.append(P)
            points_2d.append(pixel_coords_list[idx])

        if len(P_matrices) < 2:
            raise ValueError("Need at least 2 valid camera poses")

        # Triangulate using DLT (Direct Linear Transform)
        point_3d = self._triangulate_dlt(P_matrices, points_2d)

        return point_3d

    def _triangulate_dlt(
        self,
        P_matrices: List[np.ndarray],
        points_2d: List[np.ndarray]
    ) -> np.ndarray:
        """
        Triangulate using Direct Linear Transform

        Args:
            P_matrices: List of 3x4 projection matrices
            points_2d: List of 2D points

        Returns:
            3D point in homogeneous coordinates
        """
        # Build matrix A
        A = []
        for P, point in zip(P_matrices, points_2d):
            u, v = point
            A.append(u * P[2, :] - P[0, :])
            A.append(v * P[2, :] - P[1, :])

        A = np.array(A)

        # Solve using SVD
        _, _, Vt = np.linalg.svd(A)
        point_3d_h = Vt[-1, :]

        # Convert from homogeneous
        point_3d = point_3d_h[:3] / point_3d_h[3]

        return point_3d

    def estimate_depth_from_ground(
        self,
        pixel_coords: np.ndarray,
        camera_index: int,
        ground_plane_z: float = 0.0,
        object_height: float = 1.7
    ) -> float:
        """
        Estimate depth assuming object is on ground plane

        Args:
            pixel_coords: 2D pixel coordinates
            camera_index: Index of camera
            ground_plane_z: Ground plane Z coordinate
            object_height: Estimated object height

        Returns:
            Estimated depth
        """
        transformer = self.transformers[camera_index]

        # Project to ground plane
        ground_point = transformer.pixel_to_ground_plane(pixel_coords, ground_plane_z)

        # Convert to camera coordinates
        camera_coords = transformer.world_to_camera_coords(ground_point)

        # Depth is Z coordinate in camera frame
        return camera_coords[2]


def create_extrinsic_matrix(
    position: Tuple[float, float, float],
    orientation: Tuple[float, float, float]
) -> np.ndarray:
    """
    Create 4x4 extrinsic matrix from position and orientation

    Args:
        position: (x, y, z) in meters
        orientation: (roll, pitch, yaw) in degrees

    Returns:
        4x4 extrinsic transformation matrix
    """
    # Create rotation matrix
    R = CoordinateTransformer.euler_to_rotation_matrix(*orientation)

    # Create translation vector
    t = np.array(position).reshape(-1, 1)

    # Build 4x4 matrix
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3:4] = t

    return T


def compute_baseline(pose1: CameraPose, pose2: CameraPose) -> float:
    """
    Compute baseline distance between two cameras

    Args:
        pose1: First camera pose
        pose2: Second camera pose

    Returns:
        Baseline distance in meters
    """
    return np.linalg.norm(pose1.position - pose2.position)


def compute_epipolar_line(
    point: np.ndarray,
    F: np.ndarray
) -> Tuple[float, float, float]:
    """
    Compute epipolar line in second image given point in first image

    Args:
        point: 2D point in first image [u, v]
        F: Fundamental matrix

    Returns:
        Epipolar line coefficients (a, b, c) where ax + by + c = 0
    """
    # Convert to homogeneous coordinates
    point_h = np.array([point[0], point[1], 1])

    # Compute epipolar line: l' = F * p
    line = F @ point_h

    return tuple(line)
