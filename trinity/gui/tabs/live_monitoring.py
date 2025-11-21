"""
Trinity Phase 2 - Live Monitoring Tab
Real-time camera feed display and monitoring
"""

import numpy as np
import cv2
from typing import Optional, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGridLayout, QGroupBox, QPushButton, QComboBox
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from loguru import logger

from trinity.core.camera_manager import CameraManager, SynchronizedFrames
from trinity.core.recorder import MultiStreamRecorder


class CameraFeedWidget(QLabel):
    """Widget for displaying camera feed"""

    def __init__(self, camera_name: str, parent=None):
        super().__init__(parent)
        self.camera_name = camera_name

        # Setup label
        self.setObjectName("cameraFeed")
        self.setMinimumSize(320, 240)
        self.setScaledContents(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Default text
        self.setText(f"{camera_name}\nNo Feed")

    def update_frame(self, frame: np.ndarray):
        """Update displayed frame"""
        if frame is None:
            return

        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Create QImage
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            q_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

            # Set pixmap
            self.setPixmap(QPixmap.fromImage(q_image))

        except Exception as e:
            logger.error(f"Error updating frame for {self.camera_name}: {e}")


class MetricsWidget(QGroupBox):
    """Widget for displaying system metrics"""

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.setObjectName("metricsPanel")

        layout = QVBoxLayout(self)

        # Create metric labels
        self.metrics_labels = {}
        self.add_metric("FPS", "0.0")
        self.add_metric("Frame Count", "0")
        self.add_metric("Resolution", "0x0")
        self.add_metric("Latency", "0ms")

    def add_metric(self, name: str, initial_value: str):
        """Add a metric display"""
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 4, 0, 4)

        name_label = QLabel(f"{name}:")
        name_label.setObjectName("subtitleLabel")
        container_layout.addWidget(name_label)

        value_label = QLabel(initial_value)
        value_label.setObjectName("valueLabel")
        value_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #4ec9b0;")
        container_layout.addWidget(value_label)
        container_layout.addStretch()

        self.layout().addWidget(container)
        self.metrics_labels[name] = value_label

    def update_metric(self, name: str, value: str):
        """Update metric value"""
        if name in self.metrics_labels:
            self.metrics_labels[name].setText(value)


class LiveMonitoringTab(QWidget):
    """
    Live monitoring tab for real-time camera feeds and metrics
    """

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config

        # Managers
        self.camera_manager: Optional[CameraManager] = None
        self.recorder: Optional[MultiStreamRecorder] = None

        # UI components
        self.camera_feeds: List[CameraFeedWidget] = []
        self.metrics_widgets: List[MetricsWidget] = []

        # Setup UI
        self.init_ui()

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_feeds)
        self.update_timer.start(33)  # ~30 FPS

        logger.info("Live monitoring tab initialized")

    def init_ui(self):
        """Initialize user interface"""
        main_layout = QHBoxLayout(self)

        # Left panel - Camera controls (25%)
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)

        # Center panel - Camera feeds (50%)
        center_panel = self.create_center_panel()
        main_layout.addWidget(center_panel, 2)

        # Right panel - Metrics (25%)
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 1)

    def create_left_panel(self) -> QWidget:
        """Create left control panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Camera management section
        camera_group = QGroupBox("Camera Management")
        camera_layout = QVBoxLayout(camera_group)

        # Camera 1 controls
        cam1_label = QLabel("Camera 1")
        cam1_label.setObjectName("headerLabel")
        camera_layout.addWidget(cam1_label)

        self.cam1_status = QLabel("Status: Disconnected")
        camera_layout.addWidget(self.cam1_status)

        camera_layout.addSpacing(10)

        # Camera 2 controls
        cam2_label = QLabel("Camera 2")
        cam2_label.setObjectName("headerLabel")
        camera_layout.addWidget(cam2_label)

        self.cam2_status = QLabel("Status: Disconnected")
        camera_layout.addWidget(self.cam2_status)

        camera_layout.addSpacing(10)

        # Camera 3 controls
        cam3_label = QLabel("Camera 3")
        cam3_label.setObjectName("headerLabel")
        camera_layout.addWidget(cam3_label)

        self.cam3_status = QLabel("Status: Disconnected")
        camera_layout.addWidget(self.cam3_status)

        camera_layout.addStretch()
        layout.addWidget(camera_group)

        # View options
        view_group = QGroupBox("View Options")
        view_layout = QVBoxLayout(view_group)

        view_layout.addWidget(QLabel("View Mode:"))
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems([
            "3-Camera Grid",
            "Single Camera",
            "Bird's Eye View",
            "3D Visualization"
        ])
        self.view_mode_combo.currentTextChanged.connect(self.on_view_mode_changed)
        view_layout.addWidget(self.view_mode_combo)

        view_layout.addSpacing(10)

        # Overlay options
        view_layout.addWidget(QLabel("Overlays:"))

        self.show_detections_btn = QPushButton("Show Detections")
        self.show_detections_btn.setCheckable(True)
        self.show_detections_btn.setEnabled(False)
        view_layout.addWidget(self.show_detections_btn)

        self.show_tracks_btn = QPushButton("Show Tracks")
        self.show_tracks_btn.setCheckable(True)
        self.show_tracks_btn.setEnabled(False)
        view_layout.addWidget(self.show_tracks_btn)

        view_layout.addStretch()
        layout.addWidget(view_group)

        layout.addStretch()

        return panel

    def create_center_panel(self) -> QWidget:
        """Create center camera feed panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Title
        title = QLabel("Live Camera Feeds")
        title.setObjectName("headerLabel")
        layout.addWidget(title)

        # Camera grid
        self.camera_grid = QGridLayout()

        # Create 3 camera feed widgets
        camera_names = ["Camera 1", "Camera 2", "Camera 3"]
        for i, name in enumerate(camera_names):
            feed = CameraFeedWidget(name)
            self.camera_feeds.append(feed)

            # Arrange in grid: 2 on top, 1 on bottom
            if i < 2:
                self.camera_grid.addWidget(feed, 0, i)
            else:
                self.camera_grid.addWidget(feed, 1, 0, 1, 2)  # Span 2 columns

        layout.addLayout(self.camera_grid)

        # Playback controls (for future use)
        controls_layout = QHBoxLayout()

        # Placeholder for timeline scrubber
        controls_layout.addWidget(QLabel("Timeline controls coming soon..."))

        layout.addLayout(controls_layout)

        return panel

    def create_right_panel(self) -> QWidget:
        """Create right metrics panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Metrics for each camera
        for i in range(3):
            metrics = MetricsWidget(f"Camera {i+1} Metrics")
            self.metrics_widgets.append(metrics)
            layout.addWidget(metrics)

        # System metrics
        system_metrics = QGroupBox("System Metrics")
        system_layout = QVBoxLayout(system_metrics)

        self.system_fps_label = QLabel("Overall FPS: 0.0")
        system_layout.addWidget(self.system_fps_label)

        self.sync_status_label = QLabel("Sync: OK")
        system_layout.addWidget(self.sync_status_label)

        layout.addWidget(system_metrics)

        # Recording status
        recording_group = QGroupBox("Recording Status")
        recording_layout = QVBoxLayout(recording_group)

        self.recording_status_label = QLabel("Not Recording")
        recording_layout.addWidget(self.recording_status_label)

        self.recording_duration_label = QLabel("Duration: 00:00:00")
        recording_layout.addWidget(self.recording_duration_label)

        self.frame_count_label = QLabel("Frames: 0")
        recording_layout.addWidget(self.frame_count_label)

        layout.addWidget(recording_group)

        layout.addStretch()

        return panel

    def set_camera_manager(self, camera_manager: CameraManager):
        """Set camera manager instance"""
        self.camera_manager = camera_manager
        logger.info("Camera manager set")

    def set_recorder(self, recorder: MultiStreamRecorder):
        """Set recorder instance"""
        self.recorder = recorder
        logger.info("Recorder set")

    def update_feeds(self):
        """Update camera feeds and metrics"""
        if self.camera_manager is None:
            return

        try:
            # Get synchronized frames
            frames = self.camera_manager.get_synchronized_frames(timeout=0.1)

            if frames and len(frames.frames) > 0:
                # Update feeds
                for i, camera_frame in enumerate(frames.frames):
                    if i < len(self.camera_feeds):
                        # Update frame display
                        self.camera_feeds[i].update_frame(camera_frame.frame)

                        # Update metrics
                        if i < len(self.metrics_widgets):
                            self.metrics_widgets[i].update_metric("FPS", f"{camera_frame.fps:.1f}")
                            self.metrics_widgets[i].update_metric(
                                "Frame Count",
                                str(camera_frame.frame_number)
                            )
                            self.metrics_widgets[i].update_metric(
                                "Resolution",
                                f"{camera_frame.resolution[0]}x{camera_frame.resolution[1]}"
                            )

                # Update sync status
                self.sync_status_label.setText(
                    f"Sync: {frames.time_diff_ms:.1f}ms"
                )

                # Feed frames to recorder if active
                if self.recorder:
                    if self.recorder.is_recording:
                        self.recorder.record_frames(frames)
                    else:
                        # Update circular buffer even when not recording
                        self.recorder.update_circular_buffers(frames)

            # Update camera status labels
            health = self.camera_manager.health_check()
            camera_status_labels = [
                self.cam1_status,
                self.cam2_status,
                self.cam3_status
            ]

            for i, (cam_name, is_healthy) in enumerate(health.items()):
                if i < len(camera_status_labels):
                    status = "Connected" if is_healthy else "Disconnected"
                    color = "#107c10" if is_healthy else "#c42b1c"
                    camera_status_labels[i].setText(f"Status: {status}")
                    camera_status_labels[i].setStyleSheet(f"color: {color};")

            # Update recording status
            if self.recorder:
                status = self.recorder.get_recording_status()
                if status['is_recording']:
                    self.recording_status_label.setText("● RECORDING")
                    self.recording_status_label.setStyleSheet("color: #c42b1c; font-weight: bold;")

                    elapsed = int(status.get('elapsed_seconds', 0))
                    hours = elapsed // 3600
                    minutes = (elapsed % 3600) // 60
                    seconds = elapsed % 60
                    self.recording_duration_label.setText(
                        f"Duration: {hours:02d}:{minutes:02d}:{seconds:02d}"
                    )

                    self.frame_count_label.setText(f"Frames: {status.get('frame_count', 0)}")
                else:
                    self.recording_status_label.setText("Not Recording")
                    self.recording_status_label.setStyleSheet("color: #d4d4d4;")
                    self.recording_duration_label.setText("Duration: 00:00:00")
                    self.frame_count_label.setText("Frames: 0")

        except Exception as e:
            logger.error(f"Error updating feeds: {e}")

    def on_view_mode_changed(self, mode: str):
        """Handle view mode change"""
        logger.info(f"View mode changed to: {mode}")
        # Implementation for different view modes coming in Phase 2
