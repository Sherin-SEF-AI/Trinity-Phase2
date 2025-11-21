"""
Trinity Phase 2 - Camera Management System
Handles multiple camera capture, synchronization, and configuration
"""

import cv2
import numpy as np
import time
import threading
from queue import Queue, Empty
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Tuple, Callable
from loguru import logger


@dataclass
class CameraFrame:
    """Container for a single camera frame with metadata"""
    camera_id: int
    camera_name: str
    frame: np.ndarray
    timestamp: datetime
    frame_number: int
    fps: float
    resolution: Tuple[int, int]  # (width, height)


@dataclass
class SynchronizedFrames:
    """Container for synchronized frames from all cameras"""
    frames: List[CameraFrame]
    timestamp: datetime
    time_diff_ms: float  # Maximum time difference between frames


class CameraCapture:
    """Individual camera capture thread"""

    def __init__(
        self,
        camera_id: int,
        name: str,
        device_id: int,
        resolution: Tuple[int, int],
        fps: int,
        exposure: Optional[int] = None,
        brightness: int = 128,
        contrast: int = 128,
        saturation: int = 128
    ):
        self.camera_id = camera_id
        self.name = name
        self.device_id = device_id
        self.resolution = resolution
        self.target_fps = fps

        self.cap = None
        self.is_running = False
        self.thread = None
        self.frame_queue = Queue(maxsize=30)

        self.frame_number = 0
        self.actual_fps = 0.0
        self.last_frame_time = 0.0

        # Settings
        self.exposure = exposure
        self.brightness = brightness
        self.contrast = contrast
        self.saturation = saturation

        # Statistics
        self.frames_captured = 0
        self.frames_dropped = 0
        self.errors = 0

    def open(self) -> bool:
        """Open camera device"""
        try:
            self.cap = cv2.VideoCapture(self.device_id, cv2.CAP_V4L2)

            if not self.cap.isOpened():
                logger.error(f"Failed to open camera {self.name} (device {self.device_id})")
                return False

            # Set resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])

            # Set FPS
            self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)

            # Set other properties
            if self.exposure is not None:
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # Manual mode
                self.cap.set(cv2.CAP_PROP_EXPOSURE, self.exposure)
            else:
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3)  # Auto mode

            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, self.brightness)
            self.cap.set(cv2.CAP_PROP_CONTRAST, self.contrast)
            self.cap.set(cv2.CAP_PROP_SATURATION, self.saturation)

            # Set buffer size to minimum to reduce latency
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # Verify settings
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

            logger.info(
                f"Camera {self.name} opened: {actual_width}x{actual_height} @ {actual_fps:.1f} FPS"
            )

            return True

        except Exception as e:
            logger.error(f"Error opening camera {self.name}: {e}")
            return False

    def start(self):
        """Start capture thread"""
        if self.cap is None or not self.cap.isOpened():
            if not self.open():
                raise RuntimeError(f"Cannot start camera {self.name}: failed to open")

        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        logger.info(f"Camera {self.name} capture started")

    def _capture_loop(self):
        """Main capture loop (runs in separate thread)"""
        frame_interval = 1.0 / self.target_fps
        next_frame_time = time.time()

        while self.is_running:
            try:
                current_time = time.time()

                # Maintain target FPS
                if current_time < next_frame_time:
                    time.sleep(next_frame_time - current_time)
                    continue

                # Capture frame
                ret, frame = self.cap.read()

                if not ret or frame is None:
                    self.errors += 1
                    if self.errors > 10:
                        logger.error(f"Too many errors on camera {self.name}, stopping")
                        break
                    continue

                self.errors = 0  # Reset error count on success

                # Calculate FPS
                if self.last_frame_time > 0:
                    self.actual_fps = 1.0 / (current_time - self.last_frame_time)
                self.last_frame_time = current_time

                # Create frame object
                camera_frame = CameraFrame(
                    camera_id=self.camera_id,
                    camera_name=self.name,
                    frame=frame,
                    timestamp=datetime.utcnow(),
                    frame_number=self.frame_number,
                    fps=self.actual_fps,
                    resolution=(frame.shape[1], frame.shape[0])
                )

                # Add to queue (drop if full)
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()  # Remove oldest frame
                        self.frames_dropped += 1
                    except Empty:
                        pass

                self.frame_queue.put(camera_frame)
                self.frame_number += 1
                self.frames_captured += 1

                # Update next frame time
                next_frame_time = current_time + frame_interval

            except Exception as e:
                logger.error(f"Error in capture loop for camera {self.name}: {e}")
                self.errors += 1

    def get_latest_frame(self, timeout: float = 0.1) -> Optional[CameraFrame]:
        """Get the latest captured frame"""
        try:
            return self.frame_queue.get(timeout=timeout)
        except Empty:
            return None

    def stop(self):
        """Stop capture thread"""
        self.is_running = False
        if self.thread is not None:
            self.thread.join(timeout=2.0)

        if self.cap is not None:
            self.cap.release()

        logger.info(f"Camera {self.name} stopped")

    def get_statistics(self) -> Dict:
        """Get capture statistics"""
        return {
            'name': self.name,
            'device_id': self.device_id,
            'frames_captured': self.frames_captured,
            'frames_dropped': self.frames_dropped,
            'actual_fps': self.actual_fps,
            'errors': self.errors,
            'queue_size': self.frame_queue.qsize()
        }


class CameraManager:
    """
    Manages multiple cameras with synchronization
    """

    def __init__(self, config: Dict):
        """
        Initialize camera manager

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.cameras: List[CameraCapture] = []
        self.is_running = False

        # Synchronization settings
        sync_config = config.get('cameras', {}).get('synchronization', {})
        self.sync_enabled = sync_config.get('enabled', True)
        self.max_time_diff_ms = sync_config.get('max_time_diff_ms', 10)

        # Callbacks
        self.frame_callbacks: List[Callable] = []

        # Initialize cameras from config
        self._initialize_cameras()

    def _initialize_cameras(self):
        """Initialize camera objects from configuration"""
        camera_config = self.config.get('cameras', {})
        num_cameras = camera_config.get('count', 3)

        for i in range(1, num_cameras + 1):
            cam_key = f'camera_{i}'
            if cam_key in camera_config:
                cam_cfg = camera_config[cam_key]

                camera = CameraCapture(
                    camera_id=i,
                    name=cam_cfg.get('name', f'Camera {i}'),
                    device_id=cam_cfg.get('device_id', i - 1),
                    resolution=tuple(cam_cfg.get('resolution', [1920, 1080])),
                    fps=cam_cfg.get('fps', 30),
                    exposure=cam_cfg.get('exposure'),
                    brightness=cam_cfg.get('brightness', 128),
                    contrast=cam_cfg.get('contrast', 128),
                    saturation=cam_cfg.get('saturation', 128)
                )

                self.cameras.append(camera)
                logger.info(f"Initialized camera: {camera.name}")

    def start(self):
        """Start all cameras"""
        logger.info("Starting camera manager...")

        for camera in self.cameras:
            try:
                camera.start()
            except Exception as e:
                logger.error(f"Failed to start camera {camera.name}: {e}")

        self.is_running = True
        logger.success("Camera manager started")

    def stop(self):
        """Stop all cameras"""
        logger.info("Stopping camera manager...")
        self.is_running = False

        for camera in self.cameras:
            camera.stop()

        logger.success("Camera manager stopped")

    def get_synchronized_frames(
        self,
        timeout: float = 1.0
    ) -> Optional[SynchronizedFrames]:
        """
        Get synchronized frames from all cameras

        Args:
            timeout: Maximum time to wait for frames (seconds)

        Returns:
            SynchronizedFrames object or None if timeout
        """
        start_time = time.time()
        frames = []

        # Get latest frame from each camera
        for camera in self.cameras:
            frame = camera.get_latest_frame(timeout=timeout)
            if frame is None:
                # Timeout or no frame available
                if time.time() - start_time > timeout:
                    return None
                continue

            frames.append(frame)

        if len(frames) != len(self.cameras):
            return None

        # Check synchronization
        if self.sync_enabled and len(frames) > 1:
            timestamps = [f.timestamp for f in frames]
            time_diffs = [
                abs((timestamps[i] - timestamps[0]).total_seconds() * 1000)
                for i in range(1, len(timestamps))
            ]
            max_diff = max(time_diffs) if time_diffs else 0

            if max_diff > self.max_time_diff_ms:
                logger.warning(
                    f"Frame synchronization exceeds threshold: {max_diff:.1f}ms > {self.max_time_diff_ms}ms"
                )

            return SynchronizedFrames(
                frames=frames,
                timestamp=timestamps[0],  # Use first camera as reference
                time_diff_ms=max_diff
            )

        # No synchronization check
        return SynchronizedFrames(
            frames=frames,
            timestamp=frames[0].timestamp if frames else datetime.utcnow(),
            time_diff_ms=0.0
        )

    def get_frame_by_camera_id(self, camera_id: int, timeout: float = 0.1) -> Optional[CameraFrame]:
        """Get latest frame from specific camera"""
        for camera in self.cameras:
            if camera.camera_id == camera_id:
                return camera.get_latest_frame(timeout=timeout)
        return None

    def get_camera_count(self) -> int:
        """Get number of cameras"""
        return len(self.cameras)

    def get_camera_statistics(self) -> List[Dict]:
        """Get statistics for all cameras"""
        return [camera.get_statistics() for camera in self.cameras]

    def register_frame_callback(self, callback: Callable):
        """
        Register callback to be called when new frames are available

        Args:
            callback: Function that takes SynchronizedFrames as argument
        """
        self.frame_callbacks.append(callback)

    def get_camera_by_name(self, name: str) -> Optional[CameraCapture]:
        """Get camera by name"""
        for camera in self.cameras:
            if camera.name == name:
                return camera
        return None

    def update_camera_settings(
        self,
        camera_id: int,
        **settings
    ) -> bool:
        """
        Update camera settings dynamically

        Args:
            camera_id: Camera ID to update
            **settings: Settings to update (exposure, brightness, contrast, etc.)

        Returns:
            True if successful
        """
        for camera in self.cameras:
            if camera.camera_id == camera_id:
                if camera.cap is not None and camera.cap.isOpened():
                    for key, value in settings.items():
                        if key == 'exposure':
                            camera.cap.set(cv2.CAP_PROP_EXPOSURE, value)
                            camera.exposure = value
                        elif key == 'brightness':
                            camera.cap.set(cv2.CAP_PROP_BRIGHTNESS, value)
                            camera.brightness = value
                        elif key == 'contrast':
                            camera.cap.set(cv2.CAP_PROP_CONTRAST, value)
                            camera.contrast = value
                        elif key == 'saturation':
                            camera.cap.set(cv2.CAP_PROP_SATURATION, value)
                            camera.saturation = value

                    logger.info(f"Updated settings for camera {camera.name}: {settings}")
                    return True

        return False

    def __enter__(self):
        """Context manager enter"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()

    def health_check(self) -> Dict[str, bool]:
        """Check health of all cameras"""
        health = {}
        for camera in self.cameras:
            is_healthy = (
                camera.is_running and
                camera.cap is not None and
                camera.cap.isOpened() and
                camera.errors < 5 and
                camera.actual_fps > 0
            )
            health[camera.name] = is_healthy

        return health
