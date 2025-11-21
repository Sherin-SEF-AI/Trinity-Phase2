"""
Trinity Phase 2 - Camera Calibration Module
Handles camera intrinsic and extrinsic calibration
"""

import cv2
import cv2.aruco as aruco
import numpy as np
from typing import List, Tuple, Optional, Dict
from pathlib import Path
from datetime import datetime
from loguru import logger


class CameraCalibration:
    """Camera calibration using checkerboard or ArUco markers"""

    def __init__(
        self,
        checkerboard_size: Tuple[int, int] = (9, 6),
        square_size_mm: float = 25.0,
        aruco_dict_name: str = "DICT_6X6_250",
        marker_size_mm: float = 100.0
    ):
        """
        Initialize calibration

        Args:
            checkerboard_size: Number of internal corners (width, height)
            square_size_mm: Size of checkerboard squares in millimeters
            aruco_dict_name: ArUco dictionary name
            marker_size_mm: Size of ArUco markers in millimeters
        """
        self.checkerboard_size = checkerboard_size
        self.square_size_mm = square_size_mm
        self.marker_size_mm = marker_size_mm

        # ArUco setup
        aruco_dict_id = getattr(aruco, aruco_dict_name, aruco.DICT_6X6_250)
        self.aruco_dict = aruco.getPredefinedDictionary(aruco_dict_id)
        self.aruco_params = aruco.DetectorParameters()

        # Calibration data
        self.camera_matrix = None
        self.dist_coeffs = None
        self.calibration_error = None

    def calibrate_from_images(
        self,
        image_paths: List[str],
        method: str = 'checkerboard'
    ) -> Tuple[np.ndarray, np.ndarray, float]:
        """
        Calibrate camera from multiple images

        Args:
            image_paths: List of calibration image paths
            method: 'checkerboard' or 'aruco'

        Returns:
            (camera_matrix, dist_coeffs, reprojection_error)
        """
        if method == 'checkerboard':
            return self._calibrate_checkerboard(image_paths)
        elif method == 'aruco':
            return self._calibrate_aruco(image_paths)
        else:
            raise ValueError(f"Unknown calibration method: {method}")

    def _calibrate_checkerboard(
        self,
        image_paths: List[str]
    ) -> Tuple[np.ndarray, np.ndarray, float]:
        """Calibrate using checkerboard pattern"""

        # Prepare object points (3D points in real world space)
        objp = np.zeros((self.checkerboard_size[0] * self.checkerboard_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[
            0:self.checkerboard_size[0],
            0:self.checkerboard_size[1]
        ].T.reshape(-1, 2)
        objp *= self.square_size_mm / 1000.0  # Convert to meters

        # Arrays to store object points and image points
        objpoints = []  # 3D points in real world space
        imgpoints = []  # 2D points in image plane

        # Termination criteria for corner refinement
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

        image_size = None
        successful_images = 0

        for img_path in image_paths:
            img = cv2.imread(img_path)
            if img is None:
                logger.warning(f"Failed to load image: {img_path}")
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            image_size = gray.shape[::-1]

            # Find checkerboard corners
            ret, corners = cv2.findChessboardCorners(gray, self.checkerboard_size, None)

            if ret:
                objpoints.append(objp)

                # Refine corner positions
                corners_refined = cv2.cornerSubPix(
                    gray, corners, (11, 11), (-1, -1), criteria
                )
                imgpoints.append(corners_refined)

                successful_images += 1
                logger.info(f"Found checkerboard in {Path(img_path).name}")
            else:
                logger.warning(f"Checkerboard not found in {Path(img_path).name}")

        if successful_images < 3:
            raise ValueError(f"Need at least 3 successful images, got {successful_images}")

        logger.info(f"Calibrating with {successful_images} images...")

        # Calibrate camera
        ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
            objpoints, imgpoints, image_size, None, None
        )

        # Calculate reprojection error
        mean_error = 0
        for i in range(len(objpoints)):
            imgpoints_reprojected, _ = cv2.projectPoints(
                objpoints[i], rvecs[i], tvecs[i], camera_matrix, dist_coeffs
            )
            error = cv2.norm(imgpoints[i], imgpoints_reprojected, cv2.NORM_L2) / len(imgpoints_reprojected)
            mean_error += error

        reprojection_error = mean_error / len(objpoints)

        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
        self.calibration_error = reprojection_error

        logger.success(
            f"Calibration completed. Reprojection error: {reprojection_error:.4f} pixels"
        )

        return camera_matrix, dist_coeffs, reprojection_error

    def _calibrate_aruco(
        self,
        image_paths: List[str]
    ) -> Tuple[np.ndarray, np.ndarray, float]:
        """Calibrate using ArUco markers"""

        all_corners = []
        all_ids = []
        image_size = None

        for img_path in image_paths:
            img = cv2.imread(img_path)
            if img is None:
                logger.warning(f"Failed to load image: {img_path}")
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            image_size = gray.shape[::-1]

            # Detect ArUco markers
            detector = aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
            corners, ids, rejected = detector.detectMarkers(gray)

            if ids is not None and len(ids) > 0:
                all_corners.append(corners)
                all_ids.append(ids)
                logger.info(f"Found {len(ids)} ArUco markers in {Path(img_path).name}")
            else:
                logger.warning(f"No ArUco markers found in {Path(img_path).name}")

        if len(all_corners) < 3:
            raise ValueError(f"Need at least 3 images with markers, got {len(all_corners)}")

        logger.info(f"Calibrating with {len(all_corners)} images...")

        # Calibrate camera using ArUco
        ret, camera_matrix, dist_coeffs, rvecs, tvecs = aruco.calibrateCameraAruco(
            all_corners, all_ids, np.array([len(c) for c in all_corners]),
            None, image_size, None, None
        )

        # Estimate reprojection error
        total_error = 0
        total_points = 0

        for i in range(len(all_corners)):
            for j, corner in enumerate(all_corners[i]):
                imgpoints_reprojected, _ = cv2.projectPoints(
                    self._get_aruco_objpoints(), rvecs[i], tvecs[i],
                    camera_matrix, dist_coeffs
                )
                error = cv2.norm(corner, imgpoints_reprojected, cv2.NORM_L2)
                total_error += error
                total_points += len(corner)

        reprojection_error = total_error / total_points if total_points > 0 else 0

        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
        self.calibration_error = reprojection_error

        logger.success(
            f"ArUco calibration completed. Reprojection error: {reprojection_error:.4f} pixels"
        )

        return camera_matrix, dist_coeffs, reprojection_error

    def _get_aruco_objpoints(self) -> np.ndarray:
        """Get 3D object points for ArUco marker"""
        marker_size = self.marker_size_mm / 1000.0  # Convert to meters
        return np.array([
            [-marker_size/2, marker_size/2, 0],
            [marker_size/2, marker_size/2, 0],
            [marker_size/2, -marker_size/2, 0],
            [-marker_size/2, -marker_size/2, 0]
        ], dtype=np.float32)

    def estimate_pose(
        self,
        image: np.ndarray,
        method: str = 'aruco'
    ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Estimate camera pose from a single image

        Args:
            image: Input image
            method: 'checkerboard' or 'aruco'

        Returns:
            (rvec, tvec) or None if detection failed
        """
        if self.camera_matrix is None:
            raise ValueError("Camera not calibrated. Run calibrate_from_images() first.")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        if method == 'checkerboard':
            return self._estimate_pose_checkerboard(gray)
        elif method == 'aruco':
            return self._estimate_pose_aruco(gray)
        else:
            raise ValueError(f"Unknown pose estimation method: {method}")

    def _estimate_pose_checkerboard(self, gray: np.ndarray) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Estimate pose using checkerboard"""
        ret, corners = cv2.findChessboardCorners(gray, self.checkerboard_size, None)

        if not ret:
            return None

        # Refine corners
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

        # Prepare object points
        objp = np.zeros((self.checkerboard_size[0] * self.checkerboard_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[
            0:self.checkerboard_size[0],
            0:self.checkerboard_size[1]
        ].T.reshape(-1, 2)
        objp *= self.square_size_mm / 1000.0

        # Estimate pose
        ret, rvec, tvec = cv2.solvePnP(
            objp, corners_refined, self.camera_matrix, self.dist_coeffs
        )

        return (rvec, tvec) if ret else None

    def _estimate_pose_aruco(self, gray: np.ndarray) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Estimate pose using ArUco markers"""
        detector = aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        corners, ids, rejected = detector.detectMarkers(gray)

        if ids is None or len(ids) == 0:
            return None

        # Use first detected marker
        marker_corners = corners[0]
        marker_size = self.marker_size_mm / 1000.0

        # Estimate pose
        rvec, tvec, _ = aruco.estimatePoseSingleMarkers(
            marker_corners, marker_size, self.camera_matrix, self.dist_coeffs
        )

        return (rvec[0][0], tvec[0][0])

    def undistort_image(self, image: np.ndarray) -> np.ndarray:
        """
        Undistort image using calibration parameters

        Args:
            image: Distorted image

        Returns:
            Undistorted image
        """
        if self.camera_matrix is None or self.dist_coeffs is None:
            raise ValueError("Camera not calibrated")

        h, w = image.shape[:2]
        new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
            self.camera_matrix, self.dist_coeffs, (w, h), 1, (w, h)
        )

        undistorted = cv2.undistort(
            image, self.camera_matrix, self.dist_coeffs, None, new_camera_matrix
        )

        # Crop the image
        x, y, w, h = roi
        undistorted = undistorted[y:y+h, x:x+w]

        return undistorted

    def save_calibration(self, filepath: str):
        """Save calibration parameters to file"""
        if self.camera_matrix is None:
            raise ValueError("No calibration data to save")

        data = {
            'camera_matrix': self.camera_matrix.tolist(),
            'dist_coeffs': self.dist_coeffs.tolist(),
            'calibration_error': float(self.calibration_error),
            'calibration_date': datetime.now().isoformat(),
            'checkerboard_size': self.checkerboard_size,
            'square_size_mm': self.square_size_mm,
        }

        np.savez(filepath, **data)
        logger.info(f"Calibration saved to {filepath}")

    def load_calibration(self, filepath: str):
        """Load calibration parameters from file"""
        data = np.load(filepath, allow_pickle=True)

        self.camera_matrix = np.array(data['camera_matrix'])
        self.dist_coeffs = np.array(data['dist_coeffs'])
        self.calibration_error = float(data['calibration_error'])

        logger.info(f"Calibration loaded from {filepath}")
        logger.info(f"Calibration error: {self.calibration_error:.4f} pixels")

    def get_calibration_info(self) -> Dict:
        """Get calibration information as dictionary"""
        if self.camera_matrix is None:
            return {'calibrated': False}

        # Extract focal lengths and principal point
        fx = self.camera_matrix[0, 0]
        fy = self.camera_matrix[1, 1]
        cx = self.camera_matrix[0, 2]
        cy = self.camera_matrix[1, 2]

        return {
            'calibrated': True,
            'focal_length_x': fx,
            'focal_length_y': fy,
            'principal_point_x': cx,
            'principal_point_y': cy,
            'distortion_coeffs': self.dist_coeffs.flatten().tolist(),
            'calibration_error': self.calibration_error,
            'camera_matrix': self.camera_matrix.tolist(),
        }


def calibrate_stereo_cameras(
    calib1: CameraCalibration,
    calib2: CameraCalibration,
    image_pairs: List[Tuple[str, str]]
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Calibrate stereo camera pair

    Args:
        calib1: Calibration object for camera 1 (must be calibrated)
        calib2: Calibration object for camera 2 (must be calibrated)
        image_pairs: List of (image1_path, image2_path) tuples

    Returns:
        (R, T, E, F) - Rotation, Translation, Essential, Fundamental matrices
    """
    if calib1.camera_matrix is None or calib2.camera_matrix is None:
        raise ValueError("Both cameras must be calibrated first")

    # This is a simplified version - full implementation would extract corresponding points
    # and use cv2.stereoCalibrate()

    logger.warning("Stereo calibration is a placeholder - full implementation needed")

    # Placeholder return
    R = np.eye(3)
    T = np.zeros((3, 1))
    E = np.eye(3)
    F = np.eye(3)

    return R, T, E, F


def main():
    """CLI for camera calibration"""
    import argparse

    parser = argparse.ArgumentParser(description='Trinity Camera Calibration')
    parser.add_argument('images', nargs='+', help='Calibration images')
    parser.add_argument('--method', choices=['checkerboard', 'aruco'], default='checkerboard')
    parser.add_argument('--output', '-o', required=True, help='Output calibration file')
    parser.add_argument('--checkerboard-size', type=int, nargs=2, default=[9, 6])
    parser.add_argument('--square-size', type=float, default=25.0, help='Square size in mm')
    parser.add_argument('--marker-size', type=float, default=100.0, help='ArUco marker size in mm')

    args = parser.parse_args()

    calibration = CameraCalibration(
        checkerboard_size=tuple(args.checkerboard_size),
        square_size_mm=args.square_size,
        marker_size_mm=args.marker_size
    )

    try:
        camera_matrix, dist_coeffs, error = calibration.calibrate_from_images(
            args.images, method=args.method
        )

        print("\nCalibration Results:")
        print(f"Camera Matrix:\n{camera_matrix}")
        print(f"\nDistortion Coefficients:\n{dist_coeffs}")
        print(f"\nReprojection Error: {error:.4f} pixels")

        calibration.save_calibration(args.output)
        print(f"\nCalibration saved to: {args.output}")

    except Exception as e:
        print(f"Calibration failed: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
