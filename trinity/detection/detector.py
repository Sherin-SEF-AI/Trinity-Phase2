"""
Trinity Phase 2 - Object Detector
YOLOv8/v10 integration for real-time object detection
"""

import cv2
import numpy as np
import torch
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    logger.warning("Ultralytics YOLO not available. Install with: pip install ultralytics")
    YOLO_AVAILABLE = False


@dataclass
class Detection:
    """Single object detection"""
    bbox: Tuple[float, float, float, float]  # x, y, w, h
    confidence: float
    class_id: int
    class_name: str

    def get_center(self) -> Tuple[float, float]:
        """Get bounding box center point"""
        x, y, w, h = self.bbox
        return (x + w/2, y + h/2)

    def get_corners(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Get bounding box corners (top-left, bottom-right)"""
        x, y, w, h = self.bbox
        return ((x, y), (x + w, y + h))

    def get_area(self) -> float:
        """Get bounding box area"""
        _, _, w, h = self.bbox
        return w * h


@dataclass
class DetectionResult:
    """Detection results for a single frame"""
    frame_number: int
    timestamp: float
    detections: List[Detection]
    inference_time_ms: float
    image_size: Tuple[int, int]  # width, height

    def filter_by_class(self, class_names: List[str]) -> 'DetectionResult':
        """Filter detections by class name"""
        filtered = [d for d in self.detections if d.class_name in class_names]
        return DetectionResult(
            frame_number=self.frame_number,
            timestamp=self.timestamp,
            detections=filtered,
            inference_time_ms=self.inference_time_ms,
            image_size=self.image_size
        )

    def filter_by_confidence(self, min_confidence: float) -> 'DetectionResult':
        """Filter detections by minimum confidence"""
        filtered = [d for d in self.detections if d.confidence >= min_confidence]
        return DetectionResult(
            frame_number=self.frame_number,
            timestamp=self.timestamp,
            detections=filtered,
            inference_time_ms=self.inference_time_ms,
            image_size=self.image_size
        )


class ObjectDetector:
    """
    YOLOv8/v10 object detector with GPU acceleration
    """

    # COCO class names
    COCO_CLASSES = [
        'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
        'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
        'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
        'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
        'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
        'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
        'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
        'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
        'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
        'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
        'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier',
        'toothbrush'
    ]

    def __init__(
        self,
        model_name: str = 'yolov8x.pt',
        model_path: Optional[str] = None,
        device: str = 'auto',
        confidence_threshold: float = 0.5,
        nms_threshold: float = 0.4,
        enabled_classes: Optional[List[str]] = None
    ):
        """
        Initialize object detector

        Args:
            model_name: Model name (yolov8n, yolov8s, yolov8m, yolov8l, yolov8x, yolov10x)
            model_path: Path to custom model weights
            device: 'auto', 'cuda', 'cpu', or 'mps'
            confidence_threshold: Minimum confidence for detection
            nms_threshold: Non-maximum suppression threshold
            enabled_classes: List of class names to detect (None = all)
        """
        if not YOLO_AVAILABLE:
            raise RuntimeError("Ultralytics YOLO not installed")

        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.enabled_classes = enabled_classes

        # Determine device
        if device == 'auto':
            if torch.cuda.is_available():
                self.device = 'cuda'
            elif torch.backends.mps.is_available():
                self.device = 'mps'
            else:
                self.device = 'cpu'
        else:
            self.device = device

        # Load model
        if model_path and Path(model_path).exists():
            logger.info(f"Loading custom model from: {model_path}")
            self.model = YOLO(model_path)
        else:
            logger.info(f"Loading pretrained model: {model_name}")
            self.model = YOLO(model_name)

        # Move to device
        self.model.to(self.device)

        # Get class names from model
        self.class_names = self.model.names

        # Create enabled class indices
        if self.enabled_classes:
            self.enabled_class_ids = [
                i for i, name in self.class_names.items()
                if name in self.enabled_classes
            ]
        else:
            self.enabled_class_ids = None

        # Statistics
        self.total_detections = 0
        self.total_inferences = 0
        self.avg_inference_time = 0.0

        logger.success(
            f"Object detector initialized: {model_name} on {self.device.upper()}"
        )

    def detect(
        self,
        image: np.ndarray,
        conf_threshold: Optional[float] = None,
        nms_threshold: Optional[float] = None
    ) -> DetectionResult:
        """
        Detect objects in a single image

        Args:
            image: Input image (BGR format)
            conf_threshold: Override confidence threshold
            nms_threshold: Override NMS threshold

        Returns:
            DetectionResult object
        """
        import time

        conf = conf_threshold if conf_threshold is not None else self.confidence_threshold
        nms = nms_threshold if nms_threshold is not None else self.nms_threshold

        # Run inference
        start_time = time.time()

        results = self.model.predict(
            image,
            conf=conf,
            iou=nms,
            device=self.device,
            verbose=False,
            half=True if self.device == 'cuda' else False  # FP16 for GPU
        )

        inference_time = (time.time() - start_time) * 1000  # ms

        # Parse results
        detections = []

        if len(results) > 0:
            result = results[0]  # First image (batch size = 1)
            boxes = result.boxes

            if boxes is not None:
                for i in range(len(boxes)):
                    # Get box coordinates (xyxy format)
                    xyxy = boxes.xyxy[i].cpu().numpy()
                    x1, y1, x2, y2 = xyxy

                    # Convert to xywh
                    x, y, w, h = x1, y1, x2 - x1, y2 - y1

                    # Get class and confidence
                    class_id = int(boxes.cls[i])
                    confidence = float(boxes.conf[i])
                    class_name = self.class_names.get(class_id, f'class_{class_id}')

                    # Filter by enabled classes
                    if self.enabled_class_ids and class_id not in self.enabled_class_ids:
                        continue

                    detection = Detection(
                        bbox=(float(x), float(y), float(w), float(h)),
                        confidence=confidence,
                        class_id=class_id,
                        class_name=class_name
                    )

                    detections.append(detection)

        # Update statistics
        self.total_detections += len(detections)
        self.total_inferences += 1
        self.avg_inference_time = (
            (self.avg_inference_time * (self.total_inferences - 1) + inference_time) /
            self.total_inferences
        )

        return DetectionResult(
            frame_number=0,  # Will be set by caller
            timestamp=time.time(),
            detections=detections,
            inference_time_ms=inference_time,
            image_size=(image.shape[1], image.shape[0])
        )

    def detect_batch(
        self,
        images: List[np.ndarray],
        conf_threshold: Optional[float] = None,
        nms_threshold: Optional[float] = None
    ) -> List[DetectionResult]:
        """
        Detect objects in a batch of images

        Args:
            images: List of input images (BGR format)
            conf_threshold: Override confidence threshold
            nms_threshold: Override NMS threshold

        Returns:
            List of DetectionResult objects
        """
        import time

        conf = conf_threshold if conf_threshold is not None else self.confidence_threshold
        nms = nms_threshold if nms_threshold is not None else self.nms_threshold

        # Run batch inference
        start_time = time.time()

        results = self.model.predict(
            images,
            conf=conf,
            iou=nms,
            device=self.device,
            verbose=False,
            half=True if self.device == 'cuda' else False
        )

        total_time = (time.time() - start_time) * 1000  # ms
        avg_time_per_image = total_time / len(images)

        # Parse results for each image
        detection_results = []

        for idx, result in enumerate(results):
            detections = []
            boxes = result.boxes

            if boxes is not None:
                for i in range(len(boxes)):
                    xyxy = boxes.xyxy[i].cpu().numpy()
                    x1, y1, x2, y2 = xyxy
                    x, y, w, h = x1, y1, x2 - x1, y2 - y1

                    class_id = int(boxes.cls[i])
                    confidence = float(boxes.conf[i])
                    class_name = self.class_names.get(class_id, f'class_{class_id}')

                    if self.enabled_class_ids and class_id not in self.enabled_class_ids:
                        continue

                    detection = Detection(
                        bbox=(float(x), float(y), float(w), float(h)),
                        confidence=confidence,
                        class_id=class_id,
                        class_name=class_name
                    )

                    detections.append(detection)

            self.total_detections += len(detections)

            detection_results.append(DetectionResult(
                frame_number=idx,
                timestamp=time.time(),
                detections=detections,
                inference_time_ms=avg_time_per_image,
                image_size=(images[idx].shape[1], images[idx].shape[0])
            ))

        self.total_inferences += len(images)

        return detection_results

    def draw_detections(
        self,
        image: np.ndarray,
        detections: List[Detection],
        show_labels: bool = True,
        show_confidence: bool = True,
        thickness: int = 2
    ) -> np.ndarray:
        """
        Draw bounding boxes on image

        Args:
            image: Input image
            detections: List of detections
            show_labels: Show class labels
            show_confidence: Show confidence scores
            thickness: Box thickness

        Returns:
            Image with drawn detections
        """
        output = image.copy()

        # Color map for different classes
        np.random.seed(42)
        colors = {
            class_id: tuple(map(int, np.random.randint(0, 255, 3)))
            for class_id in range(len(self.class_names))
        }

        for det in detections:
            x, y, w, h = det.bbox
            x1, y1 = int(x), int(y)
            x2, y2 = int(x + w), int(y + h)

            # Get color for this class
            color = colors.get(det.class_id, (0, 255, 0))

            # Draw bounding box
            cv2.rectangle(output, (x1, y1), (x2, y2), color, thickness)

            # Draw label
            if show_labels or show_confidence:
                label_parts = []
                if show_labels:
                    label_parts.append(det.class_name)
                if show_confidence:
                    label_parts.append(f"{det.confidence:.2f}")

                label = " ".join(label_parts)

                # Get label size
                (label_w, label_h), baseline = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
                )

                # Draw label background
                cv2.rectangle(
                    output,
                    (x1, y1 - label_h - baseline - 5),
                    (x1 + label_w, y1),
                    color,
                    -1
                )

                # Draw label text
                cv2.putText(
                    output,
                    label,
                    (x1, y1 - baseline - 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1
                )

        return output

    def get_statistics(self) -> Dict[str, Any]:
        """Get detector statistics"""
        return {
            'model': self.model_name,
            'device': self.device,
            'total_inferences': self.total_inferences,
            'total_detections': self.total_detections,
            'avg_inference_time_ms': self.avg_inference_time,
            'avg_detections_per_frame': (
                self.total_detections / self.total_inferences
                if self.total_inferences > 0 else 0
            ),
            'enabled_classes': self.enabled_classes,
            'confidence_threshold': self.confidence_threshold,
            'nms_threshold': self.nms_threshold
        }

    def reset_statistics(self):
        """Reset statistics counters"""
        self.total_detections = 0
        self.total_inferences = 0
        self.avg_inference_time = 0.0


def create_detector_from_config(config: Dict) -> ObjectDetector:
    """
    Create detector from configuration dictionary

    Args:
        config: Configuration dictionary

    Returns:
        ObjectDetector instance
    """
    detection_config = config.get('detection', {})

    return ObjectDetector(
        model_name=detection_config.get('model', 'yolov8x'),
        model_path=detection_config.get('model_path'),
        device=detection_config.get('device', 'auto'),
        confidence_threshold=detection_config.get('confidence_threshold', 0.5),
        nms_threshold=detection_config.get('nms_threshold', 0.4),
        enabled_classes=detection_config.get('enabled_classes')
    )
