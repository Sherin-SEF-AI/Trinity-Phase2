"""
Trinity Phase 2 - Detection & Tracking Visualization
Utilities for drawing detections, tracks, and trajectories
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict
from loguru import logger

from trinity.detection.detector import Detection
from trinity.detection.tracker import Track


class DetectionVisualizer:
    """
    Visualizer for detections and tracks
    """

    # Color palette for different classes (RGB)
    CLASS_COLORS = {
        'person': (255, 100, 100),
        'bicycle': (100, 255, 100),
        'car': (100, 100, 255),
        'motorcycle': (255, 255, 100),
        'bus': (255, 100, 255),
        'truck': (100, 255, 255),
        'traffic_light': (255, 165, 0),
        'stop_sign': (255, 0, 0),
    }

    DEFAULT_COLOR = (0, 255, 0)

    def __init__(
        self,
        show_labels: bool = True,
        show_confidence: bool = True,
        show_track_ids: bool = True,
        show_trajectories: bool = True,
        show_predictions: bool = False,
        box_thickness: int = 2,
        text_scale: float = 0.5,
        trajectory_length: int = 50
    ):
        """
        Initialize visualizer

        Args:
            show_labels: Show class labels
            show_confidence: Show confidence scores
            show_track_ids: Show track IDs
            show_trajectories: Draw object trajectories
            show_predictions: Draw predicted positions
            box_thickness: Bounding box line thickness
            text_scale: Text scale
            trajectory_length: Maximum trajectory points to show
        """
        self.show_labels = show_labels
        self.show_confidence = show_confidence
        self.show_track_ids = show_track_ids
        self.show_trajectories = show_trajectories
        self.show_predictions = show_predictions
        self.box_thickness = box_thickness
        self.text_scale = text_scale
        self.trajectory_length = trajectory_length

    def draw_detections(
        self,
        image: np.ndarray,
        detections: List[Detection]
    ) -> np.ndarray:
        """
        Draw detections on image

        Args:
            image: Input image (BGR)
            detections: List of detections

        Returns:
            Image with drawn detections
        """
        output = image.copy()

        for det in detections:
            color = self._get_color_for_class(det.class_name)
            output = self._draw_detection_box(output, det, color)

        return output

    def draw_tracks(
        self,
        image: np.ndarray,
        tracks: List[Track]
    ) -> np.ndarray:
        """
        Draw tracks on image

        Args:
            image: Input image (BGR)
            tracks: List of tracks

        Returns:
            Image with drawn tracks
        """
        output = image.copy()

        # Draw trajectories first (behind boxes)
        if self.show_trajectories:
            for track in tracks:
                output = self._draw_trajectory(output, track)

        # Draw bounding boxes and labels
        for track in tracks:
            color = self._get_color_for_class(track.class_name)
            output = self._draw_track_box(output, track, color)

        # Draw predictions
        if self.show_predictions:
            for track in tracks:
                output = self._draw_prediction(output, track)

        return output

    def _draw_detection_box(
        self,
        image: np.ndarray,
        detection: Detection,
        color: Tuple[int, int, int]
    ) -> np.ndarray:
        """Draw a single detection bounding box"""
        x, y, w, h = detection.bbox
        x1, y1 = int(x), int(y)
        x2, y2 = int(x + w), int(y + h)

        # Draw box
        cv2.rectangle(image, (x1, y1), (x2, y2), color, self.box_thickness)

        # Draw label
        label_parts = []
        if self.show_labels:
            label_parts.append(detection.class_name)
        if self.show_confidence:
            label_parts.append(f"{detection.confidence:.2f}")

        if label_parts:
            label = " ".join(label_parts)
            image = self._draw_label(image, label, (x1, y1), color)

        return image

    def _draw_track_box(
        self,
        image: np.ndarray,
        track: Track,
        color: Tuple[int, int, int]
    ) -> np.ndarray:
        """Draw a single track bounding box"""
        x, y, w, h = track.bbox
        x1, y1 = int(x), int(y)
        x2, y2 = int(x + w), int(y + h)

        # Draw box (thicker for confirmed tracks)
        thickness = self.box_thickness if track.is_confirmed else self.box_thickness - 1
        cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)

        # Draw label with track ID
        label_parts = []
        if self.show_track_ids:
            label_parts.append(f"ID:{track.track_id}")
        if self.show_labels:
            label_parts.append(track.class_name)
        if self.show_confidence:
            label_parts.append(f"{track.confidence:.2f}")

        if label_parts:
            label = " ".join(label_parts)
            image = self._draw_label(image, label, (x1, y1), color)

        # Draw speed indicator
        if track.speed > 0:
            speed_text = f"{track.speed:.1f}px/f"
            cv2.putText(
                image,
                speed_text,
                (x1, y2 + 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                self.text_scale * 0.8,
                color,
                1
            )

        return image

    def _draw_trajectory(
        self,
        image: np.ndarray,
        track: Track
    ) -> np.ndarray:
        """Draw object trajectory"""
        points = track.get_trajectory_points(self.trajectory_length)

        if len(points) < 2:
            return image

        color = self._get_color_for_class(track.class_name)

        # Draw lines connecting trajectory points
        for i in range(len(points) - 1):
            pt1 = (int(points[i][0]), int(points[i][1]))
            pt2 = (int(points[i+1][0]), int(points[i+1][1]))

            # Fade older points
            alpha = (i + 1) / len(points)
            faded_color = tuple(int(c * alpha) for c in color)

            cv2.line(image, pt1, pt2, faded_color, 2)

        return image

    def _draw_prediction(
        self,
        image: np.ndarray,
        track: Track
    ) -> np.ndarray:
        """Draw predicted future position"""
        current_center = track.get_center()
        predicted_pos = track.get_predicted_position(steps_ahead=10)

        color = self._get_color_for_class(track.class_name)

        # Draw line to predicted position
        pt1 = (int(current_center[0]), int(current_center[1]))
        pt2 = (int(predicted_pos[0]), int(predicted_pos[1]))

        cv2.arrowedLine(image, pt1, pt2, color, 2, tipLength=0.3)

        # Draw predicted box
        x, y, w, h = track.bbox
        pred_x = predicted_pos[0] - w/2
        pred_y = predicted_pos[1] - h/2

        cv2.rectangle(
            image,
            (int(pred_x), int(pred_y)),
            (int(pred_x + w), int(pred_y + h)),
            color,
            1,
            cv2.LINE_AA
        )

        return image

    def _draw_label(
        self,
        image: np.ndarray,
        label: str,
        position: Tuple[int, int],
        color: Tuple[int, int, int]
    ) -> np.ndarray:
        """Draw text label with background"""
        x, y = position

        # Get label size
        (label_w, label_h), baseline = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            self.text_scale,
            1
        )

        # Draw background rectangle
        cv2.rectangle(
            image,
            (x, y - label_h - baseline - 5),
            (x + label_w + 5, y),
            color,
            -1
        )

        # Draw text
        cv2.putText(
            image,
            label,
            (x + 2, y - baseline - 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            self.text_scale,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )

        return image

    def _get_color_for_class(self, class_name: str) -> Tuple[int, int, int]:
        """Get color for object class"""
        return self.CLASS_COLORS.get(class_name, self.DEFAULT_COLOR)

    def draw_info_overlay(
        self,
        image: np.ndarray,
        info: Dict[str, any]
    ) -> np.ndarray:
        """
        Draw information overlay on image

        Args:
            image: Input image
            info: Dictionary of info to display

        Returns:
            Image with info overlay
        """
        output = image.copy()
        h, w = output.shape[:2]

        # Draw semi-transparent background
        overlay = output.copy()
        cv2.rectangle(overlay, (10, 10), (300, 150), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, output, 0.3, 0, output)

        # Draw info text
        y_offset = 30
        for key, value in info.items():
            text = f"{key}: {value}"
            cv2.putText(
                output,
                text,
                (20, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )
            y_offset += 25

        return output

    def create_bird_eye_view(
        self,
        tracks: List[Track],
        world_size: Tuple[float, float] = (50.0, 50.0),  # meters
        image_size: Tuple[int, int] = (500, 500),  # pixels
        show_ids: bool = True
    ) -> np.ndarray:
        """
        Create bird's eye view visualization

        Args:
            tracks: List of tracks
            world_size: World dimensions in meters (width, height)
            image_size: Output image size in pixels
            show_ids: Show track IDs

        Returns:
            Bird's eye view image
        """
        bev_image = np.zeros((image_size[1], image_size[0], 3), dtype=np.uint8)

        # Draw grid
        bev_image = self._draw_grid(bev_image, world_size, image_size)

        # Scale factors
        scale_x = image_size[0] / world_size[0]
        scale_y = image_size[1] / world_size[1]

        # Draw tracks (assuming tracks have world coordinates)
        for track in tracks:
            if hasattr(track, 'world_position') and track.world_position is not None:
                wx, wy = track.world_position[:2]

                # Convert to image coordinates (flip Y for correct orientation)
                ix = int((wx + world_size[0]/2) * scale_x)
                iy = int((world_size[1]/2 - wy) * scale_y)

                color = self._get_color_for_class(track.class_name)

                # Draw circle for object
                cv2.circle(bev_image, (ix, iy), 5, color, -1)

                # Draw trajectory
                if hasattr(track, 'world_trajectory') and track.world_trajectory:
                    for i in range(len(track.world_trajectory) - 1):
                        pt1 = track.world_trajectory[i]
                        pt2 = track.world_trajectory[i+1]

                        ix1 = int((pt1[0] + world_size[0]/2) * scale_x)
                        iy1 = int((world_size[1]/2 - pt1[1]) * scale_y)
                        ix2 = int((pt2[0] + world_size[0]/2) * scale_x)
                        iy2 = int((world_size[1]/2 - pt2[1]) * scale_y)

                        cv2.line(bev_image, (ix1, iy1), (ix2, iy2), color, 1)

                # Draw ID
                if show_ids:
                    cv2.putText(
                        bev_image,
                        str(track.track_id),
                        (ix + 8, iy),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.4,
                        (255, 255, 255),
                        1
                    )

        return bev_image

    def _draw_grid(
        self,
        image: np.ndarray,
        world_size: Tuple[float, float],
        image_size: Tuple[int, int]
    ) -> np.ndarray:
        """Draw grid on bird's eye view"""
        grid_color = (50, 50, 50)

        # Draw vertical lines
        for i in range(0, image_size[0], image_size[0] // 10):
            cv2.line(image, (i, 0), (i, image_size[1]), grid_color, 1)

        # Draw horizontal lines
        for i in range(0, image_size[1], image_size[1] // 10):
            cv2.line(image, (0, i), (image_size[0], i), grid_color, 1)

        # Draw center lines (thicker)
        cv2.line(
            image,
            (image_size[0]//2, 0),
            (image_size[0]//2, image_size[1]),
            (100, 100, 100),
            2
        )
        cv2.line(
            image,
            (0, image_size[1]//2),
            (image_size[0], image_size[1]//2),
            (100, 100, 100),
            2
        )

        return image


def create_multi_view_visualization(
    images: List[np.ndarray],
    titles: Optional[List[str]] = None,
    grid_size: Optional[Tuple[int, int]] = None
) -> np.ndarray:
    """
    Create grid visualization of multiple camera views

    Args:
        images: List of images
        titles: Optional titles for each view
        grid_size: Grid layout (rows, cols). Auto-calculated if None.

    Returns:
        Combined grid image
    """
    if not images:
        return np.zeros((480, 640, 3), dtype=np.uint8)

    # Determine grid size
    if grid_size is None:
        n = len(images)
        cols = int(np.ceil(np.sqrt(n)))
        rows = int(np.ceil(n / cols))
        grid_size = (rows, cols)

    rows, cols = grid_size

    # Get max dimensions
    max_h = max(img.shape[0] for img in images)
    max_w = max(img.shape[1] for img in images)

    # Resize all images to same size
    resized = []
    for img in images:
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        resized.append(cv2.resize(img, (max_w, max_h)))

    # Add titles if provided
    if titles:
        for i, (img, title) in enumerate(zip(resized, titles)):
            cv2.putText(
                img,
                title,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

    # Pad with black images if needed
    while len(resized) < rows * cols:
        resized.append(np.zeros((max_h, max_w, 3), dtype=np.uint8))

    # Create grid
    grid_rows = []
    for r in range(rows):
        row_images = resized[r*cols:(r+1)*cols]
        grid_rows.append(np.hstack(row_images))

    grid_image = np.vstack(grid_rows)

    return grid_image
