# Trinity Phase 2: Autonomous Vehicle Testing & Validation Suite

**Enterprise-Grade Multi-Camera AV Testing Platform**

## Overview

Trinity Phase 2 is a production-ready autonomous vehicle testing platform that uses 3 external Logitech webcams as infrastructure sensors. This system bridges real-world testing with simulation environments, provides ground truth data generation, validates perception systems, and documents edge cases for AV development.

## Key Features

- **Multi-Camera Infrastructure**: Synchronized 3-camera system with advanced calibration
- **Real-Time Object Detection & Tracking**: YOLOv8/v10 + DeepSORT with multi-view fusion
- **3D Position Estimation**: Multi-view triangulation and bird's eye view visualization
- **AV Performance Monitoring**: Comprehensive behavior analysis and safety metrics
- **Edge Case Detection**: Automatic identification and documentation of critical scenarios
- **Ground Truth Generation**: High-quality labeled datasets in multiple formats (COCO, KITTI, nuScenes)
- **CARLA Integration**: Seamless real-to-sim and sim-to-real validation
- **Perception Validation**: Compare AV sensors against infrastructure ground truth
- **Modern PyQt6 GUI**: Dark theme with comprehensive dashboards and analytics
- **REST API**: FastAPI with WebSocket support for real-time data streaming

## System Requirements

### Minimum
- CPU: Intel i7-10700K or AMD Ryzen 7 3700X (8 cores)
- GPU: NVIDIA RTX 3060 (12GB VRAM)
- RAM: 32GB DDR4
- Storage: 1TB NVMe SSD + 4TB HDD
- 3x USB 3.0 ports for Logitech webcams

### Recommended (Production)
- CPU: Intel i9-12900K or AMD Ryzen 9 5950X (16+ cores)
- GPU: NVIDIA RTX 4090 (24GB) or A4000/A5000
- RAM: 64GB DDR5
- Storage: 2TB NVMe SSD + 16TB RAID array
- 10 Gigabit Ethernet

## Technology Stack

- **GUI**: PyQt6
- **Computer Vision**: OpenCV, YOLOv8/v10, DeepSORT
- **3D Visualization**: Open3D, PyVista, Matplotlib
- **Simulation**: CARLA Python API
- **ML/AI**: PyTorch, Ultralytics
- **Database**: PostgreSQL (production), SQLite (development)
- **Video Processing**: FFmpeg, H.265 encoding
- **API**: FastAPI, WebSocket
- **Data Formats**: ROS bags, HDF5, Parquet

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Sherin-SEF-AI/Trinity-Phase2.git
cd Trinity-Phase2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -m trinity.database.init_db

# Run the application
python -m trinity.main
```

### Docker Deployment

```bash
docker-compose up -d
```

## Project Structure

```
Trinity-Phase2/
├── trinity/                    # Main application package
│   ├── core/                   # Core system components
│   │   ├── camera_manager.py  # Multi-camera management
│   │   ├── recorder.py         # Video recording system
│   │   ├── calibration.py     # Camera calibration
│   │   └── config.py           # Configuration management
│   ├── detection/              # Object detection & tracking
│   │   ├── detector.py         # YOLO integration
│   │   ├── tracker.py          # DeepSORT tracking
│   │   ├── fusion.py           # Multi-view fusion
│   │   └── position_3d.py      # 3D position estimation
│   ├── av/                     # AV-specific modules
│   │   ├── monitor.py          # AV behavior monitoring
│   │   ├── safety_metrics.py  # Safety calculations
│   │   ├── perception_validation.py
│   │   └── trajectory.py       # Trajectory analysis
│   ├── scenarios/              # Test scenario management
│   │   ├── scenario_manager.py
│   │   ├── edge_case_detector.py
│   │   └── library/            # Pre-defined scenarios
│   ├── carla_integration/      # CARLA simulation bridge
│   │   ├── carla_bridge.py
│   │   ├── scenario_exporter.py
│   │   └── sim_validator.py
│   ├── dataset/                # Dataset management
│   │   ├── annotation.py       # Annotation tools
│   │   ├── exporter.py         # Multi-format export
│   │   └── quality_control.py
│   ├── gui/                    # PyQt6 GUI
│   │   ├── main_window.py      # Main application window
│   │   ├── tabs/               # Tab implementations
│   │   ├── widgets/            # Custom widgets
│   │   └── styles/             # Dark theme styles
│   ├── database/               # Database layer
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── init_db.py          # Database initialization
│   │   └── queries.py          # Common queries
│   ├── api/                    # REST API
│   │   ├── server.py           # FastAPI server
│   │   ├── routes/             # API endpoints
│   │   └── websocket.py        # WebSocket handler
│   ├── analytics/              # Analytics & reporting
│   │   ├── metrics.py          # Metric calculations
│   │   ├── reports.py          # Report generation
│   │   └── visualizations.py
│   ├── utils/                  # Utilities
│   │   ├── coordinate_transform.py
│   │   ├── video_utils.py
│   │   └── logger.py
│   └── main.py                 # Application entry point
├── tests/                      # Test suite
├── docs/                       # Documentation
├── config/                     # Configuration files
├── docker/                     # Docker configurations
├── scripts/                    # Utility scripts
├── requirements.txt
├── pyproject.toml
├── docker-compose.yml
└── README.md
```

## Development Phases

- **Phase 1**: Core Infrastructure (Camera management, recording, GUI framework, database)
- **Phase 2**: Detection & Tracking (YOLO, DeepSORT, 3D estimation, BEV visualization)
- **Phase 3**: AV Monitoring (Tracking, trajectory analysis, safety metrics)
- **Phase 4**: Advanced Features (Edge cases, CARLA, perception validation, annotation)
- **Phase 5**: Analytics & Reports (Dashboard, reports, dataset export, API)
- **Phase 6**: Polish & Documentation (UI refinement, optimization, docs, deployment)

## Usage Examples

### Basic Test Session

```python
from trinity.core.camera_manager import CameraManager
from trinity.detection.detector import ObjectDetector
from trinity.av.monitor import AVMonitor

# Initialize system
camera_mgr = CameraManager(num_cameras=3)
detector = ObjectDetector(model='yolov8x')
av_monitor = AVMonitor()

# Start test session
session = av_monitor.start_session(
    name="Highway Test",
    av_vehicle_id="vehicle_001"
)

# Process frames
for frames in camera_mgr.get_synchronized_frames():
    detections = detector.detect_multi_view(frames)
    av_monitor.update(detections)

# Stop and generate report
session.stop()
report = session.generate_report()
```

### Edge Case Detection

```python
from trinity.scenarios.edge_case_detector import EdgeCaseDetector

detector = EdgeCaseDetector(
    ttc_threshold=2.0,
    anomaly_threshold=0.8
)

# Automatic detection during session
edge_cases = detector.detect_realtime(session)

# Export to CARLA
for case in edge_cases:
    case.export_to_carla("scenarios/edge_cases/")
```

## API Usage

### REST API

```bash
# Start a test session
curl -X POST http://localhost:8000/sessions/start \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Session", "av_id": "vehicle_001"}'

# Get real-time metrics
curl http://localhost:8000/sessions/{session_id}/metrics

# Query edge cases
curl http://localhost:8000/edge_cases?severity=5
```

### WebSocket Streaming

```python
import asyncio
import websockets

async def receive_realtime_data():
    async with websockets.connect('ws://localhost:8000/ws') as websocket:
        while True:
            data = await websocket.recv()
            print(f"Received: {data}")

asyncio.run(receive_realtime_data())
```

## Configuration

Edit `config/config.yaml` to customize:

```yaml
cameras:
  count: 3
  resolution: [1920, 1080]
  fps: 30
  codec: 'h265'

detection:
  model: 'yolov8x'
  confidence_threshold: 0.5
  nms_threshold: 0.4

tracking:
  max_age: 30
  min_hits: 3
  iou_threshold: 0.3

database:
  type: 'postgresql'  # or 'sqlite'
  host: 'localhost'
  port: 5432
  name: 'trinity_av_testing'

carla:
  host: 'localhost'
  port: 2000
  timeout: 10.0
```

## Testing

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/test_detection.py

# Run with coverage
pytest --cov=trinity --cov-report=html
```

## Documentation

- [User Manual](docs/user_manual.md)
- [Technical Documentation](docs/technical_docs.md)
- [API Reference](docs/api_reference.md)
- [Scenario Creation Guide](docs/scenario_guide.md)
- [Calibration Procedures](docs/calibration.md)
- [Troubleshooting](docs/troubleshooting.md)

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Contact

- Project Lead: Sherin-SEF-AI
- Email: [contact information]
- Issues: https://github.com/Sherin-SEF-AI/Trinity-Phase2/issues

## Acknowledgments

- YOLOv8/v10 by Ultralytics
- DeepSORT tracking algorithm
- CARLA Simulator
- PyQt6 framework
- Open3D for 3D visualization

## Citation

If you use this software in your research, please cite:

```bibtex
@software{trinity_phase2,
  title={Trinity Phase 2: Autonomous Vehicle Testing & Validation Suite},
  author={Sherin-SEF-AI},
  year={2025},
  url={https://github.com/Sherin-SEF-AI/Trinity-Phase2}
}
```

---

**Built for enterprise-grade autonomous vehicle testing and validation.**
