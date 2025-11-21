"""
Trinity Phase 2 - Multi-Stream Video Recorder
Synchronized recording from multiple cameras with advanced features
"""

import cv2
import numpy as np
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Tuple, Callable
from dataclasses import dataclass
from collections import deque
from queue import Queue, Empty
from loguru import logger

from trinity.core.camera_manager import SynchronizedFrames, CameraFrame


@dataclass
class RecordingConfig:
    """Configuration for video recording"""
    codec: str = 'h265'  # h265, h264, mjpeg
    quality: str = 'high'  # low, medium, high, lossless
    bitrate_mbps: int = 10
    container: str = 'mp4'  # mp4, avi, mkv
    fps: int = 30


@dataclass
class RecordingMetadata:
    """Metadata for a recording"""
    session_id: Optional[int]
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[float]
    frame_count: int
    cameras: List[str]
    resolution: Tuple[int, int]
    codec: str
    file_paths: List[str]
    notes: str = ""


class VideoWriter:
    """Threaded video writer for a single camera"""

    def __init__(
        self,
        camera_name: str,
        output_path: str,
        resolution: Tuple[int, int],
        fps: int,
        codec: str = 'h265'
    ):
        self.camera_name = camera_name
        self.output_path = output_path
        self.resolution = resolution
        self.fps = fps
        self.codec = codec

        self.writer = None
        self.frame_queue = Queue(maxsize=100)
        self.is_running = False
        self.thread = None

        self.frames_written = 0
        self.frames_dropped = 0

    def start(self):
        """Start writer thread"""
        # Get codec fourcc
        if self.codec == 'h265':
            fourcc = cv2.VideoWriter_fourcc(*'HEVC')
        elif self.codec == 'h264':
            fourcc = cv2.VideoWriter_fourcc(*'H264')
        elif self.codec == 'mjpeg':
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        else:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        # Create output directory
        Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize video writer
        self.writer = cv2.VideoWriter(
            self.output_path,
            fourcc,
            self.fps,
            self.resolution
        )

        if not self.writer.isOpened():
            raise RuntimeError(f"Failed to open video writer for {self.camera_name}")

        self.is_running = True
        self.thread = threading.Thread(target=self._write_loop, daemon=True)
        self.thread.start()

        logger.info(f"Video writer started for {self.camera_name}: {self.output_path}")

    def _write_loop(self):
        """Main writing loop (runs in separate thread)"""
        while self.is_running:
            try:
                frame = self.frame_queue.get(timeout=0.1)
                if frame is not None:
                    self.writer.write(frame)
                    self.frames_written += 1
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error writing frame for {self.camera_name}: {e}")

    def write_frame(self, frame: np.ndarray):
        """Queue frame for writing"""
        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()  # Drop oldest frame
                self.frames_dropped += 1
            except Empty:
                pass

        self.frame_queue.put(frame)

    def stop(self):
        """Stop writer and close file"""
        self.is_running = False
        if self.thread is not None:
            self.thread.join(timeout=2.0)

        # Write remaining frames
        while not self.frame_queue.empty():
            try:
                frame = self.frame_queue.get_nowait()
                if frame is not None and self.writer is not None:
                    self.writer.write(frame)
                    self.frames_written += 1
            except Empty:
                break

        if self.writer is not None:
            self.writer.release()

        logger.info(
            f"Video writer stopped for {self.camera_name}. "
            f"Frames written: {self.frames_written}, Dropped: {self.frames_dropped}"
        )


class CircularBuffer:
    """Circular buffer for pre-roll recording"""

    def __init__(self, max_duration_seconds: int, fps: int):
        """
        Initialize circular buffer

        Args:
            max_duration_seconds: Maximum buffer duration in seconds
            fps: Frames per second
        """
        self.max_frames = max_duration_seconds * fps
        self.buffer = deque(maxlen=self.max_frames)
        self.fps = fps

    def add_frame(self, frame: np.ndarray, timestamp: datetime):
        """Add frame to buffer"""
        self.buffer.append((frame, timestamp))

    def get_frames(self, duration_seconds: Optional[int] = None) -> List[Tuple[np.ndarray, datetime]]:
        """Get frames from buffer"""
        if duration_seconds is None:
            return list(self.buffer)

        num_frames = duration_seconds * self.fps
        return list(self.buffer)[-num_frames:] if len(self.buffer) >= num_frames else list(self.buffer)

    def clear(self):
        """Clear buffer"""
        self.buffer.clear()

    def get_duration_seconds(self) -> float:
        """Get current buffer duration"""
        return len(self.buffer) / self.fps if self.fps > 0 else 0


class MultiStreamRecorder:
    """
    Multi-camera synchronized recorder with advanced features
    """

    def __init__(self, config: Dict):
        """
        Initialize multi-stream recorder

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.recording_config = self._parse_recording_config()

        # Recording state
        self.is_recording = False
        self.writers: List[VideoWriter] = []
        self.recording_metadata: Optional[RecordingMetadata] = None

        # Circular buffer for pre-roll
        self.circular_buffer_enabled = config.get('recording', {}).get('circular_buffer', {}).get('enabled', True)
        self.circular_buffer_duration = config.get('recording', {}).get('circular_buffer', {}).get('duration_minutes', 10) * 60
        self.circular_buffers: Dict[str, CircularBuffer] = {}

        # Event-triggered recording
        self.event_triggered_enabled = config.get('recording', {}).get('event_triggered', {}).get('enabled', True)
        self.pre_roll_seconds = config.get('recording', {}).get('event_triggered', {}).get('pre_roll_seconds', 5)
        self.post_roll_seconds = config.get('recording', {}).get('event_triggered', {}).get('post_roll_seconds', 10)
        self.post_roll_timer = None

        # Output paths
        self.recordings_dir = Path(config.get('application', {}).get('recordings_dir', 'recordings'))
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

        # Callbacks
        self.recording_started_callbacks: List[Callable] = []
        self.recording_stopped_callbacks: List[Callable] = []

    def _parse_recording_config(self) -> RecordingConfig:
        """Parse recording configuration"""
        rec_config = self.config.get('recording', {})

        # Map quality to bitrate
        quality_bitrate = {
            'low': 2,
            'medium': 5,
            'high': 10,
            'lossless': 50
        }

        quality = rec_config.get('quality', 'high')
        bitrate = quality_bitrate.get(quality, 10)

        return RecordingConfig(
            codec=rec_config.get('codec', 'h265'),
            quality=quality,
            bitrate_mbps=rec_config.get('bitrate_mbps', bitrate),
            fps=self.config.get('cameras', {}).get('camera_1', {}).get('fps', 30)
        )

    def initialize_circular_buffers(self, camera_names: List[str], fps: int):
        """Initialize circular buffers for all cameras"""
        if self.circular_buffer_enabled:
            for camera_name in camera_names:
                self.circular_buffers[camera_name] = CircularBuffer(
                    self.circular_buffer_duration, fps
                )
            logger.info(f"Initialized circular buffers ({self.circular_buffer_duration}s)")

    def update_circular_buffers(self, frames: SynchronizedFrames):
        """Update circular buffers with new frames"""
        if not self.circular_buffer_enabled:
            return

        for camera_frame in frames.frames:
            camera_name = camera_frame.camera_name
            if camera_name in self.circular_buffers:
                self.circular_buffers[camera_name].add_frame(
                    camera_frame.frame, camera_frame.timestamp
                )

    def start_recording(
        self,
        session_id: Optional[int] = None,
        camera_frames: Optional[SynchronizedFrames] = None,
        notes: str = ""
    ) -> RecordingMetadata:
        """
        Start recording from all cameras

        Args:
            session_id: Database session ID (optional)
            camera_frames: Initial synchronized frames
            notes: Recording notes

        Returns:
            RecordingMetadata object
        """
        if self.is_recording:
            logger.warning("Recording already in progress")
            return self.recording_metadata

        if camera_frames is None or len(camera_frames.frames) == 0:
            raise ValueError("No camera frames provided")

        # Generate output paths
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = self.recordings_dir / f"session_{session_id or timestamp}"
        session_dir.mkdir(parents=True, exist_ok=True)

        # Initialize writers for each camera
        self.writers = []
        file_paths = []

        for camera_frame in camera_frames.frames:
            output_path = str(session_dir / f"{camera_frame.camera_name}_{timestamp}.mp4")
            file_paths.append(output_path)

            writer = VideoWriter(
                camera_name=camera_frame.camera_name,
                output_path=output_path,
                resolution=camera_frame.resolution,
                fps=self.recording_config.fps,
                codec=self.recording_config.codec
            )
            writer.start()
            self.writers.append(writer)

        # Write pre-roll frames from circular buffer
        if self.circular_buffer_enabled:
            self._write_preroll_frames(camera_frames)

        # Create metadata
        self.recording_metadata = RecordingMetadata(
            session_id=session_id,
            start_time=datetime.now(),
            end_time=None,
            duration_seconds=None,
            frame_count=0,
            cameras=[cf.camera_name for cf in camera_frames.frames],
            resolution=camera_frames.frames[0].resolution,
            codec=self.recording_config.codec,
            file_paths=file_paths,
            notes=notes
        )

        self.is_recording = True

        # Trigger callbacks
        for callback in self.recording_started_callbacks:
            callback(self.recording_metadata)

        logger.success(f"Recording started: {len(self.writers)} cameras")
        return self.recording_metadata

    def _write_preroll_frames(self, camera_frames: SynchronizedFrames):
        """Write pre-roll frames from circular buffer"""
        if self.pre_roll_seconds <= 0:
            return

        for i, camera_frame in enumerate(camera_frames.frames):
            camera_name = camera_frame.camera_name
            if camera_name in self.circular_buffers:
                preroll_frames = self.circular_buffers[camera_name].get_frames(
                    self.pre_roll_seconds
                )

                if preroll_frames and i < len(self.writers):
                    logger.info(f"Writing {len(preroll_frames)} pre-roll frames for {camera_name}")
                    for frame, _ in preroll_frames:
                        self.writers[i].write_frame(frame)

    def record_frames(self, frames: SynchronizedFrames):
        """
        Record synchronized frames from all cameras

        Args:
            frames: Synchronized frames from all cameras
        """
        # Always update circular buffers (even when not recording)
        self.update_circular_buffers(frames)

        if not self.is_recording:
            return

        # Write frames to each writer
        for i, camera_frame in enumerate(frames.frames):
            if i < len(self.writers):
                self.writers[i].write_frame(camera_frame.frame)

        # Update frame count
        if self.recording_metadata:
            self.recording_metadata.frame_count += 1

    def stop_recording(self) -> Optional[RecordingMetadata]:
        """
        Stop recording and finalize files

        Returns:
            RecordingMetadata with final information
        """
        if not self.is_recording:
            logger.warning("No recording in progress")
            return None

        # Stop all writers
        for writer in self.writers:
            writer.stop()

        # Finalize metadata
        if self.recording_metadata:
            self.recording_metadata.end_time = datetime.now()
            self.recording_metadata.duration_seconds = (
                self.recording_metadata.end_time - self.recording_metadata.start_time
            ).total_seconds()

        self.is_recording = False
        metadata = self.recording_metadata
        self.recording_metadata = None
        self.writers = []

        # Trigger callbacks
        for callback in self.recording_stopped_callbacks:
            callback(metadata)

        logger.success(
            f"Recording stopped. Duration: {metadata.duration_seconds:.1f}s, "
            f"Frames: {metadata.frame_count}"
        )

        return metadata

    def trigger_event_recording(
        self,
        event_name: str,
        camera_frames: SynchronizedFrames,
        duration_seconds: Optional[int] = None
    ) -> RecordingMetadata:
        """
        Trigger event-based recording with pre and post roll

        Args:
            event_name: Name of the event
            camera_frames: Current synchronized frames
            duration_seconds: Duration to record (default: post_roll_seconds)

        Returns:
            RecordingMetadata object
        """
        if not self.event_triggered_enabled:
            logger.warning("Event-triggered recording is disabled")
            return None

        # Start recording if not already recording
        if not self.is_recording:
            metadata = self.start_recording(
                camera_frames=camera_frames,
                notes=f"Event: {event_name}"
            )

            # Schedule automatic stop after post-roll duration
            if self.post_roll_timer is not None:
                self.post_roll_timer.cancel()

            duration = duration_seconds or self.post_roll_seconds
            self.post_roll_timer = threading.Timer(duration, self.stop_recording)
            self.post_roll_timer.start()

            logger.info(f"Event recording triggered: {event_name} (duration: {duration}s)")
            return metadata
        else:
            # Extend existing recording
            if self.post_roll_timer is not None:
                self.post_roll_timer.cancel()

            duration = duration_seconds or self.post_roll_seconds
            self.post_roll_timer = threading.Timer(duration, self.stop_recording)
            self.post_roll_timer.start()

            logger.info(f"Event recording extended: {event_name} (duration: {duration}s)")
            return self.recording_metadata

    def export_clip(
        self,
        start_time: datetime,
        end_time: datetime,
        camera_names: Optional[List[str]] = None,
        output_dir: Optional[Path] = None
    ) -> List[str]:
        """
        Export video clip from a specific time range

        Args:
            start_time: Clip start time
            end_time: Clip end time
            camera_names: List of camera names to export (None = all)
            output_dir: Output directory (None = use default)

        Returns:
            List of exported file paths
        """
        # This would require seeking in the video files
        # For now, this is a placeholder
        logger.warning("Clip export not yet implemented - requires video seeking")
        return []

    def get_recording_status(self) -> Dict:
        """Get current recording status"""
        status = {
            'is_recording': self.is_recording,
            'circular_buffer_enabled': self.circular_buffer_enabled,
        }

        if self.recording_metadata:
            elapsed = (datetime.now() - self.recording_metadata.start_time).total_seconds()
            status.update({
                'session_id': self.recording_metadata.session_id,
                'start_time': self.recording_metadata.start_time.isoformat(),
                'elapsed_seconds': elapsed,
                'frame_count': self.recording_metadata.frame_count,
                'cameras': self.recording_metadata.cameras,
                'file_paths': self.recording_metadata.file_paths
            })

        # Add circular buffer info
        if self.circular_buffer_enabled:
            buffer_info = {}
            for camera_name, buffer in self.circular_buffers.items():
                buffer_info[camera_name] = {
                    'duration_seconds': buffer.get_duration_seconds(),
                    'frame_count': len(buffer.buffer)
                }
            status['circular_buffers'] = buffer_info

        return status

    def register_callback(self, event: str, callback: Callable):
        """
        Register callback for recording events

        Args:
            event: 'started' or 'stopped'
            callback: Callback function
        """
        if event == 'started':
            self.recording_started_callbacks.append(callback)
        elif event == 'stopped':
            self.recording_stopped_callbacks.append(callback)
        else:
            raise ValueError(f"Unknown event type: {event}")

    def __enter__(self):
        """Context manager enter"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.is_recording:
            self.stop_recording()
