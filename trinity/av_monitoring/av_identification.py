"""
Trinity Phase 3 - AV Vehicle Identification
Identify and track autonomous vehicles using visual markers (ArUco) and tracking data
"""

import cv2
import numpy as np
from typing import List, Optional, Dict, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from loguru import logger

from trinity.detection.tracker import Track


@dataclass
class AVMarker:
    """ArUco marker detected on AV vehicle"""
    marker_id: int
    corners: np.ndarray  # 4x2 array of corner coordinates
    center: Tuple[float, float]
    camera_id: int
    timestamp: datetime
    confidence: float = 1.0


@dataclass
class AVVehicle:
    """Autonomous vehicle with persistent ID"""
    av_id: str  # Unique AV identifier (e.g., "AV001")
    marker_ids: Set[int] = field(default_factory=set)  # ArUco marker IDs
    track_id: Optional[int] = None  # Current track ID
    track_history: List[int] = field(default_factory=list)  # Historical track IDs

    # State information
    is_active: bool = True
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)

    # Statistics
    total_frames_tracked: int = 0
    total_distance_traveled: float = 0.0  # meters

    # Metadata
    vehicle_type: str = "car"  # car, truck, bus
    notes: str = ""


class ArUcoDetector:
    """
    Detect ArUco markers on autonomous vehicles
    """

    # ArUco dictionary types
    ARUCO_DICT_4X4_50 = cv2.aruco.DICT_4X4_50
    ARUCO_DICT_5X5_50 = cv2.aruco.DICT_5X5_50
    ARUCO_DICT_6X6_50 = cv2.aruco.DICT_6X6_50
    ARUCO_DICT_7X7_50 = cv2.aruco.DICT_7X7_50

    def __init__(
        self,
        dictionary_type: int = cv2.aruco.DICT_4X4_50,
        min_marker_perimeter: int = 100,
        adaptiveThreshWinSizeMin: int = 3,
        adaptiveThreshWinSizeMax: int = 23,
        adaptiveThreshWinSizeStep: int = 10
    ):
        """
        Initialize ArUco marker detector

        Args:
            dictionary_type: ArUco dictionary to use
            min_marker_perimeter: Minimum marker perimeter in pixels
            adaptiveThreshWinSizeMin: Minimum window size for adaptive thresholding
            adaptiveThreshWinSizeMax: Maximum window size for adaptive thresholding
            adaptiveThreshWinSizeStep: Step size for window size
        """
        self.dictionary = cv2.aruco.getPredefinedDictionary(dictionary_type)
        self.parameters = cv2.aruco.DetectorParameters()

        # Configure detection parameters
        self.parameters.adaptiveThreshWinSizeMin = adaptiveThreshWinSizeMin
        self.parameters.adaptiveThreshWinSizeMax = adaptiveThreshWinSizeMax
        self.parameters.adaptiveThreshWinSizeStep = adaptiveThreshWinSizeStep
        self.parameters.minMarkerPerimeterRate = min_marker_perimeter / 1000.0

        # Create detector
        self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.parameters)

        logger.info(f"ArUco detector initialized with dictionary type {dictionary_type}")

    def detect(
        self,
        image: np.ndarray,
        camera_id: int = 0
    ) -> List[AVMarker]:
        """
        Detect ArUco markers in image

        Args:
            image: Input image (BGR or grayscale)
            camera_id: Camera identifier

        Returns:
            List of detected AVMarker objects
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Detect markers
        corners, ids, rejected = self.detector.detectMarkers(gray)

        markers = []

        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                corner_points = corners[i][0]

                # Calculate center
                center_x = np.mean(corner_points[:, 0])
                center_y = np.mean(corner_points[:, 1])

                marker = AVMarker(
                    marker_id=int(marker_id),
                    corners=corner_points,
                    center=(float(center_x), float(center_y)),
                    camera_id=camera_id,
                    timestamp=datetime.now()
                )

                markers.append(marker)

        return markers

    def draw_markers(
        self,
        image: np.ndarray,
        markers: List[AVMarker]
    ) -> np.ndarray:
        """
        Draw detected markers on image

        Args:
            image: Input image
            markers: List of markers to draw

        Returns:
            Image with drawn markers
        """
        output = image.copy()

        for marker in markers:
            # Draw marker outline
            corners = marker.corners.astype(int)
            cv2.polylines(output, [corners], True, (0, 255, 0), 2)

            # Draw marker ID
            center = tuple(marker.center)
            center_int = (int(center[0]), int(center[1]))

            cv2.circle(output, center_int, 4, (0, 0, 255), -1)

            # Add text label
            label = f"ID:{marker.marker_id}"
            cv2.putText(
                output,
                label,
                (center_int[0] - 20, center_int[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )

        return output


class AVIdentificationSystem:
    """
    Manage AV vehicle identification and track assignment
    """

    def __init__(
        self,
        marker_detector: Optional[ArUcoDetector] = None,
        iou_threshold: float = 0.3,
        max_assignment_distance: float = 100.0  # pixels
    ):
        """
        Initialize AV identification system

        Args:
            marker_detector: ArUco marker detector (creates default if None)
            iou_threshold: IoU threshold for marker-track association
            max_assignment_distance: Maximum distance for marker-track matching
        """
        self.marker_detector = marker_detector or ArUcoDetector()
        self.iou_threshold = iou_threshold
        self.max_assignment_distance = max_assignment_distance

        # AV registry
        self.av_vehicles: Dict[str, AVVehicle] = {}  # av_id -> AVVehicle
        self.marker_to_av: Dict[int, str] = {}  # marker_id -> av_id

        # Track assignment
        self.track_to_av: Dict[int, str] = {}  # track_id -> av_id

        logger.info("AV identification system initialized")

    def register_av(
        self,
        av_id: str,
        marker_ids: List[int],
        vehicle_type: str = "car",
        notes: str = ""
    ) -> AVVehicle:
        """
        Register a new AV vehicle

        Args:
            av_id: Unique AV identifier
            marker_ids: List of ArUco marker IDs on this vehicle
            vehicle_type: Type of vehicle
            notes: Additional notes

        Returns:
            Created AVVehicle object
        """
        if av_id in self.av_vehicles:
            logger.warning(f"AV {av_id} already registered")
            return self.av_vehicles[av_id]

        av = AVVehicle(
            av_id=av_id,
            marker_ids=set(marker_ids),
            vehicle_type=vehicle_type,
            notes=notes
        )

        self.av_vehicles[av_id] = av

        # Map markers to AV
        for marker_id in marker_ids:
            self.marker_to_av[marker_id] = av_id

        logger.success(f"Registered AV {av_id} with markers {marker_ids}")

        return av

    def detect_markers(
        self,
        images: List[np.ndarray],
        camera_ids: Optional[List[int]] = None
    ) -> List[List[AVMarker]]:
        """
        Detect markers in multiple camera images

        Args:
            images: List of camera images
            camera_ids: List of camera IDs (uses indices if None)

        Returns:
            List of marker lists (one per camera)
        """
        if camera_ids is None:
            camera_ids = list(range(len(images)))

        markers_per_camera = []

        for i, (image, cam_id) in enumerate(zip(images, camera_ids)):
            markers = self.marker_detector.detect(image, cam_id)
            markers_per_camera.append(markers)

        return markers_per_camera

    def assign_tracks_to_avs(
        self,
        tracks: List[Track],
        markers: List[AVMarker]
    ) -> Dict[str, int]:
        """
        Assign tracks to AV vehicles based on marker detection

        Args:
            tracks: List of object tracks
            markers: List of detected markers

        Returns:
            Dictionary mapping av_id -> track_id
        """
        assignments = {}

        # Group markers by AV
        av_markers: Dict[str, List[AVMarker]] = defaultdict(list)
        for marker in markers:
            av_id = self.marker_to_av.get(marker.marker_id)
            if av_id:
                av_markers[av_id].append(marker)

        # For each AV with detected markers
        for av_id, av_marker_list in av_markers.items():
            if not av_marker_list:
                continue

            # Calculate average marker position
            avg_x = np.mean([m.center[0] for m in av_marker_list])
            avg_y = np.mean([m.center[1] for m in av_marker_list])
            marker_center = np.array([avg_x, avg_y])

            # Find closest track
            best_track_id = None
            best_distance = float('inf')

            for track in tracks:
                # Only consider car-like objects
                if track.class_name not in ['car', 'truck', 'bus']:
                    continue

                # Calculate distance to track center
                track_center = np.array(track.get_center())
                distance = np.linalg.norm(marker_center - track_center)

                # Check if marker is inside track bounding box (with margin)
                x, y, w, h = track.bbox
                margin = 20
                if (x - margin <= avg_x <= x + w + margin and
                    y - margin <= avg_y <= y + h + margin):

                    if distance < best_distance and distance < self.max_assignment_distance:
                        best_distance = distance
                        best_track_id = track.track_id

            # Assign track to AV
            if best_track_id is not None:
                assignments[av_id] = best_track_id
                self.track_to_av[best_track_id] = av_id

                # Update AV vehicle
                av = self.av_vehicles[av_id]
                av.track_id = best_track_id
                av.last_seen = datetime.now()
                av.is_active = True

                if best_track_id not in av.track_history:
                    av.track_history.append(best_track_id)

                logger.debug(f"Assigned track {best_track_id} to AV {av_id}")

        return assignments

    def update_av_tracks(
        self,
        tracks: List[Track],
        markers_per_camera: List[List[AVMarker]]
    ) -> Dict[str, Track]:
        """
        Update AV assignments with latest tracks and markers

        Args:
            tracks: List of current tracks
            markers_per_camera: Markers detected in each camera

        Returns:
            Dictionary mapping av_id -> Track
        """
        # Combine markers from all cameras
        all_markers = []
        for markers in markers_per_camera:
            all_markers.extend(markers)

        # Assign tracks to AVs
        assignments = self.assign_tracks_to_avs(tracks, all_markers)

        # Build result dictionary
        av_tracks = {}
        for av_id, track_id in assignments.items():
            # Find track object
            for track in tracks:
                if track.track_id == track_id:
                    av_tracks[av_id] = track
                    break

        return av_tracks

    def get_av_by_track_id(self, track_id: int) -> Optional[AVVehicle]:
        """Get AV vehicle associated with track ID"""
        av_id = self.track_to_av.get(track_id)
        return self.av_vehicles.get(av_id) if av_id else None

    def get_track_id_by_av(self, av_id: str) -> Optional[int]:
        """Get track ID associated with AV"""
        av = self.av_vehicles.get(av_id)
        return av.track_id if av else None

    def is_av_track(self, track_id: int) -> bool:
        """Check if track belongs to an AV"""
        return track_id in self.track_to_av

    def get_all_av_tracks(self, tracks: List[Track]) -> List[Track]:
        """Get all tracks that belong to AVs"""
        av_track_ids = set(self.track_to_av.keys())
        return [t for t in tracks if t.track_id in av_track_ids]

    def get_statistics(self) -> Dict:
        """Get system statistics"""
        return {
            'total_avs': len(self.av_vehicles),
            'active_avs': sum(1 for av in self.av_vehicles.values() if av.is_active),
            'total_markers': len(self.marker_to_av),
            'active_assignments': len(self.track_to_av),
            'av_details': {
                av_id: {
                    'track_id': av.track_id,
                    'is_active': av.is_active,
                    'markers': list(av.marker_ids),
                    'total_frames': av.total_frames_tracked
                }
                for av_id, av in self.av_vehicles.items()
            }
        }

    def reset(self):
        """Reset track assignments (keep AV registry)"""
        self.track_to_av.clear()
        for av in self.av_vehicles.values():
            av.track_id = None
            av.is_active = False

        logger.info("AV track assignments reset")


def create_default_av_registry() -> List[Dict]:
    """
    Create default AV registry configuration

    Returns:
        List of AV configuration dictionaries
    """
    return [
        {
            'av_id': 'AV001',
            'marker_ids': [0, 1],  # ArUco markers 0 and 1
            'vehicle_type': 'car',
            'notes': 'Primary test vehicle'
        },
        {
            'av_id': 'AV002',
            'marker_ids': [2, 3],
            'vehicle_type': 'car',
            'notes': 'Secondary test vehicle'
        },
        {
            'av_id': 'AV003',
            'marker_ids': [4, 5],
            'vehicle_type': 'truck',
            'notes': 'Heavy vehicle test'
        }
    ]
