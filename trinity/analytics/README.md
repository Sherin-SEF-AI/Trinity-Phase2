# Trinity Analytics Dashboard

**Phase 5.1** - Real-Time Metrics Visualization and Analytics

---

## Overview

The Trinity Analytics Dashboard provides comprehensive real-time visualization and analysis of system performance, detection metrics, and safety statistics. Built with PyQt6 and PyQtGraph, it offers professional-grade monitoring capabilities for AV testing sessions.

### Key Features

 **Real-Time Metrics** - Live FPS, latency, and performance monitoring
 **Time Series Charts** - Historical data visualization with PyQtGraph
 **Statistics Cards** - Key metrics at-a-glance
 **Heatmaps** - Spatial distribution visualization
 **Session Comparison** - Compare performance across test sessions
 **Automated Aggregation** - Per-second and per-minute data rollup

---

## Quick Start

### Basic Usage

```python
from trinity.analytics import AnalyticsDashboard, MetricsCollector, MetricType

# Create metrics collector
metrics = MetricsCollector(
    retention_seconds=3600,  # Keep 1 hour of data
    max_samples_per_metric=10000
)

# Create dashboard
dashboard = AnalyticsDashboard(metrics_collector=metrics)

# Record metrics
dashboard.record_metrics({
    MetricType.FPS: 30.5,
    MetricType.DETECTIONS_COUNT: 45,
    MetricType.TRACKS_COUNT: 12,
    MetricType.MIN_TTC: 3.5
})
```

### Integration with Main Application

```python
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget
from trinity.analytics import AnalyticsDashboard, MetricsCollector

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Create metrics collector
        self.metrics = MetricsCollector()

        # Create tab widget
        tabs = QTabWidget()

        # Add analytics dashboard as a tab
        self.dashboard = AnalyticsDashboard(self.metrics)
        tabs.addTab(self.dashboard, "Analytics")

        self.setCentralWidget(tabs)

    def update_metrics(self, fps, detections, tracks):
        """Called from main processing loop"""
        self.dashboard.record_metrics({
            MetricType.FPS: fps,
            MetricType.DETECTIONS_COUNT: detections,
            MetricType.TRACKS_COUNT: tracks
        })
```

---

## Metrics Collector

### MetricType Enum

Available metric types:

```python
from trinity.analytics import MetricType

# Performance metrics
MetricType.FPS
MetricType.DETECTION_TIME
MetricType.TRACKING_TIME
MetricType.TOTAL_PIPELINE_TIME

# Detection metrics
MetricType.DETECTIONS_COUNT
MetricType.TRACKS_COUNT

# Safety metrics
MetricType.MIN_TTC
MetricType.NEAR_MISS_COUNT
MetricType.EVENTS_COUNT

# Edge case metrics
MetricType.EDGE_CASES_COUNT

# System metrics
MetricType.CPU_USAGE
MetricType.MEMORY_USAGE
MetricType.GPU_USAGE
MetricType.GPU_MEMORY
```

### Recording Metrics

```python
from trinity.analytics import MetricsCollector, MetricType

collector = MetricsCollector()

# Record single metric
collector.record(MetricType.FPS, 30.5, metadata={'camera': 1})

# Record batch
collector.record_batch({
    MetricType.FPS: 30.5,
    MetricType.DETECTIONS_COUNT: 45,
    MetricType.DETECTION_TIME: 50.2  # milliseconds
})
```

### Retrieving Data

```python
# Get recent samples
samples = collector.get_recent(
    MetricType.FPS,
    seconds=60,  # Last 60 seconds
    limit=100    # Max 100 samples
)

# Get time series
timestamps, values = collector.get_time_series(
    MetricType.FPS,
    start_time=datetime.now() - timedelta(hours=1)
)

# Get aggregated data
timestamps, values = collector.get_aggregated(
    MetricType.FPS,
    period="1s",  # or "1m"
    limit=60
)

# Get statistics
stats = collector.get_statistics(
    MetricType.FPS,
    seconds=60  # Last 60 seconds
)
# Returns: MetricStatistics(count, mean, std, min, max, median, p95, p99)

# Get latest value
latest_fps = collector.get_latest(MetricType.FPS)

# Get all statistics
all_stats = collector.get_all_statistics(seconds=60)
```

### Aggregation

The collector automatically aggregates metrics in the background:

```python
# Start aggregation (happens automatically in dashboard)
collector.start_aggregation()

# Stop aggregation
collector.stop_aggregation()

# Clear data
collector.clear()  # Clear all
collector.clear(MetricType.FPS)  # Clear specific metric
```

---

## Dashboard Components

### Overview Tab

Displays key metrics with statistics cards:
- System FPS
- Detections count
- Active tracks
- Safety events
- Edge cases
- Pipeline time

Shows comprehensive statistics for the last 60 seconds.

### Performance Tab

Real-time performance monitoring:
- **FPS Chart** - System framerate over time
- **Pipeline Breakdown** - Detection, tracking, and total pipeline time

### Detection Tab

Detection statistics visualization:
- **Detections Over Time** - Count of detections and tracks
- **Spatial Heatmap** - Detection distribution across field of view

### Safety Tab

Safety metrics monitoring:
- **Safety Cards** - Min TTC, near misses, total events
- **Events Chart** - Safety events and edge cases over time
- **TTC Chart** - Time-to-collision history

### Sessions Tab

Session comparison and history:
- Compare metrics across multiple sessions
- View historical session data
- Analyze performance trends

---

## Visualization Components

### TimeSeriesChart

Real-time time series visualization:

```python
from trinity.analytics.visualizations import TimeSeriesChart

# Create chart
chart = TimeSeriesChart(
    title="System FPS",
    ylabel="FPS",
    time_window=60  # seconds
)

# Add series
chart.add_series("FPS", color='#3498db', width=2)
chart.add_series("Target", color='#27ae60', width=1)

# Update data
chart.update_series("FPS", timestamps, values)

# Clear
chart.clear()
```

### HeatmapChart

Spatial distribution visualization:

```python
from trinity.analytics.visualizations import HeatmapChart
import numpy as np

# Create heatmap
heatmap = HeatmapChart(
    title="Detection Heatmap",
    grid_size=(20, 20)
)

# Update data
data = np.random.rand(20, 20)  # Your spatial data
heatmap.update_data(data)

# Clear
heatmap.clear()
```

### StatisticsCard

Display single metric with large value:

```python
from trinity.analytics.visualizations import StatisticsCard

# Create card
card = StatisticsCard(
    label="System FPS",
    initial_value="30.5",
    unit="fps"
)

# Update value
card.set_value(32.1)

# Update with delta (change indicator)
card.set_value(32.1, delta=+1.6)  # Green up arrow

# Set color
card.set_color('#27ae60')  # Green
```

---

## Configuration

Add to `config/config.yaml`:

```yaml
analytics:
  enabled: true

  # Metrics collection
  metrics:
    retention_seconds: 3600  # 1 hour
    max_samples_per_metric: 10000
    aggregation_enabled: true

  # Dashboard
  dashboard:
    update_interval_ms: 1000  # Update every second
    default_tab: "overview"  # overview, performance, detection, safety, sessions

  # Chart settings
  charts:
    time_window_seconds: 60
    max_points_per_chart: 1000
    line_width: 2

  # Colors
  colors:
    fps_chart: "#3498db"
    detection_chart: "#2ecc71"
    safety_chart: "#e74c3c"
    edge_case_chart: "#f39c12"
```

---

## Advanced Usage

### Custom Metrics

Create custom metric types:

```python
from trinity.analytics import MetricsCollector, MetricType
from enum import Enum

# Extend MetricType
class CustomMetricType(str, Enum):
    CUSTOM_METRIC = "custom_metric"
    ANOTHER_METRIC = "another_metric"

# Use with collector
collector.record(CustomMetricType.CUSTOM_METRIC, 42.0)
```

### Real-Time Integration

Integrate with processing pipeline:

```python
import time
from trinity.analytics import MetricsCollector, MetricType

class VideoProcessor:
    def __init__(self):
        self.metrics = MetricsCollector()
        self.metrics.start_aggregation()

    def process_frame(self, frame):
        start_time = time.time()

        # Detection
        det_start = time.time()
        detections = self.detector.detect(frame)
        det_time = (time.time() - det_start) * 1000  # ms

        # Tracking
        trk_start = time.time()
        tracks = self.tracker.update(detections)
        trk_time = (time.time() - trk_start) * 1000  # ms

        # Total time
        total_time = (time.time() - start_time) * 1000  # ms
        fps = 1.0 / (time.time() - start_time)

        # Record metrics
        self.metrics.record_batch({
            MetricType.FPS: fps,
            MetricType.DETECTIONS_COUNT: len(detections),
            MetricType.TRACKS_COUNT: len(tracks),
            MetricType.DETECTION_TIME: det_time,
            MetricType.TRACKING_TIME: trk_time,
            MetricType.TOTAL_PIPELINE_TIME: total_time
        })
```

### Export Metrics

Export collected metrics for analysis:

```python
# Get all recent data
metrics_data = {}

for metric_type in collector.get_metric_types():
    timestamps, values = collector.get_time_series(metric_type)
    metrics_data[metric_type.value] = {
        'timestamps': [t.isoformat() for t in timestamps],
        'values': values
    }

# Save to JSON
import json
with open('metrics_export.json', 'w') as f:
    json.dump(metrics_data, f, indent=2)

# Save to CSV
import csv
for metric_type, data in metrics_data.items():
    with open(f'metrics_{metric_type}.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'value'])
        writer.writerows(zip(data['timestamps'], data['values']))
```

---

## Performance

### Memory Usage

The metrics collector uses circular buffers with configurable maximum sizes:

- Default: 10,000 samples per metric
- Memory per metric: ~1-2 MB (depending on metadata)
- Automatic cleanup of old data based on retention period

### Update Frequency

- Dashboard updates: 1000ms (1 Hz) by default
- Aggregation: Every 1 second and 1 minute
- Time series queries: O(n) where n = number of samples
- Statistics calculation: O(n)

### Optimization Tips

1. **Adjust retention period** based on needs:
   ```python
   # Shorter retention = less memory
   collector = MetricsCollector(retention_seconds=600)  # 10 minutes
   ```

2. **Limit samples per metric**:
   ```python
   collector = MetricsCollector(max_samples_per_metric=5000)
   ```

3. **Use aggregated data** for long time ranges:
   ```python
   # Instead of raw samples
   timestamps, values = collector.get_aggregated(
       MetricType.FPS,
       period="1m",  # 1-minute aggregates
       limit=60      # Last hour
   )
   ```

---

## Dependencies

**Required:**
- `PyQt6` - GUI framework
- `numpy` - Numerical operations
- `loguru` - Logging

**Optional:**
- `pyqtgraph` - High-performance charting (highly recommended)

### Install Dependencies

```bash
# Minimal
pip install PyQt6 numpy loguru

# With charting
pip install PyQt6 numpy loguru pyqtgraph
```

---

## Integration Examples

### Complete Application

```python
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget
from trinity.analytics import AnalyticsDashboard, MetricsCollector, MetricType
import sys

class AnalyticsApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trinity Analytics")
        self.setGeometry(100, 100, 1200, 800)

        # Create metrics collector
        self.metrics = MetricsCollector()

        # Create dashboard
        self.dashboard = AnalyticsDashboard(self.metrics)
        self.setCentralWidget(self.dashboard)

    def simulate_metrics(self):
        """Simulate some metrics (for testing)"""
        import random
        self.dashboard.record_metrics({
            MetricType.FPS: 25 + random.random() * 10,
            MetricType.DETECTIONS_COUNT: random.randint(30, 60),
            MetricType.TRACKS_COUNT: random.randint(5, 15),
            MetricType.MIN_TTC: 2.0 + random.random() * 3.0,
            MetricType.EVENTS_COUNT: random.randint(0, 5)
        })

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Set dark style
    app.setStyle('Fusion')

    window = AnalyticsApp()
    window.show()

    # Simulate metrics every second
    from PyQt6.QtCore import QTimer
    timer = QTimer()
    timer.timeout.connect(window.simulate_metrics)
    timer.start(1000)

    sys.exit(app.exec())
```

---

## Troubleshooting

### PyQtGraph Not Available

**Error:** Charts appear as "PyQtGraph not available" placeholders

**Solution:**
```bash
pip install pyqtgraph
```

### High Memory Usage

**Problem:** Dashboard consuming too much memory

**Solutions:**
1. Reduce retention period:
   ```python
   collector = MetricsCollector(retention_seconds=1800)  # 30 min
   ```

2. Limit samples:
   ```python
   collector = MetricsCollector(max_samples_per_metric=5000)
   ```

3. Clear old data periodically:
   ```python
   collector.clear()
   ```

### Slow Performance

**Problem:** Dashboard updates causing lag

**Solutions:**
1. Increase update interval:
   ```python
   dashboard.set_update_interval(2000)  # 2 seconds
   ```

2. Use aggregated data:
   ```python
   timestamps, values = collector.get_aggregated(
       MetricType.FPS,
       period="1s"
   )
   ```

---

## File Structure

```
trinity/analytics/
   __init__.py              # Package exports
   metrics_collector.py     # Metrics collection engine (~550 lines)
   visualizations.py        # Chart components (~450 lines)
   dashboard.py             # Main dashboard (~500 lines)
   README.md               # This file
```

**Total Code:** ~1,500 lines

---

## API Reference

### MetricsCollector

**Constructor:**
```python
MetricsCollector(retention_seconds=3600, max_samples_per_metric=10000)
```

**Methods:**
- `record(metric_type, value, metadata=None)` - Record single metric
- `record_batch(metrics)` - Record multiple metrics
- `get_recent(metric_type, seconds=None, limit=None)` - Get recent samples
- `get_time_series(metric_type, start_time=None, end_time=None)` - Get time series
- `get_aggregated(metric_type, period="1s", limit=100)` - Get aggregated data
- `get_statistics(metric_type, seconds=None)` - Get statistics
- `get_latest(metric_type)` - Get latest value
- `start_aggregation()` - Start background aggregation
- `stop_aggregation()` - Stop background aggregation
- `clear(metric_type=None)` - Clear metrics

### AnalyticsDashboard

**Constructor:**
```python
AnalyticsDashboard(metrics_collector=None, parent=None)
```

**Methods:**
- `record_metrics(metrics)` - Record batch of metrics
- `clear_metrics()` - Clear all metrics
- `set_update_interval(interval_ms)` - Set update frequency
- `cleanup()` - Cleanup resources

---

## License

Copyright © 2025 Sherin-SEF-AI
Part of Trinity Phase 2 - Autonomous Vehicle Testing Platform

---

## Support

For issues or questions:
- Check examples above
- Review configuration options
- See main project documentation

**Phase 5.1 Complete** 
