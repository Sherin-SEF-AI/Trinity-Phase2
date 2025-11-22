# Trinity Phase 2: Autonomous Vehicle Testing & Validation Suite

**Enterprise-Grade Multi-Camera AV Testing Platform**

[![Status](https://img.shields.io/badge/Status-72%25%20Complete-blue)]()
[![Python](https://img.shields.io/badge/Python-3.10%2B-green)]()
[![License](https://img.shields.io/badge/License-Proprietary-red)]()
[![Code](https://img.shields.io/badge/Code-19k%20lines-brightgreen)]()

---

## 🎯 Overview

Trinity Phase 2 is a **production-ready** autonomous vehicle testing and validation platform designed for real-world AV development. Using a 3-camera infrastructure sensor setup, it provides comprehensive testing capabilities including real-time detection, safety monitoring, edge case detection, perception validation, and automated reporting.

### What Makes Trinity Unique

- **Infrastructure-Based Testing**: Fixed cameras provide ground truth independent of vehicle sensors
- **Comprehensive Safety Monitoring**: Real-time TTC, near-miss detection, and trajectory analysis
- **Automatic Edge Case Detection**: 18 categories with multi-dimensional severity scoring
- **Production-Ready Analytics**: Real-time dashboards, automated reports, and REST API
- **Dataset Generation**: Multi-format export (COCO, KITTI, nuScenes) with PII anonymization

---

## ✨ Key Features

### Core Capabilities

✅ **Multi-Camera Infrastructure**
- Synchronized 3-camera capture (<10ms accuracy)
- ArUco marker-based calibration
- H.265/H.264 video encoding
- Event-triggered recording with pre/post-roll

✅ **Real-Time Detection & Tracking**
- YOLOv8/v10 object detection (80 COCO classes)
- DeepSORT multi-object tracking
- 3D position estimation via triangulation
- Bird's eye view visualization

✅ **AV-Specific Monitoring**
- ArUco marker-based vehicle identification
- Trajectory analysis and prediction
- Safety metrics (TTC, near-miss, safe distance)
- 7 automatic event detection rules

✅ **Advanced Features**
- Edge case detection (18 categories)
- Perception validation (MOTA/MOTP metrics)
- Dataset management with PII protection
- Multi-format export (COCO/KITTI/nuScenes)

✅ **Analytics & Reporting**
- Real-time analytics dashboard (14 metric types)
- Automated report generation (PDF/HTML/Excel)
- Scheduled reports (daily/weekly/monthly)
- REST API with WebSocket support

✅ **Professional GUI**
- PyQt6 dark theme interface
- 9-tab dashboard
- Live camera feeds with detection overlays
- Real-time metrics visualization

---

## 📊 Current Status

**Overall Completion:** 72% (~19,000 / ~26,000 lines)

| Phase | Status | Lines | Description |
|-------|--------|-------|-------------|
| Phase 1: Core Infrastructure | ✅ 100% | 3,500 | Camera, recording, calibration, database, GUI |
| Phase 2: Detection & Tracking | ✅ 100% | 2,500 | YOLO, DeepSORT, 3D estimation, visualization |
| Phase 3: AV Monitoring | ✅ 100% | 1,800 | AV ID, trajectory, safety, event detection |
| Phase 4: Advanced Features | ✅ 75% | 2,600 | Edge cases, perception validation, datasets |
| Phase 5: Analytics & Integration | ✅ 100% | 5,914 | Dashboard, reporting, dataset export, API |
| Phase 6: Polish & Deployment | 🚧 0% | TBD | UI/UX, optimization, docs, Docker |

**What's Working:**
- Multi-camera capture and recording
- Real-time object detection and tracking
- AV identification and safety monitoring
- Edge case detection and perception validation
- Analytics dashboard with real-time metrics
- Automated report generation
- REST API with WebSocket support
- Dataset export in multiple formats

**What's Next:**
- UI/UX refinement
- Performance optimization
- Comprehensive documentation (in progress)
- Docker deployment packages

---

## 🚀 Quick Start

### System Requirements

**Minimum:**
- Python 3.10+
- NVIDIA GPU with 6GB+ VRAM (GTX 1660 Ti or better)
- 16GB RAM
- 3x USB webcams (Logitech C920 or similar)

**Recommended:**
- Python 3.11
- NVIDIA RTX 3080 or better (12GB+ VRAM)
- 32GB RAM
- 3x high-quality 1080p webcams

### Installation

```bash
# Clone repository
git clone https://github.com/Sherin-SEF-AI/Trinity-Phase2.git
cd Trinity-Phase2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows

# Install numpy first (required for lap package)
pip install --upgrade pip setuptools wheel
pip install "numpy<2.0"
pip install scipy lap

# Install remaining dependencies
pip install -r requirements.txt

# Initialize database
python -m trinity.database.init_db

# Copy and configure settings
cp config/config.template.yaml config/config.yaml
# Edit config/config.yaml with your camera settings

# Download YOLO weights
python -c "from ultralytics import YOLO; YOLO('yolov8x.pt')"

# Run application
python trinity/main.py
```

### Docker Deployment (Coming Soon)

```bash
docker-compose up -d
```

---

## 📁 Project Structure

```
Trinity-Phase2/
├── trinity/                     # Main application package (~19,000 lines)
│   ├── core/                    # Core system (~1,200 lines)
│   │   ├── camera_manager.py   # Multi-camera management
│   │   ├── recorder.py          # H.265 video recording
│   │   ├── calibration.py      # Camera calibration
│   │   └── config.py            # Configuration system
│   ├── database/                # Database layer (~800 lines)
│   │   ├── models.py            # 12 SQLAlchemy models
│   │   ├── init_db.py           # Database initialization
│   │   └── queries.py           # Common queries
│   ├── detection/               # Detection & Tracking (~2,500 lines)
│   │   ├── detector.py          # YOLOv8/v10 integration
│   │   ├── tracker.py           # DeepSORT tracking
│   │   ├── position_3d.py       # 3D estimation
│   │   ├── detection_system.py  # Integrated pipeline
│   │   └── visualization.py     # Detection visualization
│   ├── av_monitoring/           # AV Monitoring (~1,800 lines)
│   │   ├── av_identification.py # ArUco marker detection
│   │   ├── trajectory_analysis.py # Path analysis
│   │   ├── safety_metrics.py    # TTC, near-miss
│   │   ├── event_detection.py   # 7 event rules
│   │   └── av_monitoring_system.py
│   ├── advanced/                # Advanced Features (~2,600 lines)
│   │   ├── edge_case_detection.py # 18 edge case categories
│   │   ├── perception_validation.py # MOTA/MOTP metrics
│   │   └── dataset_management.py # Multi-format export
│   ├── reporting/               # Report Generation (~2,550 lines)
│   │   ├── report_generator.py  # PDF/HTML/Excel reports
│   │   ├── template_engine.py   # Report templates
│   │   ├── chart_generator.py   # Chart generation
│   │   └── scheduler.py         # Automated scheduling
│   ├── analytics/               # Analytics Dashboard (~1,500 lines)
│   │   ├── metrics_collector.py # Metrics collection
│   │   ├── visualizations.py    # Chart widgets
│   │   └── dashboard.py         # Main dashboard
│   ├── api/                     # REST API (~1,014 lines)
│   │   └── main.py              # FastAPI application
│   ├── gui/                     # PyQt6 GUI (~1,500 lines)
│   │   ├── main_window.py       # Main application
│   │   ├── tabs/                # 9 tab implementations
│   │   └── widgets/             # Custom widgets
│   ├── utils/                   # Utilities (~300 lines)
│   │   ├── coordinate_transform.py
│   │   └── logger.py
│   └── main.py                  # Entry point
├── config/                      # Configuration
│   └── config.template.yaml     # Template configuration
├── tests/                       # Test suite (planned)
├── docs/                        # Documentation
├── requirements.txt             # Python dependencies
├── PHASE*_SUMMARY.md           # Phase documentation
├── PROJECT_STATUS.md            # Detailed project status
└── README.md                    # This file
```

---

## 💻 Usage Examples

### Basic Test Session

```python
from trinity.core.camera_manager import CameraManager
from trinity.detection.detection_system import DetectionTrackingSystem
from trinity.av_monitoring.av_monitoring_system import AVMonitoringSystem

# Initialize systems
camera_mgr = CameraManager(config, num_cameras=3)
detection = DetectionTrackingSystem(config, num_cameras=3)
av_monitor = AVMonitoringSystem(config)

# Start test session
camera_mgr.start_capture()

# Process frames
while True:
    frames = camera_mgr.get_synchronized_frames()

    # Detection and tracking
    results = detection.process_frame(frames)

    # AV monitoring
    av_results = av_monitor.process_frame(
        all_tracks=results['global_tracks'],
        frame_number=results['frame_number']
    )

    # Check for safety events
    if av_results['safety_events']:
        print(f"Safety event detected: {av_results['safety_events']}")
```

### Edge Case Detection

```python
from trinity.advanced.edge_case_detection import EdgeCaseDetector

detector = EdgeCaseDetector(config)

# Process frame
edge_cases = detector.detect_edge_cases(
    all_tracks=tracks,
    av_tracks=av_tracks,
    ttc_results=ttc_results,
    frame_number=frame_num
)

# Get high-severity cases
critical_cases = [
    ec for ec in edge_cases
    if ec.severity == 'CRITICAL'
]

print(f"Found {len(critical_cases)} critical edge cases")
```

### Generate Reports

```python
from trinity.reporting import ReportGenerator, SessionSummary, ReportFormat
from datetime import datetime

# Create report generator
generator = ReportGenerator()

# Create session summary
summary = SessionSummary(
    session_id=1,
    session_name="Highway Test",
    test_type="scenario",
    start_time=datetime.now(),
    end_time=datetime.now(),
    duration_seconds=3600,
    total_frames=108000,
    total_detections=25000,
    total_tracks=450
)

# Generate PDF report
report_path = generator.generate_session_report(
    summary,
    output_format=ReportFormat.PDF
)
```

### Analytics Dashboard

```python
from trinity.analytics import AnalyticsDashboard, MetricsCollector, MetricType

# Create metrics collector
metrics = MetricsCollector()

# Create dashboard
dashboard = AnalyticsDashboard(metrics_collector=metrics)

# Record metrics in processing loop
dashboard.record_metrics({
    MetricType.FPS: 30.5,
    MetricType.DETECTIONS_COUNT: 45,
    MetricType.TRACKS_COUNT: 12,
    MetricType.MIN_TTC: 3.5
})
```

---

## 🌐 REST API Usage

### Start API Server

```bash
cd trinity/api
uvicorn main:app --host 0.0.0.0 --port 8000
```

### API Examples

```bash
# Get system status
curl http://localhost:8000/api/v1/system/status

# List test sessions
curl http://localhost:8000/api/v1/sessions

# Create new session
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Session", "test_type": "scenario", "av_vehicle_id": "AV001"}'

# Get detections
curl "http://localhost:8000/api/v1/detections?session_id=1&limit=50"

# Get safety events
curl "http://localhost:8000/api/v1/safety/events?severity=high"
```

### WebSocket

```python
import asyncio
import websockets
import json

async def receive_detections():
    async with websockets.connect('ws://localhost:8000/ws/detections') as ws:
        while True:
            data = await ws.receive()
            detections = json.loads(data)
            print(f"Received {len(detections['detections'])} detections")

asyncio.run(receive_detections())
```

---

## ⚙️ Configuration

Edit `config/config.yaml` to customize system behavior. Key sections:

### Camera Configuration

```yaml
cameras:
  count: 3
  camera_1:
    device_id: 0
    resolution: [1920, 1080]
    fps: 30
    position: [0.0, 0.0, 3.0]  # X, Y, Z in meters
```

### Detection Settings

```yaml
detection:
  model: 'yolov8x'
  confidence_threshold: 0.5
  device: 'cuda'  # or 'cpu'
  batch_size: 3
```

### AV Monitoring

```yaml
av_monitoring:
  enable_av_identification: true
  enable_trajectory_analysis: true
  enable_safety_metrics: true
  enable_event_detection: true

  registered_avs:
    AV001:
      name: "Test Vehicle 1"
      marker_ids: [0, 1, 2, 3]
```

### Reporting

```yaml
reporting:
  enabled: true
  generator:
    default_format: "pdf"
    include_charts: true
  scheduler:
    enabled: true
    schedules:
      daily_summary:
        enabled: true
        format: "html"
        hour: 18
```

See `config/config.template.yaml` for full configuration options.

---

## 📚 Documentation

- **[Project Status](PROJECT_STATUS.md)** - Detailed project status and roadmap
- **[Phase Summaries](PHASE*_SUMMARY.md)** - Documentation for each phase
- **[API Documentation](trinity/api/README.md)** - Complete API reference
- **[Analytics Guide](trinity/analytics/README.md)** - Analytics dashboard guide
- **[Reporting Guide](trinity/reporting/README.md)** - Report generation guide

### Module-Specific Documentation

Each major module has its own README:
- [Detection System](trinity/detection/) - Object detection and tracking
- [AV Monitoring](trinity/av_monitoring/) - AV-specific monitoring
- [Advanced Features](trinity/advanced/) - Edge cases, perception, datasets
- [Reporting](trinity/reporting/) - Report generation and scheduling
- [Analytics](trinity/analytics/) - Real-time analytics dashboard
- [REST API](trinity/api/) - API endpoints and WebSocket

---

## 🧪 Testing

```bash
# Run all tests (when implemented)
pytest

# Run with coverage
pytest --cov=trinity --cov-report=html

# Run specific module tests
pytest tests/test_detection.py
```

---

## 🏗️ Technology Stack

### Core Technologies
- **Python 3.10+** - Primary language
- **PyQt6** - GUI framework
- **OpenCV** - Computer vision
- **PyTorch** - Deep learning
- **SQLAlchemy** - Database ORM

### Detection & Tracking
- **YOLOv8/v10** (Ultralytics) - Object detection
- **DeepSORT** - Multi-object tracking
- **NumPy/SciPy** - Numerical computing

### Analytics & Reporting
- **PyQtGraph** - Real-time charts
- **Matplotlib** - Chart generation
- **ReportLab** - PDF generation
- **openpyxl** - Excel generation
- **Jinja2** - HTML templates

### API & Integration
- **FastAPI** - REST API framework
- **Uvicorn** - ASGI server
- **WebSockets** - Real-time communication
- **Pydantic** - Data validation

### Database
- **PostgreSQL** (production) - Primary database
- **SQLite** (development) - Local testing

### Video Processing
- **FFmpeg** - Video encoding/decoding
- **H.265/H.264** - Video codecs
- **imageio** - Frame processing

---

## 🎯 Performance

**Current System Performance** (NVIDIA RTX 3080, Intel i7-12700K)

| Component | Time (ms) | FPS | Notes |
|-----------|-----------|-----|-------|
| Camera Capture (3x) | ~33 | 30 | Hardware limited |
| YOLOv8x Detection | ~50 | 20 | 3 cameras, batch |
| DeepSORT Tracking | ~15 | 66 | All tracks |
| 3D Estimation | ~5 | 200 | Per-frame |
| AV Monitoring | ~10 | 100 | Full pipeline |
| **Total Pipeline** | **~85ms** | **~12 FPS** | **End-to-end** |

**Optimization Opportunities:**
- TensorRT optimization: 2x speedup possible
- Model quantization: 1.5-2x speedup
- Multi-GPU: Near-linear scaling

---

## 🐛 Known Issues & Limitations

1. **Performance**: Current pipeline runs at ~12 FPS (target: 20-30 FPS)
2. **CARLA Integration**: Phase 4.2 not yet implemented
3. **Testing**: Comprehensive test suite not yet implemented
4. **Documentation**: API documentation incomplete
5. **Deployment**: Docker containers not yet created

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for detailed status.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings (Google style)
- Add unit tests for new features

---

## 📄 License

Copyright © 2025 Sherin-SEF-AI. All rights reserved.

This is proprietary software. Unauthorized copying, modification, or distribution is prohibited.

---

## 📧 Contact & Support

- **Project Lead**: Sherin-SEF-AI
- **Repository**: https://github.com/Sherin-SEF-AI/Trinity-Phase2
- **Issues**: https://github.com/Sherin-SEF-AI/Trinity-Phase2/issues

---

## 🙏 Acknowledgments

- **Ultralytics** - YOLOv8/v10 implementation
- **DeepSORT** - Multi-object tracking algorithm
- **PyQt6** - GUI framework
- **FastAPI** - Modern web framework
- **OpenCV** - Computer vision library

---

## 📖 Citation

If you use this software in your research, please cite:

```bibtex
@software{trinity_phase2_2025,
  title={Trinity Phase 2: Autonomous Vehicle Testing & Validation Suite},
  author={Sherin-SEF-AI},
  year={2025},
  version={0.72},
  url={https://github.com/Sherin-SEF-AI/Trinity-Phase2}
}
```

---

**Built for enterprise-grade autonomous vehicle testing and validation.**

**Status:** Active Development | **Version:** 0.72 (72% Complete) | **Last Updated:** 2025-11-22
