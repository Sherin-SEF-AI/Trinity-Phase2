"""
Trinity Phase 4 - Dataset Management & Annotation Tools
Semi-automatic annotation, multi-format export (COCO/KITTI/nuScenes), and PII anonymization
"""

import cv2
import numpy as np
import json
from typing import List, Optional, Dict, Tuple, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import shutil
from loguru import logger

from trinity.detection.tracker import Track


@dataclass
class Annotation:
    """Annotation for a single object"""
    annotation_id: int
    image_id: int
    category_id: int
    category_name: str

    # 2D bounding box (x, y, width, height)
    bbox: Tuple[float, float, float, float]

    # 3D information (optional)
    position_3d: Optional[Tuple[float, float, float]] = None
    dimensions_3d: Optional[Tuple[float, float, float]] = None  # height, width, length
    rotation_y: Optional[float] = None  # rotation around Y-axis in radians

    # Metadata
    area: float = 0.0
    iscrowd: bool = False
    occlusion: int = 0  # 0=fully visible, 1=partly, 2=largely, 3=unknown
    truncation: float = 0.0  # 0.0-1.0

    # Tracking information
    track_id: Optional[int] = None

    # Annotation metadata
    annotator: str = "auto"
    verified: bool = False
    confidence: float = 1.0

    # Additional attributes
    attributes: Dict = field(default_factory=dict)


@dataclass
class ImageInfo:
    """Image metadata"""
    image_id: int
    file_name: str
    width: int
    height: int

    # Optional fields
    frame_number: Optional[int] = None
    camera_id: Optional[int] = None
    timestamp: Optional[str] = None

    # Calibration (for 3D)
    camera_intrinsic: Optional[List[float]] = None  # 3x3 matrix flattened
    camera_extrinsic: Optional[List[float]] = None  # 4x4 matrix flattened


@dataclass
class Category:
    """Object category"""
    category_id: int
    name: str
    supercategory: str = "object"


class AnnotationPropagator:
    """
    Propagate annotations across frames using tracking information
    """

    def __init__(self, iou_threshold: float = 0.5):
        """
        Initialize annotation propagator

        Args:
            iou_threshold: IoU threshold for matching annotations to tracks
        """
        self.iou_threshold = iou_threshold

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

        intersection = (x_right - x_left) * (y_bottom - y_top)
        union = w1 * h1 + w2 * h2 - intersection

        return intersection / union if union > 0 else 0.0

    def propagate_annotations(
        self,
        source_annotations: List[Annotation],
        target_tracks: List[Track],
        source_frame: int,
        target_frame: int
    ) -> List[Annotation]:
        """
        Propagate annotations from source frame to target frame using tracks

        Args:
            source_annotations: Annotations from source frame
            target_tracks: Tracks in target frame
            source_frame: Source frame number
            target_frame: Target frame number

        Returns:
            List of propagated annotations
        """
        propagated = []

        # Match source annotations to tracks
        for ann in source_annotations:
            best_match = None
            best_iou = 0.0

            for track in target_tracks:
                # Check if class matches
                if track.class_name != ann.category_name:
                    continue

                # Calculate IoU
                track_bbox = track.bbox
                iou = self.calculate_iou(ann.bbox, track_bbox)

                if iou > best_iou and iou >= self.iou_threshold:
                    best_iou = iou
                    best_match = track

            # Propagate if match found
            if best_match:
                propagated_ann = Annotation(
                    annotation_id=-1,  # Will be assigned later
                    image_id=-1,  # Will be assigned later
                    category_id=ann.category_id,
                    category_name=ann.category_name,
                    bbox=best_match.bbox,
                    track_id=best_match.track_id,
                    annotator="propagated",
                    verified=False,
                    confidence=best_iou,
                    attributes={
                        'source_frame': source_frame,
                        'propagation_iou': best_iou
                    }
                )

                # Copy 3D information if available
                if hasattr(best_match, 'world_position') and best_match.world_position:
                    propagated_ann.position_3d = best_match.world_position

                propagated.append(propagated_ann)

        return propagated


class PIIAnonymizer:
    """
    Anonymize personally identifiable information (faces and license plates)
    """

    def __init__(self, blur_radius: int = 15):
        """
        Initialize PII anonymizer

        Args:
            blur_radius: Radius for Gaussian blur
        """
        self.blur_radius = blur_radius

        # Load face detection model (Haar Cascade)
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

        # License plate detection (simple approach using contours)
        # For production, use specialized model like YOLO or ALPR

        logger.info("PII anonymizer initialized")

    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in image

        Args:
            image: Input image (BGR)

        Returns:
            List of face bounding boxes (x, y, w, h)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        return [tuple(face) for face in faces]

    def detect_license_plates(
        self,
        image: np.ndarray
    ) -> List[Tuple[int, int, int, int]]:
        """
        Detect potential license plates in image

        Args:
            image: Input image (BGR)

        Returns:
            List of plate bounding boxes (x, y, w, h)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply bilateral filter to reduce noise
        bilateral = cv2.bilateralFilter(gray, 11, 17, 17)

        # Edge detection
        edges = cv2.Canny(bilateral, 30, 200)

        # Find contours
        contours, _ = cv2.findContours(
            edges.copy(),
            cv2.RETR_TREE,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # Filter contours by aspect ratio (typical license plate ratios)
        plates = []

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / float(h)

            # License plates typically have aspect ratio between 2:1 and 5:1
            if 2.0 <= aspect_ratio <= 5.0 and w > 50 and h > 15:
                plates.append((x, y, w, h))

        return plates

    def blur_region(
        self,
        image: np.ndarray,
        bbox: Tuple[int, int, int, int]
    ) -> np.ndarray:
        """
        Blur a region in the image

        Args:
            image: Input image
            bbox: Bounding box to blur (x, y, w, h)

        Returns:
            Image with blurred region
        """
        x, y, w, h = bbox

        # Extract region
        region = image[y:y+h, x:x+w]

        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(region, (self.blur_radius, self.blur_radius), 0)

        # Replace region
        result = image.copy()
        result[y:y+h, x:x+w] = blurred

        return result

    def anonymize_image(
        self,
        image: np.ndarray,
        blur_faces: bool = True,
        blur_plates: bool = True
    ) -> Tuple[np.ndarray, Dict]:
        """
        Anonymize an image by blurring faces and license plates

        Args:
            image: Input image (BGR)
            blur_faces: Whether to blur faces
            blur_plates: Whether to blur license plates

        Returns:
            Tuple of (anonymized image, metadata dict)
        """
        result = image.copy()
        metadata = {
            'faces_blurred': 0,
            'plates_blurred': 0,
            'face_boxes': [],
            'plate_boxes': []
        }

        # Blur faces
        if blur_faces:
            faces = self.detect_faces(image)
            for face in faces:
                result = self.blur_region(result, face)
                metadata['face_boxes'].append(face)
            metadata['faces_blurred'] = len(faces)

        # Blur license plates
        if blur_plates:
            plates = self.detect_license_plates(image)
            for plate in plates:
                result = self.blur_region(result, plate)
                metadata['plate_boxes'].append(plate)
            metadata['plates_blurred'] = len(plates)

        return result, metadata


class DatasetExporter:
    """
    Export dataset in multiple formats (COCO, KITTI, nuScenes)
    """

    def __init__(self, output_dir: Path):
        """
        Initialize dataset exporter

        Args:
            output_dir: Output directory for exported datasets
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Dataset exporter initialized: {output_dir}")

    def export_coco(
        self,
        images: List[ImageInfo],
        annotations: List[Annotation],
        categories: List[Category],
        info: Optional[Dict] = None
    ) -> Path:
        """
        Export dataset in COCO format

        Args:
            images: List of image metadata
            annotations: List of annotations
            categories: List of categories
            info: Optional dataset info

        Returns:
            Path to exported JSON file
        """
        output_file = self.output_dir / "coco_annotations.json"

        # Build COCO structure
        coco_data = {
            "info": info or {
                "description": "Trinity AV Testing Dataset",
                "version": "1.0",
                "year": datetime.now().year,
                "contributor": "Trinity Phase 2",
                "date_created": datetime.now().isoformat()
            },
            "licenses": [],
            "images": [],
            "annotations": [],
            "categories": []
        }

        # Add categories
        for cat in categories:
            coco_data["categories"].append({
                "id": cat.category_id,
                "name": cat.name,
                "supercategory": cat.supercategory
            })

        # Add images
        for img in images:
            coco_data["images"].append({
                "id": img.image_id,
                "file_name": img.file_name,
                "width": img.width,
                "height": img.height,
                "frame_number": img.frame_number,
                "camera_id": img.camera_id,
                "timestamp": img.timestamp
            })

        # Add annotations
        for ann in annotations:
            x, y, w, h = ann.bbox

            coco_data["annotations"].append({
                "id": ann.annotation_id,
                "image_id": ann.image_id,
                "category_id": ann.category_id,
                "bbox": [x, y, w, h],
                "area": ann.area if ann.area > 0 else w * h,
                "iscrowd": 1 if ann.iscrowd else 0,
                "track_id": ann.track_id,
                "verified": ann.verified,
                "confidence": ann.confidence
            })

        # Write to file
        with open(output_file, 'w') as f:
            json.dump(coco_data, f, indent=2)

        logger.success(f"COCO dataset exported: {output_file}")
        return output_file

    def export_kitti(
        self,
        images: List[ImageInfo],
        annotations: List[Annotation],
        image_dir: Path
    ) -> Path:
        """
        Export dataset in KITTI format

        Args:
            images: List of image metadata
            annotations: List of annotations
            image_dir: Directory containing images

        Returns:
            Path to label directory
        """
        label_dir = self.output_dir / "kitti" / "labels"
        label_dir.mkdir(parents=True, exist_ok=True)

        # Group annotations by image
        annotations_by_image = defaultdict(list)
        for ann in annotations:
            annotations_by_image[ann.image_id].append(ann)

        # Write label file for each image
        for img in images:
            frame_num = img.frame_number if img.frame_number is not None else img.image_id
            label_file = label_dir / f"{frame_num:06d}.txt"

            with open(label_file, 'w') as f:
                img_annotations = annotations_by_image.get(img.image_id, [])

                for ann in img_annotations:
                    # KITTI format:
                    # type truncated occluded alpha bbox_left bbox_top bbox_right bbox_bottom
                    # dimensions_h dimensions_w dimensions_l location_x location_y location_z rotation_y

                    x, y, w, h = ann.bbox

                    # Basic 2D format
                    line_parts = [
                        ann.category_name,  # type
                        f"{ann.truncation:.2f}",  # truncated
                        str(ann.occlusion),  # occluded
                        "0.0",  # alpha (observation angle)
                        f"{x:.2f}",  # bbox left
                        f"{y:.2f}",  # bbox top
                        f"{x + w:.2f}",  # bbox right
                        f"{y + h:.2f}",  # bbox bottom
                    ]

                    # Add 3D information if available
                    if ann.dimensions_3d and ann.position_3d:
                        h3d, w3d, l3d = ann.dimensions_3d
                        x3d, y3d, z3d = ann.position_3d

                        line_parts.extend([
                            f"{h3d:.2f}",  # height
                            f"{w3d:.2f}",  # width
                            f"{l3d:.2f}",  # length
                            f"{x3d:.2f}",  # location x
                            f"{y3d:.2f}",  # location y
                            f"{z3d:.2f}",  # location z
                            f"{ann.rotation_y or 0.0:.2f}"  # rotation_y
                        ])
                    else:
                        # Default values for 3D
                        line_parts.extend([
                            "0.0", "0.0", "0.0",  # dimensions
                            "0.0", "0.0", "0.0",  # location
                            "0.0"  # rotation
                        ])

                    f.write(" ".join(line_parts) + "\n")

        logger.success(f"KITTI dataset exported: {label_dir}")
        return label_dir

    def export_nuscenes(
        self,
        images: List[ImageInfo],
        annotations: List[Annotation],
        categories: List[Category]
    ) -> Path:
        """
        Export dataset in nuScenes format (simplified)

        Args:
            images: List of image metadata
            annotations: List of annotations
            categories: List of categories

        Returns:
            Path to output directory
        """
        nuscenes_dir = self.output_dir / "nuscenes"
        nuscenes_dir.mkdir(parents=True, exist_ok=True)

        # nuScenes has complex structure - this is simplified version
        # Full implementation would require sample, ego_pose, calibrated_sensor, etc.

        # Create simplified annotation format
        data = {
            "version": "trinity-v1.0",
            "images": [],
            "annotations": [],
            "categories": [asdict(cat) for cat in categories]
        }

        for img in images:
            data["images"].append({
                "token": f"img_{img.image_id}",
                "filename": img.file_name,
                "width": img.width,
                "height": img.height,
                "timestamp": img.timestamp
            })

        for ann in annotations:
            data["annotations"].append({
                "token": f"ann_{ann.annotation_id}",
                "image_token": f"img_{ann.image_id}",
                "category_name": ann.category_name,
                "bbox": list(ann.bbox),
                "position_3d": list(ann.position_3d) if ann.position_3d else None,
                "dimensions_3d": list(ann.dimensions_3d) if ann.dimensions_3d else None,
                "rotation": ann.rotation_y,
                "track_id": ann.track_id
            })

        output_file = nuscenes_dir / "annotations.json"
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

        logger.success(f"nuScenes dataset exported: {nuscenes_dir}")
        return nuscenes_dir


class DatasetSplitter:
    """
    Split dataset into train/val/test sets
    """

    @staticmethod
    def split_dataset(
        image_ids: List[int],
        split_ratios: Tuple[float, float, float] = (0.7, 0.15, 0.15),
        shuffle: bool = True,
        seed: Optional[int] = 42
    ) -> Dict[str, List[int]]:
        """
        Split dataset into train/val/test sets

        Args:
            image_ids: List of image IDs
            split_ratios: Tuple of (train, val, test) ratios
            shuffle: Whether to shuffle before splitting
            seed: Random seed for reproducibility

        Returns:
            Dictionary with 'train', 'val', 'test' keys
        """
        assert abs(sum(split_ratios) - 1.0) < 1e-6, "Split ratios must sum to 1.0"

        # Set random seed
        if seed is not None:
            np.random.seed(seed)

        # Shuffle if requested
        ids = image_ids.copy()
        if shuffle:
            np.random.shuffle(ids)

        # Calculate split indices
        n_total = len(ids)
        n_train = int(n_total * split_ratios[0])
        n_val = int(n_total * split_ratios[1])

        # Split
        train_ids = ids[:n_train]
        val_ids = ids[n_train:n_train + n_val]
        test_ids = ids[n_train + n_val:]

        logger.info(f"Dataset split: train={len(train_ids)}, val={len(val_ids)}, test={len(test_ids)}")

        return {
            'train': train_ids,
            'val': val_ids,
            'test': test_ids
        }


class DatasetManager:
    """
    Complete dataset management system
    """

    def __init__(
        self,
        dataset_dir: Path,
        config: Optional[Dict] = None
    ):
        """
        Initialize dataset manager

        Args:
            dataset_dir: Base directory for dataset
            config: Optional configuration
        """
        self.dataset_dir = Path(dataset_dir)
        self.dataset_dir.mkdir(parents=True, exist_ok=True)

        self.config = config or {}

        # Initialize components
        self.propagator = AnnotationPropagator()
        self.anonymizer = PIIAnonymizer(
            blur_radius=self.config.get('blur_radius', 15)
        )
        self.exporter = DatasetExporter(self.dataset_dir / "exports")

        # Storage
        self.images: List[ImageInfo] = []
        self.annotations: List[Annotation] = []
        self.categories: List[Category] = []

        self.next_annotation_id = 1
        self.next_image_id = 1

        logger.info(f"Dataset manager initialized: {dataset_dir}")

    def add_category(self, name: str, supercategory: str = "object") -> int:
        """Add a category and return its ID"""
        # Check if already exists
        for cat in self.categories:
            if cat.name == name:
                return cat.category_id

        category_id = len(self.categories) + 1
        self.categories.append(Category(
            category_id=category_id,
            name=name,
            supercategory=supercategory
        ))

        return category_id

    def add_image(
        self,
        file_name: str,
        width: int,
        height: int,
        **kwargs
    ) -> int:
        """Add an image and return its ID"""
        image_id = self.next_image_id
        self.next_image_id += 1

        self.images.append(ImageInfo(
            image_id=image_id,
            file_name=file_name,
            width=width,
            height=height,
            **kwargs
        ))

        return image_id

    def add_annotation(
        self,
        image_id: int,
        category_name: str,
        bbox: Tuple[float, float, float, float],
        **kwargs
    ) -> int:
        """Add an annotation and return its ID"""
        # Get category ID
        category_id = self.add_category(category_name)

        annotation_id = self.next_annotation_id
        self.next_annotation_id += 1

        self.annotations.append(Annotation(
            annotation_id=annotation_id,
            image_id=image_id,
            category_id=category_id,
            category_name=category_name,
            bbox=bbox,
            **kwargs
        ))

        return annotation_id

    def export_all_formats(
        self,
        image_dir: Path,
        anonymize: bool = False
    ):
        """
        Export dataset in all supported formats

        Args:
            image_dir: Directory containing images
            anonymize: Whether to anonymize images
        """
        logger.info("Exporting dataset in all formats...")

        # Anonymize images if requested
        if anonymize:
            self._anonymize_images(image_dir)

        # Export COCO
        self.exporter.export_coco(
            self.images,
            self.annotations,
            self.categories
        )

        # Export KITTI
        self.exporter.export_kitti(
            self.images,
            self.annotations,
            image_dir
        )

        # Export nuScenes
        self.exporter.export_nuscenes(
            self.images,
            self.annotations,
            self.categories
        )

        logger.success("All formats exported successfully")

    def _anonymize_images(self, image_dir: Path):
        """Anonymize all images in directory"""
        anonymized_dir = self.dataset_dir / "anonymized"
        anonymized_dir.mkdir(exist_ok=True)

        for img_info in self.images:
            img_path = image_dir / img_info.file_name

            if not img_path.exists():
                logger.warning(f"Image not found: {img_path}")
                continue

            # Load image
            image = cv2.imread(str(img_path))

            # Anonymize
            anonymized, metadata = self.anonymizer.anonymize_image(image)

            # Save
            output_path = anonymized_dir / img_info.file_name
            cv2.imwrite(str(output_path), anonymized)

            logger.debug(f"Anonymized {img_info.file_name}: {metadata}")
