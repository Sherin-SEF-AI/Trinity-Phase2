"""
Trinity Analytics Visualizations
PyQt6-based visualization components for the analytics dashboard
"""

from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import numpy as np

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QFrame, QSizePolicy, QGridLayout
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal
    from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False

from loguru import logger


# ============================================================================
# Base Classes
# ============================================================================

if PYQT_AVAILABLE:
    class BaseChartWidget(QWidget):
        """Base class for chart widgets"""

        def __init__(self, title: str = "", parent=None):
            super().__init__(parent)
            self.title = title
            self._setup_ui()

        def _setup_ui(self):
            """Setup the widget UI"""
            layout = QVBoxLayout()
            layout.setContentsMargins(10, 10, 10, 10)

            # Title
            if self.title:
                title_label = QLabel(self.title)
                title_font = QFont()
                title_font.setPointSize(12)
                title_font.setBold(True)
                title_label.setFont(title_font)
                title_label.setStyleSheet("color: #ecf0f1;")
                layout.addWidget(title_label)

            # Frame for content
            self.content_frame = QFrame()
            self.content_frame.setStyleSheet("""
                QFrame {
                    background-color: #2c3e50;
                    border: 1px solid #34495e;
                    border-radius: 5px;
                }
            """)
            self.content_layout = QVBoxLayout(self.content_frame)
            self.content_layout.setContentsMargins(5, 5, 5, 5)

            layout.addWidget(self.content_frame)
            self.setLayout(layout)

        def clear(self):
            """Clear the chart"""
            pass


# ============================================================================
# Time Series Chart
# ============================================================================

if PYQT_AVAILABLE and PYQTGRAPH_AVAILABLE:
    class TimeSeriesChart(BaseChartWidget):
        """
        Real-time time series chart using pyqtgraph

        Features:
        - Multiple series support
        - Auto-scaling
        - Customizable colors
        - Real-time updates
        - Configurable time window
        """

        def __init__(
            self,
            title: str = "Time Series",
            ylabel: str = "Value",
            time_window: int = 60,  # seconds
            parent=None
        ):
            self.ylabel = ylabel
            self.time_window = time_window
            self.series_data: Dict[str, Tuple[List, List]] = {}  # {name: (times, values)}
            self.series_colors: Dict[str, str] = {}
            self.plot_items: Dict[str, Any] = {}

            super().__init__(title, parent)

        def _setup_ui(self):
            """Setup the chart UI"""
            super()._setup_ui()

            # Create plot widget
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.setBackground('#2c3e50')
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            self.plot_widget.setLabel('left', self.ylabel, color='#ecf0f1')
            self.plot_widget.setLabel('bottom', 'Time (s)', color='#ecf0f1')

            # Style axes
            axis_pen = pg.mkPen(color='#ecf0f1', width=1)
            self.plot_widget.getAxis('left').setPen(axis_pen)
            self.plot_widget.getAxis('bottom').setPen(axis_pen)

            self.content_layout.addWidget(self.plot_widget)

        def add_series(
            self,
            name: str,
            color: str = '#3498db',
            width: int = 2
        ):
            """
            Add a new series to the chart

            Args:
                name: Series name
                color: Line color (hex)
                width: Line width
            """
            self.series_data[name] = ([], [])
            self.series_colors[name] = color

            # Create plot item
            pen = pg.mkPen(color=color, width=width)
            plot_item = self.plot_widget.plot([], [], pen=pen, name=name)
            self.plot_items[name] = plot_item

        def update_series(
            self,
            name: str,
            timestamps: List[datetime],
            values: List[float]
        ):
            """
            Update a series with new data

            Args:
                name: Series name
                timestamps: List of timestamps
                values: List of values
            """
            if name not in self.series_data:
                self.add_series(name)

            # Convert timestamps to seconds relative to now
            if timestamps:
                now = datetime.now()
                times = [(now - ts).total_seconds() for ts in timestamps]
                times = [-t for t in times]  # Negative = past

                # Keep only data within time window
                cutoff = -self.time_window
                filtered_times = []
                filtered_values = []

                for t, v in zip(times, values):
                    if t >= cutoff:
                        filtered_times.append(t)
                        filtered_values.append(v)

                # Update series data
                self.series_data[name] = (filtered_times, filtered_values)

                # Update plot
                if name in self.plot_items:
                    self.plot_items[name].setData(filtered_times, filtered_values)

        def clear(self):
            """Clear all series"""
            for name in list(self.series_data.keys()):
                self.series_data[name] = ([], [])
                if name in self.plot_items:
                    self.plot_items[name].setData([], [])

elif PYQT_AVAILABLE:
    # Fallback if pyqtgraph not available
    class TimeSeriesChart(BaseChartWidget):
        """Fallback time series chart (basic implementation)"""

        def __init__(self, title: str = "Time Series", ylabel: str = "Value",
                     time_window: int = 60, parent=None):
            super().__init__(title, parent)
            label = QLabel("PyQtGraph not available - time series visualization disabled")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(label)

        def add_series(self, name: str, color: str = '#3498db', width: int = 2):
            pass

        def update_series(self, name: str, timestamps: List[datetime], values: List[float]):
            pass


# ============================================================================
# Heatmap Chart
# ============================================================================

if PYQT_AVAILABLE:
    class HeatmapChart(BaseChartWidget):
        """
        Heatmap visualization for spatial data

        Features:
        - 2D grid-based heatmap
        - Customizable resolution
        - Color mapping
        - Real-time updates
        """

        def __init__(
            self,
            title: str = "Heatmap",
            grid_size: Tuple[int, int] = (20, 20),
            parent=None
        ):
            self.grid_size = grid_size
            self.data = np.zeros(grid_size)
            self.color_map = 'hot'  # Matplotlib colormap name

            super().__init__(title, parent)

        def _setup_ui(self):
            """Setup the heatmap UI"""
            super()._setup_ui()

            # Create canvas for heatmap
            self.canvas = HeatmapCanvas(self.grid_size)
            self.content_layout.addWidget(self.canvas)

        def update_data(self, data: np.ndarray):
            """
            Update heatmap data

            Args:
                data: 2D numpy array matching grid_size
            """
            if data.shape != self.grid_size:
                logger.warning(f"Data shape {data.shape} doesn't match grid {self.grid_size}")
                return

            self.data = data
            self.canvas.set_data(data)
            self.canvas.update()

        def clear(self):
            """Clear heatmap"""
            self.data = np.zeros(self.grid_size)
            self.canvas.set_data(self.data)
            self.canvas.update()


    class HeatmapCanvas(QWidget):
        """Canvas widget for drawing heatmap"""

        def __init__(self, grid_size: Tuple[int, int], parent=None):
            super().__init__(parent)
            self.grid_size = grid_size
            self.data = np.zeros(grid_size)
            self.setMinimumSize(400, 400)

        def set_data(self, data: np.ndarray):
            """Set heatmap data"""
            self.data = data

        def paintEvent(self, event):
            """Paint the heatmap"""
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            width = self.width()
            height = self.height()

            rows, cols = self.grid_size
            cell_width = width / cols
            cell_height = height / rows

            # Normalize data to 0-1
            data_min = self.data.min()
            data_max = self.data.max()

            if data_max > data_min:
                normalized = (self.data - data_min) / (data_max - data_min)
            else:
                normalized = np.zeros_like(self.data)

            # Draw cells
            for i in range(rows):
                for j in range(cols):
                    value = normalized[i, j]

                    # Color mapping (simple hot colormap)
                    if value < 0.33:
                        # Black to red
                        r = int(value * 3 * 255)
                        g = 0
                        b = 0
                    elif value < 0.66:
                        # Red to yellow
                        r = 255
                        g = int((value - 0.33) * 3 * 255)
                        b = 0
                    else:
                        # Yellow to white
                        r = 255
                        g = 255
                        b = int((value - 0.66) * 3 * 255)

                    color = QColor(r, g, b)
                    brush = QBrush(color)
                    painter.setBrush(brush)
                    painter.setPen(QPen(Qt.PenStyle.NoPen))

                    x = j * cell_width
                    y = i * cell_height

                    painter.drawRect(int(x), int(y), int(cell_width), int(cell_height))


# ============================================================================
# Statistics Card
# ============================================================================

if PYQT_AVAILABLE:
    class StatisticsCard(QWidget):
        """
        Displays a single statistic with label and value

        Features:
        - Large value display
        - Optional delta/change indicator
        - Color coding
        - Unit support
        """

        def __init__(
            self,
            label: str,
            initial_value: str = "0",
            unit: str = "",
            parent=None
        ):
            super().__init__(parent)
            self.label_text = label
            self.unit = unit
            self._setup_ui()
            self.set_value(initial_value)

        def _setup_ui(self):
            """Setup the card UI"""
            layout = QVBoxLayout()
            layout.setContentsMargins(15, 15, 15, 15)
            layout.setSpacing(10)

            # Container frame
            frame = QFrame()
            frame.setStyleSheet("""
                QFrame {
                    background-color: #2c3e50;
                    border: 1px solid #34495e;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)

            frame_layout = QVBoxLayout(frame)
            frame_layout.setSpacing(5)

            # Label
            self.label = QLabel(self.label_text)
            self.label.setStyleSheet("""
                QLabel {
                    color: #95a5a6;
                    font-size: 11pt;
                }
            """)
            self.label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            frame_layout.addWidget(self.label)

            # Value
            self.value = QLabel("0")
            self.value.setStyleSheet("""
                QLabel {
                    color: #ecf0f1;
                    font-size: 24pt;
                    font-weight: bold;
                }
            """)
            self.value.setAlignment(Qt.AlignmentFlag.AlignLeft)
            frame_layout.addWidget(self.value)

            # Delta (optional)
            self.delta = QLabel("")
            self.delta.setStyleSheet("""
                QLabel {
                    color: #95a5a6;
                    font-size: 9pt;
                }
            """)
            self.delta.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.delta.setVisible(False)
            frame_layout.addWidget(self.delta)

            layout.addWidget(frame)
            self.setLayout(layout)

            # Set size policy
            self.setSizePolicy(
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Fixed
            )

        def set_value(self, value: Any, delta: Optional[float] = None):
            """
            Set the value displayed on the card

            Args:
                value: Value to display (will be converted to string)
                delta: Optional delta/change value
            """
            # Format value
            if isinstance(value, float):
                if abs(value) >= 1000:
                    value_str = f"{value:,.0f}"
                elif abs(value) >= 10:
                    value_str = f"{value:.1f}"
                else:
                    value_str = f"{value:.2f}"
            else:
                value_str = str(value)

            # Add unit
            if self.unit:
                value_str = f"{value_str} {self.unit}"

            self.value.setText(value_str)

            # Update delta if provided
            if delta is not None:
                self.set_delta(delta)

        def set_delta(self, delta: float):
            """
            Set delta/change indicator

            Args:
                delta: Change value (positive = increase, negative = decrease)
            """
            if delta > 0:
                delta_str = f"² {delta:+.1f}"
                color = "#27ae60"  # Green
            elif delta < 0:
                delta_str = f"¼ {delta:+.1f}"
                color = "#e74c3c"  # Red
            else:
                delta_str = "  0.0"
                color = "#95a5a6"  # Gray

            self.delta.setText(delta_str)
            self.delta.setStyleSheet(f"QLabel {{ color: {color}; font-size: 9pt; }}")
            self.delta.setVisible(True)

        def set_color(self, color: str):
            """
            Set value color

            Args:
                color: Hex color code
            """
            self.value.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-size: 24pt;
                    font-weight: bold;
                }}
            """)


# ============================================================================
# Session Comparison Widget
# ============================================================================

if PYQT_AVAILABLE:
    class SessionComparisonWidget(QWidget):
        """
        Compare statistics across multiple sessions

        Features:
        - Side-by-side comparison
        - Percentage differences
        - Color-coded improvements/regressions
        """

        def __init__(self, parent=None):
            super().__init__(parent)
            self.sessions: List[Dict[str, Any]] = []
            self._setup_ui()

        def _setup_ui(self):
            """Setup the widget UI"""
            layout = QVBoxLayout()
            layout.setContentsMargins(10, 10, 10, 10)

            # Title
            title = QLabel("Session Comparison")
            title_font = QFont()
            title_font.setPointSize(12)
            title_font.setBold(True)
            title.setFont(title_font)
            title.setStyleSheet("color: #ecf0f1;")
            layout.addWidget(title)

            # Grid for comparison
            self.grid = QGridLayout()
            self.grid.setSpacing(10)

            grid_widget = QWidget()
            grid_widget.setLayout(self.grid)

            layout.addWidget(grid_widget)
            layout.addStretch()

            self.setLayout(layout)

        def set_sessions(self, sessions: List[Dict[str, Any]]):
            """
            Set sessions to compare

            Args:
                sessions: List of session dictionaries with statistics
            """
            self.sessions = sessions
            self._update_comparison()

        def _update_comparison(self):
            """Update comparison display"""
            # Clear existing widgets
            for i in reversed(range(self.grid.count())):
                self.grid.itemAt(i).widget().setParent(None)

            if len(self.sessions) < 2:
                label = QLabel("Add at least 2 sessions to compare")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.grid.addWidget(label, 0, 0)
                return

            # Add headers
            metrics = ['FPS', 'Detections', 'Tracks', 'Events', 'Edge Cases']

            self.grid.addWidget(QLabel("Metric"), 0, 0)

            for col, session in enumerate(self.sessions[:3], 1):  # Max 3 sessions
                header = QLabel(f"Session {session.get('id', col)}")
                header.setStyleSheet("font-weight: bold; color: #3498db;")
                self.grid.addWidget(header, 0, col)

            # Add metrics
            for row, metric in enumerate(metrics, 1):
                label = QLabel(metric)
                label.setStyleSheet("color: #ecf0f1;")
                self.grid.addWidget(label, row, 0)

                for col, session in enumerate(self.sessions[:3], 1):
                    value = session.get(metric.lower(), 0)
                    value_label = QLabel(str(value))
                    value_label.setStyleSheet("color: #ecf0f1;")
                    self.grid.addWidget(value_label, row, col)
