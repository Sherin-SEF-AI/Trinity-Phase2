"""
Trinity Analytics Dashboard
Main dashboard for real-time metrics and analytics visualization
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QTabWidget, QScrollArea, QLabel, QFrame, QPushButton
    )
    from PyQt6.QtCore import QTimer, Qt
    from PyQt6.QtGui import QFont
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

from loguru import logger

from .metrics_collector import MetricsCollector, MetricType, MetricStatistics
from .visualizations import (
    TimeSeriesChart, HeatmapChart, StatisticsCard,
    SessionComparisonWidget
)


# Re-export MetricType for convenience
__all__ = ['AnalyticsDashboard', 'MetricType']


if PYQT_AVAILABLE:
    class AnalyticsDashboard(QWidget):
        """
        Main analytics dashboard widget

        Features:
        - Real-time metrics visualization
        - Performance monitoring (FPS, latency)
        - Detection statistics
        - Safety metrics
        - Session comparison
        - Historical data analysis
        """

        def __init__(self, metrics_collector: Optional[MetricsCollector] = None, parent=None):
            super().__init__(parent)

            self.metrics_collector = metrics_collector or MetricsCollector()
            self.update_interval_ms = 1000  # Update every second

            # Start metrics aggregation
            if not self.metrics_collector.aggregation_running:
                self.metrics_collector.start_aggregation()

            self._setup_ui()
            self._start_updates()

            logger.info("Analytics dashboard initialized")

        # ====================================================================
        # UI Setup
        # ====================================================================

        def _setup_ui(self):
            """Setup the dashboard UI"""
            layout = QVBoxLayout()
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(10)

            # Title
            title = QLabel("Analytics Dashboard")
            title_font = QFont()
            title_font.setPointSize(16)
            title_font.setBold(True)
            title.setFont(title_font)
            title.setStyleSheet("color: #ecf0f1; padding: 10px;")
            layout.addWidget(title)

            # Tab widget for different sections
            self.tabs = QTabWidget()
            self.tabs.setStyleSheet("""
                QTabWidget::pane {
                    border: 1px solid #34495e;
                    background-color: #1e2a38;
                }
                QTabBar::tab {
                    background-color: #2c3e50;
                    color: #ecf0f1;
                    padding: 10px 20px;
                    border: 1px solid #34495e;
                    border-bottom: none;
                }
                QTabBar::tab:selected {
                    background-color: #3498db;
                    color: white;
                }
                QTabBar::tab:hover {
                    background-color: #34495e;
                }
            """)

            # Add tabs
            self.tabs.addTab(self._create_overview_tab(), "Overview")
            self.tabs.addTab(self._create_performance_tab(), "Performance")
            self.tabs.addTab(self._create_detection_tab(), "Detection")
            self.tabs.addTab(self._create_safety_tab(), "Safety")
            self.tabs.addTab(self._create_sessions_tab(), "Sessions")

            layout.addWidget(self.tabs)

            self.setLayout(layout)
            self.setStyleSheet("background-color: #1e2a38;")

        def _create_overview_tab(self) -> QWidget:
            """Create overview tab with key metrics"""
            tab = QWidget()
            layout = QVBoxLayout()
            layout.setContentsMargins(15, 15, 15, 15)
            layout.setSpacing(15)

            # Statistics cards in grid
            cards_widget = QWidget()
            cards_layout = QGridLayout(cards_widget)
            cards_layout.setSpacing(15)

            # Create cards
            self.fps_card = StatisticsCard("System FPS", "0", "fps")
            self.detections_card = StatisticsCard("Detections", "0")
            self.tracks_card = StatisticsCard("Active Tracks", "0")
            self.events_card = StatisticsCard("Safety Events", "0")
            self.edge_cases_card = StatisticsCard("Edge Cases", "0")
            self.pipeline_time_card = StatisticsCard("Pipeline Time", "0", "ms")

            # Add to grid (2 columns)
            cards_layout.addWidget(self.fps_card, 0, 0)
            cards_layout.addWidget(self.detections_card, 0, 1)
            cards_layout.addWidget(self.tracks_card, 1, 0)
            cards_layout.addWidget(self.events_card, 1, 1)
            cards_layout.addWidget(self.edge_cases_card, 2, 0)
            cards_layout.addWidget(self.pipeline_time_card, 2, 1)

            layout.addWidget(cards_widget)

            # Quick stats section
            stats_label = QLabel("System Statistics")
            stats_label.setStyleSheet("color: #ecf0f1; font-size: 12pt; font-weight: bold; margin-top: 10px;")
            layout.addWidget(stats_label)

            self.stats_text = QLabel("Loading...")
            self.stats_text.setStyleSheet("color: #95a5a6; font-family: monospace; padding: 10px;")
            self.stats_text.setWordWrap(True)
            layout.addWidget(self.stats_text)

            layout.addStretch()

            tab.setLayout(layout)
            return tab

        def _create_performance_tab(self) -> QWidget:
            """Create performance monitoring tab"""
            tab = QWidget()
            layout = QVBoxLayout()
            layout.setContentsMargins(15, 15, 15, 15)
            layout.setSpacing(15)

            # FPS chart
            self.fps_chart = TimeSeriesChart(
                title="System FPS",
                ylabel="FPS",
                time_window=60
            )
            self.fps_chart.add_series("FPS", color='#3498db', width=2)
            layout.addWidget(self.fps_chart, stretch=1)

            # Pipeline time breakdown chart
            self.pipeline_chart = TimeSeriesChart(
                title="Pipeline Time Breakdown",
                ylabel="Time (ms)",
                time_window=60
            )
            self.pipeline_chart.add_series("Detection", color='#e74c3c', width=2)
            self.pipeline_chart.add_series("Tracking", color='#f39c12', width=2)
            self.pipeline_chart.add_series("Total", color='#9b59b6', width=2)
            layout.addWidget(self.pipeline_chart, stretch=1)

            tab.setLayout(layout)
            return tab

        def _create_detection_tab(self) -> QWidget:
            """Create detection statistics tab"""
            tab = QWidget()
            layout = QVBoxLayout()
            layout.setContentsMargins(15, 15, 15, 15)
            layout.setSpacing(15)

            # Detections over time
            self.detections_chart = TimeSeriesChart(
                title="Detections Over Time",
                ylabel="Count",
                time_window=120
            )
            self.detections_chart.add_series("Detections", color='#3498db', width=2)
            self.detections_chart.add_series("Tracks", color='#2ecc71', width=2)
            layout.addWidget(self.detections_chart, stretch=1)

            # Detection heatmap
            self.detection_heatmap = HeatmapChart(
                title="Detection Spatial Distribution",
                grid_size=(20, 20)
            )
            layout.addWidget(self.detection_heatmap, stretch=1)

            tab.setLayout(layout)
            return tab

        def _create_safety_tab(self) -> QWidget:
            """Create safety metrics tab"""
            tab = QWidget()
            layout = QVBoxLayout()
            layout.setContentsMargins(15, 15, 15, 15)
            layout.setSpacing(15)

            # Safety cards
            safety_cards = QWidget()
            safety_layout = QGridLayout(safety_cards)
            safety_layout.setSpacing(15)

            self.min_ttc_card = StatisticsCard("Minimum TTC", "N/A", "s")
            self.near_miss_card = StatisticsCard("Near Misses", "0")
            self.total_events_card = StatisticsCard("Total Events", "0")

            safety_layout.addWidget(self.min_ttc_card, 0, 0)
            safety_layout.addWidget(self.near_miss_card, 0, 1)
            safety_layout.addWidget(self.total_events_card, 0, 2)

            layout.addWidget(safety_cards)

            # Safety events over time
            self.events_chart = TimeSeriesChart(
                title="Safety Events Over Time",
                ylabel="Count",
                time_window=300  # 5 minutes
            )
            self.events_chart.add_series("Events", color='#e74c3c', width=2)
            self.events_chart.add_series("Edge Cases", color='#f39c12', width=2)
            layout.addWidget(self.events_chart, stretch=1)

            # TTC chart
            self.ttc_chart = TimeSeriesChart(
                title="Time-to-Collision (TTC)",
                ylabel="TTC (s)",
                time_window=120
            )
            self.ttc_chart.add_series("Min TTC", color='#e74c3c', width=2)
            layout.addWidget(self.ttc_chart, stretch=1)

            tab.setLayout(layout)
            return tab

        def _create_sessions_tab(self) -> QWidget:
            """Create sessions comparison tab"""
            tab = QWidget()
            layout = QVBoxLayout()
            layout.setContentsMargins(15, 15, 15, 15)
            layout.setSpacing(15)

            # Session comparison widget
            self.session_comparison = SessionComparisonWidget()
            layout.addWidget(self.session_comparison)

            # Placeholder for session list
            sessions_label = QLabel("Session History")
            sessions_label.setStyleSheet("color: #ecf0f1; font-size: 12pt; font-weight: bold;")
            layout.addWidget(sessions_label)

            self.sessions_text = QLabel("No previous sessions loaded")
            self.sessions_text.setStyleSheet("color: #95a5a6; padding: 10px;")
            layout.addWidget(self.sessions_text)

            layout.addStretch()

            tab.setLayout(layout)
            return tab

        # ====================================================================
        # Update Methods
        # ====================================================================

        def _start_updates(self):
            """Start periodic updates"""
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self._update_all)
            self.update_timer.start(self.update_interval_ms)

        def _update_all(self):
            """Update all dashboard components"""
            try:
                self._update_overview()
                self._update_performance()
                self._update_detection()
                self._update_safety()
            except Exception as e:
                logger.error(f"Error updating dashboard: {e}")

        def _update_overview(self):
            """Update overview tab"""
            # Update statistic cards
            latest_fps = self.metrics_collector.get_latest(MetricType.FPS)
            if latest_fps is not None:
                self.fps_card.set_value(latest_fps)

            latest_detections = self.metrics_collector.get_latest(MetricType.DETECTIONS_COUNT)
            if latest_detections is not None:
                self.detections_card.set_value(int(latest_detections))

            latest_tracks = self.metrics_collector.get_latest(MetricType.TRACKS_COUNT)
            if latest_tracks is not None:
                self.tracks_card.set_value(int(latest_tracks))

            latest_events = self.metrics_collector.get_latest(MetricType.EVENTS_COUNT)
            if latest_events is not None:
                self.events_card.set_value(int(latest_events))

            latest_edge_cases = self.metrics_collector.get_latest(MetricType.EDGE_CASES_COUNT)
            if latest_edge_cases is not None:
                self.edge_cases_card.set_value(int(latest_edge_cases))

            latest_pipeline_time = self.metrics_collector.get_latest(MetricType.TOTAL_PIPELINE_TIME)
            if latest_pipeline_time is not None:
                self.pipeline_time_card.set_value(latest_pipeline_time)

            # Update statistics text
            stats = self.metrics_collector.get_all_statistics(seconds=60)
            if stats:
                stats_lines = ["System Statistics (Last 60s):"]
                for metric_type, stat in stats.items():
                    name = metric_type.value.replace('_', ' ').title()
                    stats_lines.append(
                        f"{name:30s}: "
                        f"Mean={stat.mean:8.2f}, "
                        f"Min={stat.min:8.2f}, "
                        f"Max={stat.max:8.2f}"
                    )
                self.stats_text.setText("\n".join(stats_lines))

        def _update_performance(self):
            """Update performance tab"""
            # Update FPS chart
            timestamps, values = self.metrics_collector.get_time_series(
                MetricType.FPS
            )
            if timestamps:
                self.fps_chart.update_series("FPS", timestamps, values)

            # Update pipeline chart
            det_ts, det_vals = self.metrics_collector.get_time_series(MetricType.DETECTION_TIME)
            trk_ts, trk_vals = self.metrics_collector.get_time_series(MetricType.TRACKING_TIME)
            tot_ts, tot_vals = self.metrics_collector.get_time_series(MetricType.TOTAL_PIPELINE_TIME)

            if det_ts:
                self.pipeline_chart.update_series("Detection", det_ts, det_vals)
            if trk_ts:
                self.pipeline_chart.update_series("Tracking", trk_ts, trk_vals)
            if tot_ts:
                self.pipeline_chart.update_series("Total", tot_ts, tot_vals)

        def _update_detection(self):
            """Update detection tab"""
            # Update detections chart
            det_ts, det_vals = self.metrics_collector.get_time_series(MetricType.DETECTIONS_COUNT)
            trk_ts, trk_vals = self.metrics_collector.get_time_series(MetricType.TRACKS_COUNT)

            if det_ts:
                self.detections_chart.update_series("Detections", det_ts, det_vals)
            if trk_ts:
                self.detections_chart.update_series("Tracks", trk_ts, trk_vals)

        def _update_safety(self):
            """Update safety tab"""
            # Update safety cards
            latest_ttc = self.metrics_collector.get_latest(MetricType.MIN_TTC)
            if latest_ttc is not None:
                self.min_ttc_card.set_value(latest_ttc)
                # Color code based on TTC
                if latest_ttc < 2.0:
                    self.min_ttc_card.set_color('#e74c3c')  # Red - critical
                elif latest_ttc < 4.0:
                    self.min_ttc_card.set_color('#f39c12')  # Orange - warning
                else:
                    self.min_ttc_card.set_color('#27ae60')  # Green - safe

            latest_near_miss = self.metrics_collector.get_latest(MetricType.NEAR_MISS_COUNT)
            if latest_near_miss is not None:
                self.near_miss_card.set_value(int(latest_near_miss))

            latest_events = self.metrics_collector.get_latest(MetricType.EVENTS_COUNT)
            if latest_events is not None:
                self.total_events_card.set_value(int(latest_events))

            # Update events chart
            evt_ts, evt_vals = self.metrics_collector.get_time_series(MetricType.EVENTS_COUNT)
            edg_ts, edg_vals = self.metrics_collector.get_time_series(MetricType.EDGE_CASES_COUNT)

            if evt_ts:
                self.events_chart.update_series("Events", evt_ts, evt_vals)
            if edg_ts:
                self.events_chart.update_series("Edge Cases", edg_ts, edg_vals)

            # Update TTC chart
            ttc_ts, ttc_vals = self.metrics_collector.get_time_series(MetricType.MIN_TTC)
            if ttc_ts:
                self.ttc_chart.update_series("Min TTC", ttc_ts, ttc_vals)

        # ====================================================================
        # Public Methods
        # ====================================================================

        def record_metrics(self, metrics: Dict[MetricType, float]):
            """
            Record a batch of metrics

            Args:
                metrics: Dictionary of {metric_type: value}
            """
            self.metrics_collector.record_batch(metrics)

        def clear_metrics(self):
            """Clear all metrics data"""
            self.metrics_collector.clear()
            logger.info("Dashboard metrics cleared")

        def set_update_interval(self, interval_ms: int):
            """
            Set dashboard update interval

            Args:
                interval_ms: Update interval in milliseconds
            """
            self.update_interval_ms = interval_ms
            self.update_timer.setInterval(interval_ms)

        def cleanup(self):
            """Cleanup dashboard resources"""
            if hasattr(self, 'update_timer'):
                self.update_timer.stop()

            if self.metrics_collector.aggregation_running:
                self.metrics_collector.stop_aggregation()

            logger.info("Dashboard cleanup complete")

else:
    # Fallback if PyQt6 not available
    class AnalyticsDashboard:
        """Fallback dashboard (no GUI)"""

        def __init__(self, metrics_collector: Optional[MetricsCollector] = None, parent=None):
            self.metrics_collector = metrics_collector or MetricsCollector()
            logger.warning("PyQt6 not available - dashboard GUI disabled")

        def record_metrics(self, metrics: Dict[MetricType, float]):
            self.metrics_collector.record_batch(metrics)

        def clear_metrics(self):
            self.metrics_collector.clear()

        def set_update_interval(self, interval_ms: int):
            pass

        def cleanup(self):
            if self.metrics_collector.aggregation_running:
                self.metrics_collector.stop_aggregation()
