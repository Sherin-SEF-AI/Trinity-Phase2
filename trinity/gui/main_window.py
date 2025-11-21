"""
Trinity Phase 2 - Main Window
PyQt6 main application window with tabbed interface
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QStatusBar, QToolBar, QSplitter,
    QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QAction, QIcon, QFont
from loguru import logger

from trinity.core.config import Config
from trinity.core.camera_manager import CameraManager
from trinity.core.recorder import MultiStreamRecorder
from trinity.database.init_db import DatabaseManager


class MainWindow(QMainWindow):
    """
    Trinity Phase 2 Main Application Window
    """

    # Signals
    session_started = pyqtSignal(int)
    session_stopped = pyqtSignal()
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()

    def __init__(self, config: Optional[Dict] = None):
        super().__init__()

        # Load configuration
        if config is None:
            self.config_manager = Config()
            self.config = self.config_manager.get_all()
        else:
            self.config = config

        # Initialize managers
        self.camera_manager: Optional[CameraManager] = None
        self.recorder: Optional[MultiStreamRecorder] = None
        self.db_manager: Optional[DatabaseManager] = None

        # Application state
        self.current_session_id: Optional[int] = None
        self.is_session_active = False

        # Setup UI
        self.init_ui()
        self.load_stylesheet()
        self.setup_connections()

        # Start update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(100)  # Update every 100ms

        logger.info("Main window initialized")

    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("Trinity Phase 2 - Autonomous Vehicle Testing Platform")
        self.setGeometry(100, 100, 1600, 900)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create header
        header = self.create_header()
        main_layout.addWidget(header)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        main_layout.addWidget(self.tab_widget)

        # Add tabs (placeholders for now)
        self.create_tabs()

        # Create status bar
        self.create_status_bar()

        # Create menu bar
        self.create_menu_bar()

        # Create toolbar
        self.create_toolbar()

    def create_header(self) -> QWidget:
        """Create application header with controls"""
        header = QWidget()
        header.setObjectName("header")
        header.setMinimumHeight(80)
        header.setMaximumHeight(80)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)

        # Left side - Title and status
        left_layout = QVBoxLayout()

        title_label = QLabel("Trinity Phase 2")
        title_label.setObjectName("headerLabel")
        title_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        left_layout.addWidget(title_label)

        self.session_label = QLabel("No Active Session")
        self.session_label.setObjectName("subtitleLabel")
        left_layout.addWidget(self.session_label)

        layout.addLayout(left_layout)
        layout.addStretch()

        # Right side - Quick controls
        self.start_session_btn = QPushButton("Start Session")
        self.start_session_btn.setObjectName("successButton")
        self.start_session_btn.setFixedSize(140, 40)
        self.start_session_btn.clicked.connect(self.start_session)
        layout.addWidget(self.start_session_btn)

        self.stop_session_btn = QPushButton("Stop Session")
        self.stop_session_btn.setObjectName("dangerButton")
        self.stop_session_btn.setFixedSize(140, 40)
        self.stop_session_btn.setEnabled(False)
        self.stop_session_btn.clicked.connect(self.stop_session)
        layout.addWidget(self.stop_session_btn)

        self.record_btn = QPushButton("● Record")
        self.record_btn.setFixedSize(120, 40)
        self.record_btn.setEnabled(False)
        self.record_btn.clicked.connect(self.toggle_recording)
        layout.addWidget(self.record_btn)

        return header

    def create_tabs(self):
        """Create all application tabs"""
        # Tab 1: Live Monitoring
        from trinity.gui.tabs.live_monitoring import LiveMonitoringTab
        self.live_tab = LiveMonitoringTab(self.config)
        self.tab_widget.addTab(self.live_tab, "Live Monitoring")

        # Tab 2: Scenario Testing (placeholder)
        scenario_tab = QWidget()
        scenario_layout = QVBoxLayout(scenario_tab)
        scenario_layout.addWidget(QLabel("Scenario Testing - Coming Soon"))
        self.tab_widget.addTab(scenario_tab, "Scenario Testing")

        # Tab 3: Object Tracking (placeholder)
        tracking_tab = QWidget()
        tracking_layout = QVBoxLayout(tracking_tab)
        tracking_layout.addWidget(QLabel("Object Tracking & Analysis - Coming Soon"))
        self.tab_widget.addTab(tracking_tab, "Object Tracking")

        # Tab 4: AV Performance (placeholder)
        av_tab = QWidget()
        av_layout = QVBoxLayout(av_tab)
        av_layout.addWidget(QLabel("AV Performance Validation - Coming Soon"))
        self.tab_widget.addTab(av_tab, "AV Performance")

        # Tab 5: Edge Cases (placeholder)
        edge_tab = QWidget()
        edge_layout = QVBoxLayout(edge_tab)
        edge_layout.addWidget(QLabel("Edge Case Explorer - Coming Soon"))
        self.tab_widget.addTab(edge_tab, "Edge Cases")

        # Tab 6: Dataset Management (placeholder)
        dataset_tab = QWidget()
        dataset_layout = QVBoxLayout(dataset_tab)
        dataset_layout.addWidget(QLabel("Dataset Management - Coming Soon"))
        self.tab_widget.addTab(dataset_tab, "Datasets")

        # Tab 7: CARLA Integration (placeholder)
        carla_tab = QWidget()
        carla_layout = QVBoxLayout(carla_tab)
        carla_layout.addWidget(QLabel("CARLA Integration - Coming Soon"))
        self.tab_widget.addTab(carla_tab, "CARLA")

        # Tab 8: Analytics (placeholder)
        analytics_tab = QWidget()
        analytics_layout = QVBoxLayout(analytics_tab)
        analytics_layout.addWidget(QLabel("Analytics & Reports - Coming Soon"))
        self.tab_widget.addTab(analytics_tab, "Analytics")

        # Tab 9: Settings (placeholder)
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.addWidget(QLabel("System Configuration - Coming Soon"))
        self.tab_widget.addTab(settings_tab, "Settings")

    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # FPS indicator
        self.fps_label = QLabel("FPS: 0.0")
        self.status_bar.addPermanentWidget(self.fps_label)

        # Recording indicator
        self.recording_label = QLabel("● REC")
        self.recording_label.setVisible(False)
        self.status_bar.addPermanentWidget(self.recording_label)

        # Camera status
        self.camera_status_label = QLabel("Cameras: 0/3")
        self.status_bar.addPermanentWidget(self.camera_status_label)

        # Database status
        self.db_status_label = QLabel("DB: Disconnected")
        self.status_bar.addPermanentWidget(self.db_status_label)

        self.status_bar.showMessage("Ready")

    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        new_session_action = QAction("&New Session", self)
        new_session_action.setShortcut("Ctrl+N")
        new_session_action.triggered.connect(self.start_session)
        file_menu.addAction(new_session_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        fullscreen_action = QAction("&Fullscreen", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.setCheckable(True)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        calibrate_action = QAction("&Camera Calibration", self)
        calibrate_action.triggered.connect(self.open_calibration)
        tools_menu.addAction(calibrate_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_toolbar(self):
        """Create toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Add actions
        start_action = QAction("Start", self)
        start_action.triggered.connect(self.start_session)
        toolbar.addAction(start_action)

        stop_action = QAction("Stop", self)
        stop_action.triggered.connect(self.stop_session)
        toolbar.addAction(stop_action)

        toolbar.addSeparator()

        record_action = QAction("Record", self)
        record_action.triggered.connect(self.toggle_recording)
        toolbar.addAction(record_action)

    def load_stylesheet(self):
        """Load and apply stylesheet"""
        style_path = Path(__file__).parent / "styles" / "dark_theme.qss"
        if style_path.exists():
            with open(style_path, 'r') as f:
                self.setStyleSheet(f.read())
            logger.info("Stylesheet loaded")
        else:
            logger.warning(f"Stylesheet not found: {style_path}")

    def setup_connections(self):
        """Setup signal/slot connections"""
        # Connect signals
        self.session_started.connect(self.on_session_started)
        self.session_stopped.connect(self.on_session_stopped)
        self.recording_started.connect(self.on_recording_started)
        self.recording_stopped.connect(self.on_recording_stopped)

    def start_session(self):
        """Start a new test session"""
        try:
            # Initialize database if needed
            if self.db_manager is None:
                self.db_manager = DatabaseManager(self.config)

            # Initialize camera manager
            if self.camera_manager is None:
                self.camera_manager = CameraManager(self.config)
                self.camera_manager.start()

            # Initialize recorder
            if self.recorder is None:
                self.recorder = MultiStreamRecorder(self.config)
                # Initialize circular buffers
                camera_names = [cam.name for cam in self.camera_manager.cameras]
                self.recorder.initialize_circular_buffers(
                    camera_names,
                    fps=self.config.get('cameras', {}).get('camera_1', {}).get('fps', 30)
                )

            # Create session in database
            from trinity.database.queries import create_test_session
            db_session = self.db_manager.get_session()

            test_session = create_test_session(
                db_session,
                name=f"Session {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                test_type="free_roam",
                description="Test session"
            )

            self.current_session_id = test_session.id
            self.is_session_active = True

            # Update UI
            self.session_started.emit(self.current_session_id)

            # Pass camera manager to live tab
            if hasattr(self, 'live_tab'):
                self.live_tab.set_camera_manager(self.camera_manager)
                self.live_tab.set_recorder(self.recorder)

            logger.success(f"Session started: ID {self.current_session_id}")

        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start session:\n{e}")

    def stop_session(self):
        """Stop current test session"""
        try:
            if self.current_session_id is None:
                return

            # Stop recording if active
            if self.recorder and self.recorder.is_recording:
                self.recorder.stop_recording()

            # End session in database
            from trinity.database.queries import end_test_session
            db_session = self.db_manager.get_session()
            end_test_session(db_session, self.current_session_id)

            self.is_session_active = False
            self.current_session_id = None

            # Update UI
            self.session_stopped.emit()

            logger.success("Session stopped")

        except Exception as e:
            logger.error(f"Failed to stop session: {e}")
            QMessageBox.critical(self, "Error", f"Failed to stop session:\n{e}")

    def toggle_recording(self):
        """Toggle recording on/off"""
        if self.recorder is None:
            return

        try:
            if not self.recorder.is_recording:
                # Get current frames
                frames = self.camera_manager.get_synchronized_frames(timeout=1.0)
                if frames:
                    self.recorder.start_recording(
                        session_id=self.current_session_id,
                        camera_frames=frames
                    )
                    self.recording_started.emit()
            else:
                self.recorder.stop_recording()
                self.recording_stopped.emit()

        except Exception as e:
            logger.error(f"Recording error: {e}")
            QMessageBox.critical(self, "Error", f"Recording error:\n{e}")

    def update_status(self):
        """Update status bar and metrics"""
        # Update camera status
        if self.camera_manager:
            health = self.camera_manager.health_check()
            healthy_count = sum(1 for h in health.values() if h)
            total_count = len(health)
            self.camera_status_label.setText(f"Cameras: {healthy_count}/{total_count}")

            # Update FPS
            if self.camera_manager.cameras:
                avg_fps = sum(c.actual_fps for c in self.camera_manager.cameras) / len(self.camera_manager.cameras)
                self.fps_label.setText(f"FPS: {avg_fps:.1f}")

        # Update database status
        if self.db_manager:
            self.db_status_label.setText("DB: Connected")

    def on_session_started(self, session_id: int):
        """Handle session started event"""
        self.session_label.setText(f"Session ID: {session_id}")
        self.start_session_btn.setEnabled(False)
        self.stop_session_btn.setEnabled(True)
        self.record_btn.setEnabled(True)
        self.status_bar.showMessage(f"Session {session_id} started")

    def on_session_stopped(self):
        """Handle session stopped event"""
        self.session_label.setText("No Active Session")
        self.start_session_btn.setEnabled(True)
        self.stop_session_btn.setEnabled(False)
        self.record_btn.setEnabled(False)
        self.status_bar.showMessage("Session stopped")

    def on_recording_started(self):
        """Handle recording started event"""
        self.record_btn.setText("■ Stop")
        self.record_btn.setObjectName("dangerButton")
        self.record_btn.setStyleSheet("")  # Force style refresh
        self.recording_label.setVisible(True)
        self.status_bar.showMessage("Recording...")

    def on_recording_stopped(self):
        """Handle recording stopped event"""
        self.record_btn.setText("● Record")
        self.record_btn.setObjectName("")
        self.record_btn.setStyleSheet("")  # Force style refresh
        self.recording_label.setVisible(False)
        self.status_bar.showMessage("Recording stopped")

    def toggle_fullscreen(self, checked: bool):
        """Toggle fullscreen mode"""
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def open_calibration(self):
        """Open camera calibration dialog"""
        QMessageBox.information(
            self,
            "Camera Calibration",
            "Camera calibration tool coming soon!\n\n"
            "For now, use the CLI tool:\n"
            "python -m trinity.core.calibration"
        )

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About Trinity Phase 2",
            "<h2>Trinity Phase 2</h2>"
            "<p>Autonomous Vehicle Testing & Validation Suite</p>"
            "<p>Version 1.0.0</p>"
            "<p>© 2025 Sherin-SEF-AI</p>"
            "<p><a href='https://github.com/Sherin-SEF-AI/Trinity-Phase2'>GitHub Repository</a></p>"
        )

    def closeEvent(self, event):
        """Handle window close event"""
        if self.is_session_active:
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "A session is active. Stop session and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.stop_session()
                event.accept()
            else:
                event.ignore()
                return

        # Cleanup
        if self.camera_manager:
            self.camera_manager.stop()

        if self.recorder and self.recorder.is_recording:
            self.recorder.stop_recording()

        event.accept()
        logger.info("Application closed")


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Trinity Phase 2")
    app.setOrganizationName("Sherin-SEF-AI")

    # Setup logging
    from trinity.utils.logger import setup_logger
    from trinity.core.config import load_config

    config = load_config()
    setup_logger(config)

    # Create and show main window
    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
