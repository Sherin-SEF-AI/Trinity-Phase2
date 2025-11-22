"""
Trinity Phase 4 - Perception Validation Module
Ground truth comparison and accuracy metrics for detection and tracking validation
"""

import numpy as np
from typing import List, Optional, Dict, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path
import json
from loguru import logger

from trinity.detection.tracker import Track


@dataclass
class GroundTruthObject:
    """Ground truth object annotation"""
    object_id: int
    frame_number: int
    class_name: str
    bbox: Tuple[float, float, float, float]  # x, y, w, h
    confidence: float = 1.0
    position_3d: Optional[Tuple[float, float, float]] = None
    velocity: Optional[Tuple[float, float]] = None
    occlusion_level: int = 0  # 0=fully visible, 1=partially, 2=largely, 3=unknown
    truncation: float = 0.0  # 0.0-1.0
    attributes: Dict = field(default_factory=dict)


@dataclass
class DetectionMatch:
    """Matched detection and ground truth"""
    gt_object: GroundTruthObject
    detected_track: Optional[Track]
    iou: float
    distance_2d: float = 0.0
    distance_3d: Optional[float] = None
    is_match: bool = False
    is_false_positive: bool = False
    is_false_negative: bool = False


@dataclass
class DetectionMetrics:
    """Detection performance metrics"""
    # Per-class metrics
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    # Aggregate metrics
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    average_precision: float = 0.0  # AP

    # IoU statistics
    mean_iou: float = 0.0
    median_iou: float = 0.0

    # Confidence statistics
    mean_confidence: float = 0.0

    # Position errors
    mean_position_error: Optional[float] = None
    median_position_error: Optional[float] = None


@dataclass
class TrackingMetrics:
    """Tracking performance metrics (CLEAR MOT)"""
    # Frame-based counts
    total_frames: int = 0
    total_gt_objects: int = 0
    total_detections: int = 0

    # Match statistics
    matches: int = 0  # True positives
    false_positives: int = 0  # FP
    false_negatives: int = 0  # Misses (FN)
    id_switches: int = 0  # IDSW
    fragmentations: int = 0  # Fragmentation count

    # Mostly tracked/lost
    mostly_tracked: int = 0  # MT: tracked ≥80% of lifespan
    mostly_lost: int = 0  # ML: tracked ≤20% of lifespan
    partially_tracked: int = 0  # PT: neither MT nor ML

    # CLEAR MOT metrics
    mota: float = 0.0  # Multi-Object Tracking Accuracy
    motp: float = 0.0  # Multi-Object Tracking Precision
    moda: float = 0.0  # Multi-Object Detection Accuracy (without ID switches)

    # Additional metrics
    precision: float = 0.0
    recall: float = 0.0


@dataclass
class ConfusionMatrix:
    """Confusion matrix for classification"""
    classes: List[str]
    matrix: np.ndarray  # Shape: (n_classes, n_classes)

    def get_class_accuracy(self, class_name: str) -> float:
        """Get accuracy for specific class"""
        if class_name not in self.classes:
            return 0.0

        idx = self.classes.index(class_name)
        total = np.sum(self.matrix[idx, :])
        correct = self.matrix[idx, idx]

        return correct / total if total > 0 else 0.0

    def get_overall_accuracy(self) -> float:
        """Get overall classification accuracy"""
        total = np.sum(self.matrix)
        correct = np.trace(self.matrix)
        return correct / total if total > 0 else 0.0


class GroundTruthLoader:
    """Load ground truth annotations from various formats"""

    @staticmethod
    def load_coco_format(annotation_file: Path) -> Dict[int, List[GroundTruthObject]]:
        """
        Load COCO format annotations

        Args:
            annotation_file: Path to COCO JSON file

        Returns:
            Dictionary mapping frame_number -> list of GroundTruthObjects
        """
        with open(annotation_file, 'r') as f:
            data = json.load(f)

        # Build category mapping
        categories = {cat['id']: cat['name'] for cat in data['categories']}

        # Build image ID to frame number mapping
        images = {img['id']: img for img in data['images']}

        # Group annotations by frame
        annotations_by_frame = defaultdict(list)

        for ann in data['annotations']:
            image_id = ann['image_id']
            if image_id not in images:
                continue

            # Extract frame number from image filename or use image_id
            image_info = images[image_id]
            frame_number = image_info.get('frame_id', image_id)

            # Create ground truth object
            bbox = ann['bbox']  # [x, y, width, height]

            gt_obj = GroundTruthObject(
                object_id=ann['id'],
                frame_number=frame_number,
                class_name=categories.get(ann['category_id'], 'unknown'),
                bbox=(bbox[0], bbox[1], bbox[2], bbox[3]),
                confidence=1.0,
                attributes={
                    'area': ann.get('area', 0),
                    'iscrowd': ann.get('iscrowd', 0)
                }
            )

            annotations_by_frame[frame_number].append(gt_obj)

        logger.info(f"Loaded {len(data['annotations'])} annotations from COCO format")
        return dict(annotations_by_frame)

    @staticmethod
    def load_kitti_format(label_dir: Path) -> Dict[int, List[GroundTruthObject]]:
        """
        Load KITTI format annotations

        Args:
            label_dir: Directory containing KITTI label files (one per frame)

        Returns:
            Dictionary mapping frame_number -> list of GroundTruthObjects
        """
        annotations_by_frame = {}

        for label_file in sorted(label_dir.glob('*.txt')):
            # Extract frame number from filename
            frame_number = int(label_file.stem)

            objects = []

            with open(label_file, 'r') as f:
                for line_num, line in enumerate(f):
                    parts = line.strip().split()

                    if len(parts) < 15:
                        continue

                    # KITTI format:
                    # type truncated occluded alpha bbox_left bbox_top bbox_right bbox_bottom
                    # dimensions_h dimensions_w dimensions_l location_x location_y location_z rotation_y
                    class_name = parts[0].lower()
                    truncation = float(parts[1])
                    occlusion = int(parts[2])

                    # 2D bounding box
                    bbox_left = float(parts[4])
                    bbox_top = float(parts[5])
                    bbox_right = float(parts[6])
                    bbox_bottom = float(parts[7])

                    bbox_w = bbox_right - bbox_left
                    bbox_h = bbox_bottom - bbox_top

                    # 3D position (if available)
                    if len(parts) >= 14:
                        loc_x = float(parts[11])
                        loc_y = float(parts[12])
                        loc_z = float(parts[13])
                        position_3d = (loc_x, loc_y, loc_z)
                    else:
                        position_3d = None

                    gt_obj = GroundTruthObject(
                        object_id=line_num,
                        frame_number=frame_number,
                        class_name=class_name,
                        bbox=(bbox_left, bbox_top, bbox_w, bbox_h),
                        confidence=1.0,
                        position_3d=position_3d,
                        occlusion_level=occlusion,
                        truncation=truncation
                    )

                    objects.append(gt_obj)

            annotations_by_frame[frame_number] = objects

        logger.info(f"Loaded {len(annotations_by_frame)} frames from KITTI format")
        return annotations_by_frame


class PerceptionValidator:
    """
    Validate detection and tracking performance against ground truth
    """

    def __init__(
        self,
        iou_threshold: float = 0.5,
        distance_threshold: float = 2.0,  # meters
        class_mapping: Optional[Dict[str, str]] = None
    ):
        """
        Initialize perception validator

        Args:
            iou_threshold: IoU threshold for detection matching
            distance_threshold: Distance threshold for 3D matching (meters)
            class_mapping: Optional mapping from GT classes to detection classes
        """
        self.iou_threshold = iou_threshold
        self.distance_threshold = distance_threshold
        self.class_mapping = class_mapping or {}

        # Statistics storage
        self.matches_by_frame: Dict[int, List[DetectionMatch]] = {}
        self.track_associations: Dict[int, Dict[int, int]] = {}  # frame -> {gt_id: track_id}

        logger.info("Perception validator initialized")

    def calculate_iou(
        self,
        bbox1: Tuple[float, float, float, float],
        bbox2: Tuple[float, float, float, float]
    ) -> float:
        """Calculate IoU between two bounding boxes"""
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2

        # Calculate intersection
        x_left = max(x1, x2)
        y_top = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_bottom = min(y1 + h1, y2 + h2)

        if x_right < x_left or y_bottom < y_top:
            return 0.0

        intersection_area = (x_right - x_left) * (y_bottom - y_top)

        # Calculate union
        bbox1_area = w1 * h1
        bbox2_area = w2 * h2
        union_area = bbox1_area + bbox2_area - intersection_area

        return intersection_area / union_area if union_area > 0 else 0.0

    def match_detections(
        self,
        ground_truth: List[GroundTruthObject],
        detections: List[Track],
        frame_number: int
    ) -> List[DetectionMatch]:
        """
        Match detections to ground truth objects

        Args:
            ground_truth: List of ground truth objects
            detections: List of detected tracks
            frame_number: Current frame number

        Returns:
            List of DetectionMatch objects
        """
        matches = []

        # Create IoU matrix
        n_gt = len(ground_truth)
        n_det = len(detections)

        iou_matrix = np.zeros((n_gt, n_det))

        for i, gt in enumerate(ground_truth):
            for j, det in enumerate(detections):
                # Map class names if needed
                gt_class = self.class_mapping.get(gt.class_name, gt.class_name)

                # Check if classes match
                if gt_class != det.class_name:
                    continue

                # Calculate IoU
                det_bbox = det.bbox  # Should be (x, y, w, h)
                iou = self.calculate_iou(gt.bbox, det_bbox)
                iou_matrix[i, j] = iou

        # Hungarian matching (greedy approximation)
        matched_gt = set()
        matched_det = set()

        # Sort by IoU (descending)
        matches_sorted = []
        for i in range(n_gt):
            for j in range(n_det):
                if iou_matrix[i, j] >= self.iou_threshold:
                    matches_sorted.append((i, j, iou_matrix[i, j]))

        matches_sorted.sort(key=lambda x: x[2], reverse=True)

        # Greedy matching
        for i, j, iou in matches_sorted:
            if i not in matched_gt and j not in matched_det:
                # Calculate 2D distance
                gt_center = (
                    gt.bbox[0] + gt.bbox[2] / 2,
                    gt.bbox[1] + gt.bbox[3] / 2
                )
                det_center = detections[j].get_center()
                distance_2d = np.linalg.norm(np.array(gt_center) - np.array(det_center))

                # Calculate 3D distance if available
                distance_3d = None
                gt = ground_truth[i]
                det = detections[j]

                if gt.position_3d and hasattr(det, 'world_position') and det.world_position:
                    gt_pos = np.array(gt.position_3d)
                    det_pos = np.array(det.world_position)
                    distance_3d = np.linalg.norm(gt_pos - det_pos)

                match = DetectionMatch(
                    gt_object=gt,
                    detected_track=det,
                    iou=iou,
                    distance_2d=distance_2d,
                    distance_3d=distance_3d,
                    is_match=True
                )

                matches.append(match)
                matched_gt.add(i)
                matched_det.add(j)

        # False negatives (missed detections)
        for i in range(n_gt):
            if i not in matched_gt:
                match = DetectionMatch(
                    gt_object=ground_truth[i],
                    detected_track=None,
                    iou=0.0,
                    is_false_negative=True
                )
                matches.append(match)

        # False positives (spurious detections)
        for j in range(n_det):
            if j not in matched_det:
                # Create a dummy GT object for FP
                det = detections[j]
                dummy_gt = GroundTruthObject(
                    object_id=-1,
                    frame_number=frame_number,
                    class_name=det.class_name,
                    bbox=det.bbox,
                    confidence=0.0
                )

                match = DetectionMatch(
                    gt_object=dummy_gt,
                    detected_track=det,
                    iou=0.0,
                    is_false_positive=True
                )
                matches.append(match)

        # Store matches
        self.matches_by_frame[frame_number] = matches

        return matches

    def calculate_detection_metrics(
        self,
        class_filter: Optional[str] = None
    ) -> DetectionMetrics:
        """
        Calculate detection performance metrics

        Args:
            class_filter: Optional class name to filter metrics

        Returns:
            DetectionMetrics object
        """
        tp = 0
        fp = 0
        fn = 0

        ious = []
        confidences = []
        position_errors = []

        for frame_num, matches in self.matches_by_frame.items():
            for match in matches:
                # Filter by class if specified
                if class_filter and match.gt_object.class_name != class_filter:
                    continue

                if match.is_match:
                    tp += 1
                    ious.append(match.iou)
                    if match.detected_track:
                        confidences.append(match.detected_track.confidence)

                    if match.distance_3d is not None:
                        position_errors.append(match.distance_3d)

                elif match.is_false_positive:
                    fp += 1
                    if match.detected_track:
                        confidences.append(match.detected_track.confidence)

                elif match.is_false_negative:
                    fn += 1

        # Calculate metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        mean_iou = np.mean(ious) if ious else 0.0
        median_iou = np.median(ious) if ious else 0.0
        mean_confidence = np.mean(confidences) if confidences else 0.0

        mean_pos_error = np.mean(position_errors) if position_errors else None
        median_pos_error = np.median(position_errors) if position_errors else None

        return DetectionMetrics(
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1_score=f1,
            mean_iou=mean_iou,
            median_iou=median_iou,
            mean_confidence=mean_confidence,
            mean_position_error=mean_pos_error,
            median_position_error=median_pos_error
        )

    def calculate_tracking_metrics(
        self,
        ground_truth_by_frame: Dict[int, List[GroundTruthObject]],
        class_filter: Optional[str] = None
    ) -> TrackingMetrics:
        """
        Calculate tracking performance metrics (CLEAR MOT)

        Args:
            ground_truth_by_frame: Ground truth annotations by frame
            class_filter: Optional class name to filter

        Returns:
            TrackingMetrics object
        """
        total_frames = 0
        total_gt = 0
        total_det = 0

        matches_count = 0
        fp_count = 0
        fn_count = 0

        # Track ID associations: gt_id -> list of (frame, track_id)
        gt_track_associations: Dict[int, List[Tuple[int, int]]] = defaultdict(list)

        # Process each frame
        for frame_num in sorted(self.matches_by_frame.keys()):
            matches = self.matches_by_frame[frame_num]

            total_frames += 1

            frame_gt_count = 0
            frame_det_count = 0
            frame_matches = 0
            frame_fp = 0
            frame_fn = 0

            for match in matches:
                # Filter by class
                if class_filter and match.gt_object.class_name != class_filter:
                    continue

                if match.is_match:
                    frame_matches += 1
                    frame_gt_count += 1
                    frame_det_count += 1

                    # Record track association
                    gt_id = match.gt_object.object_id
                    track_id = match.detected_track.track_id if match.detected_track else -1
                    gt_track_associations[gt_id].append((frame_num, track_id))

                elif match.is_false_positive:
                    frame_fp += 1
                    frame_det_count += 1

                elif match.is_false_negative:
                    frame_fn += 1
                    frame_gt_count += 1

            total_gt += frame_gt_count
            total_det += frame_det_count
            matches_count += frame_matches
            fp_count += frame_fp
            fn_count += frame_fn

        # Calculate ID switches
        id_switches = 0
        for gt_id, associations in gt_track_associations.items():
            if len(associations) < 2:
                continue

            # Sort by frame
            associations.sort(key=lambda x: x[0])

            # Count switches
            prev_track_id = associations[0][1]
            for frame, track_id in associations[1:]:
                if track_id != prev_track_id and track_id != -1:
                    id_switches += 1
                prev_track_id = track_id

        # Calculate mostly tracked / mostly lost
        mt = 0
        ml = 0
        pt = 0

        for gt_id, associations in gt_track_associations.items():
            total_appearances = len([a for a in associations if a[1] != -1])
            total_frames_for_gt = len(associations)

            if total_frames_for_gt == 0:
                continue

            track_ratio = total_appearances / total_frames_for_gt

            if track_ratio >= 0.8:
                mt += 1
            elif track_ratio <= 0.2:
                ml += 1
            else:
                pt += 1

        # Calculate CLEAR MOT metrics
        # MOTA = 1 - (FN + FP + IDSW) / GT
        mota = 1.0 - (fn_count + fp_count + id_switches) / total_gt if total_gt > 0 else 0.0

        # MOTP = average IoU of matched detections
        all_ious = []
        for matches in self.matches_by_frame.values():
            for match in matches:
                if match.is_match and match.iou > 0:
                    if not class_filter or match.gt_object.class_name == class_filter:
                        all_ious.append(match.iou)

        motp = np.mean(all_ious) if all_ious else 0.0

        # MODA = MOTA without ID switches
        moda = 1.0 - (fn_count + fp_count) / total_gt if total_gt > 0 else 0.0

        # Precision and recall
        precision = matches_count / total_det if total_det > 0 else 0.0
        recall = matches_count / total_gt if total_gt > 0 else 0.0

        return TrackingMetrics(
            total_frames=total_frames,
            total_gt_objects=total_gt,
            total_detections=total_det,
            matches=matches_count,
            false_positives=fp_count,
            false_negatives=fn_count,
            id_switches=id_switches,
            mostly_tracked=mt,
            mostly_lost=ml,
            partially_tracked=pt,
            mota=mota,
            motp=motp,
            moda=moda,
            precision=precision,
            recall=recall
        )

    def generate_confusion_matrix(
        self,
        classes: List[str]
    ) -> ConfusionMatrix:
        """
        Generate confusion matrix for classification

        Args:
            classes: List of class names

        Returns:
            ConfusionMatrix object
        """
        n_classes = len(classes)
        matrix = np.zeros((n_classes, n_classes), dtype=int)

        class_to_idx = {cls: idx for idx, cls in enumerate(classes)}

        for matches in self.matches_by_frame.values():
            for match in matches:
                if not match.is_match:
                    continue

                gt_class = match.gt_object.class_name
                det_class = match.detected_track.class_name if match.detected_track else 'unknown'

                if gt_class in class_to_idx and det_class in class_to_idx:
                    gt_idx = class_to_idx[gt_class]
                    det_idx = class_to_idx[det_class]
                    matrix[gt_idx, det_idx] += 1

        return ConfusionMatrix(classes=classes, matrix=matrix)

    def analyze_errors_by_distance(
        self,
        distance_bins: List[float] = [0, 10, 25, 50, 100]
    ) -> Dict[str, DetectionMetrics]:
        """
        Analyze errors by distance bins

        Args:
            distance_bins: Distance bin edges (meters)

        Returns:
            Dictionary mapping distance range -> DetectionMetrics
        """
        results = {}

        for i in range(len(distance_bins) - 1):
            bin_start = distance_bins[i]
            bin_end = distance_bins[i + 1]
            bin_key = f"{bin_start}-{bin_end}m"

            tp, fp, fn = 0, 0, 0
            ious = []

            for matches in self.matches_by_frame.values():
                for match in matches:
                    if match.distance_3d is None:
                        continue

                    if bin_start <= match.distance_3d < bin_end:
                        if match.is_match:
                            tp += 1
                            ious.append(match.iou)
                        elif match.is_false_positive:
                            fp += 1
                        elif match.is_false_negative:
                            fn += 1

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

            results[bin_key] = DetectionMetrics(
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
                precision=precision,
                recall=recall,
                f1_score=f1,
                mean_iou=float(np.mean(ious)) if ious else 0.0
            )

        return results

    def analyze_errors_by_occlusion(
        self,
        occlusion_levels: List[int] = [0, 1, 2, 3]
    ) -> Dict[int, DetectionMetrics]:
        """
        Analyze errors by occlusion level

        Args:
            occlusion_levels: Occlusion levels to analyze

        Returns:
            Dictionary mapping occlusion_level -> DetectionMetrics
        """
        results = {}

        for level in occlusion_levels:
            tp, fp, fn = 0, 0, 0
            ious = []

            for matches in self.matches_by_frame.values():
                for match in matches:
                    if match.gt_object.occlusion_level != level:
                        continue

                    if match.is_match:
                        tp += 1
                        ious.append(match.iou)
                    elif match.is_false_positive:
                        fp += 1
                    elif match.is_false_negative:
                        fn += 1

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

            results[level] = DetectionMetrics(
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
                precision=precision,
                recall=recall,
                f1_score=f1,
                mean_iou=float(np.mean(ious)) if ious else 0.0
            )

        return results

    def get_summary_report(self) -> Dict:
        """Generate comprehensive summary report"""
        overall_detection = self.calculate_detection_metrics()
        overall_tracking = self.calculate_tracking_metrics({})

        # Per-class metrics
        classes = set()
        for matches in self.matches_by_frame.values():
            for match in matches:
                classes.add(match.gt_object.class_name)

        per_class_metrics = {}
        for cls in classes:
            per_class_metrics[cls] = self.calculate_detection_metrics(class_filter=cls)

        return {
            'overall_detection': {
                'precision': overall_detection.precision,
                'recall': overall_detection.recall,
                'f1_score': overall_detection.f1_score,
                'mean_iou': overall_detection.mean_iou,
                'true_positives': overall_detection.true_positives,
                'false_positives': overall_detection.false_positives,
                'false_negatives': overall_detection.false_negatives
            },
            'overall_tracking': {
                'mota': overall_tracking.mota,
                'motp': overall_tracking.motp,
                'moda': overall_tracking.moda,
                'precision': overall_tracking.precision,
                'recall': overall_tracking.recall,
                'id_switches': overall_tracking.id_switches,
                'mostly_tracked': overall_tracking.mostly_tracked,
                'mostly_lost': overall_tracking.mostly_lost
            },
            'per_class': {
                cls: {
                    'precision': metrics.precision,
                    'recall': metrics.recall,
                    'f1_score': metrics.f1_score,
                    'mean_iou': metrics.mean_iou
                }
                for cls, metrics in per_class_metrics.items()
            },
            'total_frames': len(self.matches_by_frame)
        }
