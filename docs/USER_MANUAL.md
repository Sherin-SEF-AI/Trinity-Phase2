# Trinity Phase 2 - User Manual

Comprehensive guide for using the Trinity Autonomous Vehicle Testing Platform.

## Table of Contents

- [Introduction](#introduction)
- [Getting Started](#getting-started)
- [GUI Overview](#gui-overview)
- [Core Features](#core-features)
  - [Camera Management](#camera-management)
  - [Recording Sessions](#recording-sessions)
  - [Object Detection & Tracking](#object-detection--tracking)
  - [Edge Case Detection](#edge-case-detection)
  - [Analytics Dashboard](#analytics-dashboard)
  - [Report Generation](#report-generation)
- [Advanced Features](#advanced-features)
- [Workflows](#workflows)
- [Best Practices](#best-practices)
- [FAQ](#faq)

---

## Introduction

Trinity Phase 2 is a comprehensive testing platform designed for autonomous vehicle (AV) validation, safety analysis, and edge case detection. It provides real-time monitoring, advanced analytics, and automated reporting capabilities.

### Key Capabilities

- **Multi-Camera Recording**: Synchronize up to 4 camera streams
- **Real-Time Detection**: YOLOv8/v10 object detection with DeepSORT tracking
- **Safety Analysis**: TTC calculation, near-miss detection, collision prediction
- **Edge Case Detection**: Automatic identification of challenging scenarios
- **Analytics**: Real-time metrics visualization and session comparison
- **Reporting**: Automated PDF report generation with visualizations
- **API Access**: RESTful API and WebSocket support for integration

---

## Getting Started

### Initial Setup

1. **Launch Trinity**:
```bash
python -m trinity.gui.main_window
```

2. **Configure Cameras** (first time):
   - Click **"Settings"** → **"Camera Configuration"**
   - Add camera sources (RTSP URLs, video files, or device IDs)
   - Calibrate cameras for 3D positioning
   - Save configuration

3. **Select Detection Model**:
   - Click **"Detection"** → **"Model Settings"**
   - Choose YOLO model (yolov8n for speed, yolov8m for accuracy)
   - Select device (CUDA GPU recommended)
   - Apply settings

4. **Start Your First Session**:
   - Click **"New Session"**
   - Select cameras to use
   - Click **"Start Recording"**

---

## GUI Overview

The Trinity GUI consists of several main areas:

### Main Window Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Trinity Phase 2 - AV Testing Platform          [_][□][X]   │
├─────────────────────────────────────────────────────────────┤
│  File  Session  Detection  Analytics  Tools  Help           │
├─────────────────────────────────────────────────────────────┤
│  [Camera 1]      [Camera 2]      [Camera 3]      [Camera 4] │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐│
│  │           │  │           │  │           │  │           ││
│  │  Live     │  │  Live     │  │  Live     │  │  Live     ││
│  │  Video    │  │  Video    │  │  Video    │  │  Video    ││
│  │           │  │           │  │           │  │           ││
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘│
├─────────────────────────────────────────────────────────────┤
│  [Bird's Eye View]                [Detection Stats]          │
│  ┌─────────────────────────┐    ┌──────────────────────┐   │
│  │                         │    │ Detections: 45       │   │
│  │   ●  AV  ●             │    │ Tracks: 12           │   │
│  │      ●      ●          │    │ FPS: 28.5            │   │
│  │  ●              ●      │    │ Events: 3            │   │
│  │         ●              │    │ TTC: 4.2s            │   │
│  └─────────────────────────┘    └──────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  Status: Recording | Duration: 00:15:32 | Events: 3         │
└─────────────────────────────────────────────────────────────┘
```

### Menu Bar

- **File**: New session, open session, save, export, exit
- **Session**: Start/stop recording, pause, session settings
- **Detection**: Model settings, detection parameters, calibration
- **Analytics**: Open dashboard, view reports, session comparison
- **Tools**: Annotation tools, dataset export, API settings
- **Help**: Documentation, about, check for updates

---

## Core Features

### Camera Management

#### Adding Cameras

1. **Menu Path**: Settings → Camera Configuration → Add Camera

2. **Source Types**:
   - **RTSP Stream**: `rtsp://username:password@ip:port/path`
   - **USB Camera**: Device ID (0, 1, 2, etc.)
   - **Video File**: Path to MP4/AVI file
   - **Image Sequence**: Directory with numbered images

3. **Example Configuration**:
```yaml
cameras:
  - id: 1
    name: "Front Camera"
    source: "rtsp://admin:password@192.168.1.100:554/stream1"
    resolution: [1920, 1080]
    fps: 30

  - id: 2
    name: "Rear Camera"
    source: "/dev/video0"
    resolution: [1280, 720]
    fps: 30
```

#### Camera Calibration

Calibration enables 3D position estimation and bird's eye view.

1. **Capture Calibration Images**:
   - Click **"Calibration"** → **"Start Calibration"**
   - Use checkerboard pattern (9x6 recommended)
   - Capture 15-20 images from different angles
   - Click **"Process Images"**

2. **Set Ground Plane**:
   - Click **"Set Ground Points"**
   - Mark 4 points on the ground plane
   - Enter real-world dimensions
   - Click **"Calculate Transform"**

3. **Verify Calibration**:
   - Check reprojection error (should be < 0.5 pixels)
   - Test with known distances
   - Save calibration data

---

### Recording Sessions

#### Creating a New Session

1. **Click "New Session"** or File → New Session
2. **Configure Session**:
   - **Name**: Descriptive name (e.g., "Highway Test - Sunny Day")
   - **Location**: Test location
   - **Description**: Test objectives
   - **Cameras**: Select cameras to use
   - **Recording Settings**:
     - Video codec: H.264 (recommended)
     - Quality: High/Medium/Low
     - Separate files per camera: Yes/No

3. **Click "Create"**

#### During Recording

**Start Recording**:
```
Session → Start Recording (or Ctrl+R)
```

**Monitor**:
- Live video feeds
- Real-time detection overlays
- Bird's eye view
- Statistics panel
- Event log

**Pause/Resume**:
```
Session → Pause (Ctrl+P)
Session → Resume (Ctrl+R)
```

**Manual Event Marking**:
```
Right-click on video → Mark Event → Select type → Add notes
```

**Stop Recording**:
```
Session → Stop Recording (Ctrl+S)
```

#### Post-Session

After stopping, Trinity automatically:
- Saves video files
- Processes detections
- Generates metadata
- Creates session summary
- Detects edge cases

---

### Object Detection & Tracking

#### Detection Settings

**Access**: Detection → Model Settings

**Parameters**:
- **Model**: yolov8n/s/m/l/x (n=fastest, x=most accurate)
- **Confidence Threshold**: 0.25 (lower = more detections, more false positives)
- **NMS Threshold**: 0.45 (lower = fewer overlapping boxes)
- **Device**: cuda:0 (GPU) or cpu
- **Input Size**: 640/1280 (higher = more accurate, slower)

**Recommended Settings**:
```yaml
# For real-time performance
detection:
  model: yolov8n
  conf_threshold: 0.30
  nms_threshold: 0.45
  device: cuda:0
  input_size: 640

# For maximum accuracy
detection:
  model: yolov8m
  conf_threshold: 0.25
  nms_threshold: 0.45
  device: cuda:0
  input_size: 1280
```

#### Tracking Settings

**Access**: Detection → Tracking Settings

**Parameters**:
- **Max Age**: Frames to keep track without detection (default: 30)
- **Min Hits**: Detections before track confirmed (default: 3)
- **IOU Threshold**: Overlap threshold for matching (default: 0.3)

#### Viewing Detections

**Live View**:
- Bounding boxes with class labels
- Confidence scores
- Track IDs
- Velocity vectors (if tracking enabled)

**Bird's Eye View**:
- 2D top-down view
- Object positions in real-world coordinates
- Trajectories
- AV highlighting

---

### Edge Case Detection

Trinity automatically detects challenging scenarios for AV testing.

#### Detected Edge Cases

1. **Occlusion Events**
   - Partial object occlusion
   - Complete object occlusion
   - Re-appearance after occlusion

2. **Complex Interactions**
   - Multiple objects in proximity
   - Crossing paths
   - Lane changes near AV

3. **Environmental Challenges**
   - Low lighting conditions
   - Adverse weather
   - Glare/reflections

4. **Traffic Scenarios**
   - Dense traffic
   - Sudden braking
   - Erratic behavior

5. **Safety-Critical Events**
   - Near misses (TTC < 2s)
   - Collision warnings
   - Emergency maneuvers

#### Viewing Edge Cases

**During Session**:
- Edge cases appear in event log with ⚠️ icon
- Automatic clip extraction (±5 seconds)

**After Session**:
```
Analytics → Edge Cases → View Detected Cases
```

**Edge Case Panel**:
- Thumbnail preview
- Timestamp
- Category
- Severity (Low/Medium/High/Critical)
- Confidence score
- Video clip with annotations

#### Exporting Edge Cases

```
Analytics → Edge Cases → Export
```

**Export Options**:
- Video clips only
- With annotations (JSON/XML)
- COCO dataset format
- KITTI format
- Custom format

---

### Analytics Dashboard

Real-time and historical analytics visualization.

#### Opening Dashboard

```
Analytics → Open Dashboard
```

#### Dashboard Tabs

**1. Overview Tab**
- System FPS
- Total detections
- Active tracks
- Safety events
- Edge cases count
- Pipeline time
- System statistics (last 60s)

**2. Performance Tab**
- FPS time series chart
- Pipeline time breakdown:
  - Detection time
  - Tracking time
  - Total pipeline time
- Resource utilization

**3. Detection Tab**
- Detections over time
- Active tracks over time
- Detection spatial distribution (heatmap)
- Class distribution

**4. Safety Tab**
- Minimum TTC
- Near misses count
- Total safety events
- Events over time
- TTC time series

**5. Sessions Tab**
- Session comparison
- Historical data
- Trend analysis

#### Recording Metrics

Metrics are automatically recorded during sessions. You can also manually record:

```python
from trinity.analytics import MetricType

dashboard.record_metrics({
    MetricType.FPS: 30.5,
    MetricType.DETECTIONS_COUNT: 45,
    MetricType.TRACKS_COUNT: 12,
    MetricType.MIN_TTC: 3.5
})
```

---

### Report Generation

Automated comprehensive reporting.

#### Generating Reports

**From GUI**:
```
Analytics → Generate Report → Select Session → Configure → Generate
```

**From Code**:
```python
from trinity.reporting import ReportGenerator

generator = ReportGenerator()
report = generator.generate_session_report(
    session_id="test_session_001",
    output_path="reports/session_report.pdf",
    include_visualizations=True
)
```

#### Report Sections

1. **Executive Summary**
   - Test overview
   - Key findings
   - Recommendations

2. **Session Information**
   - Date, time, duration
   - Location, weather
   - Equipment used

3. **Detection Statistics**
   - Total detections by class
   - Detection confidence distribution
   - Temporal distribution

4. **Tracking Analysis**
   - Total tracks
   - Average track duration
   - Track stability metrics

5. **Safety Analysis**
   - TTC statistics
   - Near misses
   - Collision warnings
   - Safety score

6. **Edge Cases**
   - Total edge cases detected
   - Breakdown by category
   - Example clips with thumbnails
   - Annotations

7. **Performance Metrics**
   - Average FPS
   - Pipeline latency
   - Resource utilization
   - System health

8. **Visualizations**
   - Detection heatmaps
   - Trajectory plots
   - Time series charts
   - Statistical graphs

#### Report Formats

- **PDF**: Full report with visualizations (default)
- **HTML**: Interactive web report
- **JSON**: Machine-readable data
- **Excel**: Tabular data export

#### Customizing Reports

Edit report template:
```
config/report_template.yaml
```

Example customization:
```yaml
report:
  title: "AV Safety Validation Report"
  company: "Your Company"
  logo: "assets/logo.png"

  sections:
    - executive_summary
    - session_info
    - detection_stats
    - safety_analysis
    - edge_cases

  visualizations:
    detection_heatmap: true
    trajectory_plot: true
    fps_chart: true

  styling:
    primary_color: "#3498db"
    font: "Arial"
```

---

## Advanced Features

### API Integration

Trinity provides a REST API and WebSocket interface.

#### Starting API Server

```bash
python -m trinity.api.server --host 0.0.0.0 --port 8000
```

#### REST API Examples

**Start Session**:
```bash
curl -X POST http://localhost:8000/api/v1/sessions/start \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Session", "cameras": [1, 2]}'
```

**Get Metrics**:
```bash
curl http://localhost:8000/api/v1/metrics/current
```

**Generate Report**:
```bash
curl -X POST http://localhost:8000/api/v1/reports/generate \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test_001", "format": "pdf"}'
```

See [API Reference](API_REFERENCE.md) for complete documentation.

#### WebSocket Streaming

```python
import asyncio
import websockets
import json

async def stream_detections():
    uri = "ws://localhost:8000/ws/detections"
    async with websockets.connect(uri) as websocket:
        while True:
            data = await websocket.recv()
            detections = json.loads(data)
            print(f"Received {len(detections)} detections")

asyncio.run(stream_detections())
```

### Dataset Export

Export annotated data for ML training.

#### Export Formats

**COCO Format**:
```python
from trinity.datasets import COCOExporter

exporter = COCOExporter()
exporter.export_session(
    session_id="test_001",
    output_dir="datasets/coco",
    split="train"  # train/val/test
)
```

**KITTI Format**:
```python
from trinity.datasets import KITTIExporter

exporter = KITTIExporter()
exporter.export_session(
    session_id="test_001",
    output_dir="datasets/kitti"
)
```

**nuScenes Format**:
```python
from trinity.datasets import NuScenesExporter

exporter = NuScenesExporter()
exporter.export_session(
    session_id="test_001",
    output_dir="datasets/nuscenes"
)
```

### Annotation Tools

Manual annotation interface for ground truth creation.

**Open Annotation Tool**:
```
Tools → Annotation → Open Annotator
```

**Features**:
- Bounding box annotation
- Track annotation
- Keypoint annotation
- Segmentation masks
- Event labeling
- Quality assurance tools

### Batch Processing

Process multiple sessions automatically.

```python
from trinity.processing import BatchProcessor

processor = BatchProcessor()
processor.add_sessions([
    "session_001",
    "session_002",
    "session_003"
])

processor.run(
    detect_edge_cases=True,
    generate_reports=True,
    export_datasets=True
)
```

---

## Workflows

### Workflow 1: Basic Testing Session

1. Configure cameras
2. Start new session
3. Begin recording
4. Monitor live detections
5. Mark important events manually
6. Stop recording
7. Review edge cases
8. Generate report

**Time**: ~30 minutes

---

### Workflow 2: Dataset Collection

1. Create session with target scenario
2. Record continuously
3. Use annotation tool for ground truth
4. Export in desired format (COCO/KITTI)
5. Validate annotations
6. Upload to training pipeline

**Time**: Varies

---

### Workflow 3: Safety Validation

1. Configure safety thresholds
2. Record test drive
3. Monitor real-time TTC
4. Review safety events
5. Analyze near misses
6. Generate safety report
7. Export edge cases for analysis

**Time**: ~1 hour

---

### Workflow 4: Comparative Analysis

1. Record baseline session
2. Record test session (with changes)
3. Open analytics dashboard
4. Compare sessions side-by-side
5. Analyze improvements/regressions
6. Generate comparative report

**Time**: ~45 minutes

---

## Best Practices

### Recording

- **Pre-flight check**: Test all cameras before recording
- **Lighting**: Ensure adequate lighting for detection
- **Calibration**: Calibrate cameras before each deployment
- **Naming**: Use descriptive session names with dates
- **Documentation**: Add notes about test conditions

### Detection

- **Model selection**: Start with yolov8n, upgrade if needed
- **Confidence threshold**: 0.25-0.30 for most cases
- **Resolution**: 640px for real-time, 1280px for accuracy
- **GPU**: Always use GPU for real-time performance

### Storage

- **Disk space**: Monitor available space (videos are large)
- **Backup**: Regular backups of session data
- **Archival**: Compress old sessions
- **Organization**: Use consistent directory structure

### Performance

- **Target FPS**: Aim for 20+ FPS for smooth tracking
- **Resolution**: Lower resolution if FPS drops
- **Cameras**: Limit active cameras if performance issues
- **Resources**: Monitor GPU memory and CPU usage

---

## FAQ

### Q: What FPS should I expect?

**A**: With YOLOv8n on RTX 3060:
- 1 camera @ 1080p: 25-30 FPS
- 2 cameras @ 1080p: 15-20 FPS
- 4 cameras @ 720p: 12-15 FPS

### Q: How much storage do I need?

**A**: Approximate rates (H.264, high quality):
- 1080p @ 30fps: ~200 MB/minute
- 720p @ 30fps: ~100 MB/minute

For 1-hour session with 4 cameras @ 1080p: ~50 GB

### Q: Can I use Trinity without a GPU?

**A**: Yes, but performance will be limited:
- CPU mode: 2-5 FPS (not real-time)
- Recommended: Process recorded videos offline

### Q: How do I improve detection accuracy?

**A**:
1. Use larger model (yolov8m/l)
2. Increase input size to 1280
3. Lower confidence threshold
4. Ensure good lighting
5. Calibrate cameras properly

### Q: What cameras are supported?

**A**:
- USB cameras (UVC compatible)
- IP cameras with RTSP
- Video files (MP4, AVI, MOV)
- Image sequences
- GigE Vision cameras (with adapter)

### Q: Can I run Trinity on multiple machines?

**A**: Yes, via API:
- One machine: Recording + detection
- Other machines: Connect via REST API
- WebSocket: Real-time data streaming

### Q: How do I export edge cases for retraining?

**A**:
```python
from trinity.edge_cases import EdgeCaseExporter

exporter = EdgeCaseExporter()
exporter.export_for_training(
    session_id="test_001",
    output_dir="training_data/edge_cases",
    format="coco"
)
```

### Q: What's the difference between events and edge cases?

**A**:
- **Events**: Any notable occurrence (manual or automatic)
- **Edge Cases**: Specific challenging scenarios for AV systems

All edge cases are events, but not all events are edge cases.

---

## Next Steps

- **Advanced Configuration**: [CONFIGURATION.md](CONFIGURATION.md)
- **API Documentation**: [API_REFERENCE.md](API_REFERENCE.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Development**: [CONTRIBUTING.md](../CONTRIBUTING.md)

---

## Support

- **Email**: sherin@sef-ai.com
- **GitHub Issues**: [Report a bug](https://github.com/Sherin-SEF-AI/Trinity-Phase2/issues)
- **Documentation**: [Full docs](https://github.com/Sherin-SEF-AI/Trinity-Phase2/tree/main/docs)

---

**Document Version**: 1.0.0
**Last Updated**: November 2025
**Trinity Version**: Phase 2 (72% complete)
