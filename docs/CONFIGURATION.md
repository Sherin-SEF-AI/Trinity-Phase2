# Trinity Phase 2 - Configuration Guide

Complete configuration reference for the Trinity AV Testing Platform.

## Table of Contents

- [Overview](#overview)
- [Configuration Files](#configuration-files)
- [System Configuration](#system-configuration)
- [Detection Configuration](#detection-configuration)
- [Tracking Configuration](#tracking-configuration)
- [Camera Configuration](#camera-configuration)
- [Recording Configuration](#recording-configuration)
- [Safety Configuration](#safety-configuration)
- [Analytics Configuration](#analytics-configuration)
- [API Configuration](#api-configuration)
- [Database Configuration](#database-configuration)
- [Performance Tuning](#performance-tuning)
- [Environment Variables](#environment-variables)

---

## Overview

Trinity uses YAML configuration files for system setup. Configuration files are located in the `config/` directory.

**Main Configuration File**: `config/config.yaml`

**Configuration Priority** (highest to lowest):
1. Command-line arguments
2. Environment variables
3. Configuration file
4. Default values

---

## Configuration Files

### Directory Structure

```
config/
├── config.yaml              # Main configuration
├── cameras.yaml             # Camera setup
├── detection_models.yaml    # Detection model settings
├── api.yaml                 # API server configuration
└── calibration/            # Camera calibration data
    ├── camera_1.yaml
    └── camera_2.yaml
```

### Creating Configuration

```bash
# Copy example configuration
cp config/config.example.yaml config/config.yaml

# Edit with your settings
nano config/config.yaml
```

---

## System Configuration

**Location**: `config/config.yaml` → `system`

### Basic Settings

```yaml
system:
  # Application name
  name: "Trinity Phase 2"

  # Version
  version: "2.0.0"

  # Working directory for data
  data_dir: "./data"

  # Logging configuration
  logging:
    level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    file: "logs/trinity.log"
    max_size_mb: 100
    backup_count: 5
    console: true

  # Performance settings
  performance:
    num_workers: 4  # Number of processing threads
    use_gpu: true
    gpu_id: 0  # GPU device ID (0, 1, 2, ...)
    max_memory_mb: 8192  # Maximum GPU memory usage

  # Resource limits
  resources:
    max_cpu_percent: 80.0
    max_memory_percent: 75.0
    max_gpu_memory_percent: 90.0
```

### Advanced Settings

```yaml
system:
  # Debug mode
  debug: false

  # Profile performance
  profiling:
    enabled: false
    output_dir: "profiling/"

  # Crash reporting
  crash_reporting:
    enabled: true
    send_logs: false

  # Auto-save interval (seconds)
  autosave_interval: 300

  # Temporary files
  temp_dir: "/tmp/trinity"
  cleanup_temp_on_exit: true
```

---

## Detection Configuration

**Location**: `config/config.yaml` → `detection`

### Model Settings

```yaml
detection:
  # Model selection
  model: "yolov8n"  # yolov8n, yolov8s, yolov8m, yolov8l, yolov8x

  # Model path
  model_path: "models/yolo/yolov8n.pt"

  # Device
  device: "cuda:0"  # cuda:0, cuda:1, cpu

  # Input size
  input_size: 640  # 320, 640, 1280

  # Confidence threshold
  conf_threshold: 0.25  # 0.0 - 1.0

  # NMS (Non-Maximum Suppression) threshold
  nms_threshold: 0.45  # 0.0 - 1.0

  # Maximum detections per image
  max_det: 300

  # Classes to detect (empty = all classes)
  classes: []  # e.g., [0, 1, 2] for person, bicycle, car

  # Enable half-precision (FP16) for faster inference
  half: true

  # Batch size for processing
  batch_size: 1
```

### Class Names and IDs

```yaml
detection:
  # COCO class mapping
  class_names:
    0: "person"
    1: "bicycle"
    2: "car"
    3: "motorcycle"
    5: "bus"
    7: "truck"
    # ... add more as needed

  # Classes of interest for AV testing
  av_classes: [0, 1, 2, 3, 5, 7]  # person, bicycle, car, motorcycle, bus, truck
```

### Performance Tuning

```yaml
detection:
  # Preprocessing
  preprocessing:
    resize_method: "bilinear"  # nearest, bilinear, bicubic
    normalize: true
    mean: [0.485, 0.456, 0.406]
    std: [0.229, 0.224, 0.225]

  # Post-processing
  postprocessing:
    agnostic_nms: false  # Class-agnostic NMS
    multi_label: false  # Multiple labels per box
```

---

## Tracking Configuration

**Location**: `config/config.yaml` → `tracking`

### DeepSORT Settings

```yaml
tracking:
  # Enable tracking
  enabled: true

  # Tracker type
  tracker: "deepsort"  # deepsort, sort, bytetrack

  # DeepSORT parameters
  deepsort:
    # Maximum age of track without detection
    max_age: 30  # frames

    # Minimum hits before track is confirmed
    min_hits: 3

    # IOU threshold for matching
    iou_threshold: 0.3

    # Maximum IOU distance
    max_iou_distance: 0.7

    # Feature matching
    max_cosine_distance: 0.2
    nn_budget: 100

    # ReID model
    reid_model: "models/reid/osnet_x0_25.pth"
    use_reid: true
```

### Track Management

```yaml
tracking:
  # Track ID assignment
  track_id_start: 1
  reuse_track_ids: false

  # Velocity estimation
  velocity:
    enabled: true
    smoothing: 0.3  # 0.0 - 1.0 (higher = smoother)
    fps: 30  # Assumed FPS for velocity calculation

  # 3D position estimation
  position_3d:
    enabled: true
    ground_plane_height: 0.0  # meters
```

---

## Camera Configuration

**Location**: `config/cameras.yaml`

### Camera Setup

```yaml
cameras:
  # Camera 1
  - id: 1
    name: "Front Camera"
    enabled: true

    # Source
    source:
      type: "rtsp"  # rtsp, usb, file, image_sequence
      url: "rtsp://admin:password@192.168.1.100:554/stream1"
      # For USB: device: 0
      # For file: path: "video.mp4"

    # Resolution
    resolution:
      width: 1920
      height: 1080

    # Frame rate
    fps: 30

    # Region of interest (optional)
    roi:
      enabled: false
      x: 0
      y: 0
      width: 1920
      height: 1080

    # Calibration
    calibration:
      file: "config/calibration/camera_1.yaml"
      auto_load: true

    # Stream settings
    stream:
      buffer_size: 10
      reconnect_attempts: 3
      reconnect_delay_sec: 5
```

### Multiple Cameras

```yaml
cameras:
  - id: 1
    name: "Front Camera"
    source:
      type: "rtsp"
      url: "rtsp://192.168.1.100:554/stream1"
    resolution: {width: 1920, height: 1080}
    fps: 30

  - id: 2
    name: "Rear Camera"
    source:
      type: "rtsp"
      url: "rtsp://192.168.1.101:554/stream1"
    resolution: {width: 1920, height: 1080}
    fps: 30

  - id: 3
    name: "Left Camera"
    source:
      type: "usb"
      device: 0
    resolution: {width: 1280, height: 720}
    fps: 30

  - id: 4
    name: "Right Camera"
    source:
      type: "usb"
      device: 1
    resolution: {width: 1280, height: 720}
    fps: 30
```

### Calibration Data

**Location**: `config/calibration/camera_1.yaml`

```yaml
camera_matrix:
  - [1000.0, 0.0, 960.0]
  - [0.0, 1000.0, 540.0]
  - [0.0, 0.0, 1.0]

distortion_coefficients:
  - [-0.2, 0.05, 0.0, 0.0, 0.0]

resolution: [1920, 1080]

# Rotation and translation for bird's eye view
rotation_matrix:
  - [1.0, 0.0, 0.0]
  - [0.0, 0.866, -0.5]
  - [0.0, 0.5, 0.866]

translation_vector: [0.0, 1.5, 0.5]

# Ground plane equation: ax + by + cz + d = 0
ground_plane: [0.0, 0.0, 1.0, 0.0]
```

---

## Recording Configuration

**Location**: `config/config.yaml` → `recording`

### Video Settings

```yaml
recording:
  # Video codec
  codec: "h264"  # h264, h265, mjpeg, avi

  # Quality
  quality: "high"  # low, medium, high, lossless

  # Bitrate (for h264/h265)
  bitrate_mbps: 10

  # GOP size (keyframe interval)
  gop_size: 30

  # Output format
  format: "mp4"  # mp4, avi, mkv

  # Separate files per camera
  separate_files: true

  # Include audio (if available)
  audio: false

  # Frame dropping
  drop_frames_if_slow: false
```

### Storage Settings

```yaml
recording:
  # Output directory
  output_dir: "data/sessions"

  # Directory structure
  directory_structure: "{session_id}/{camera_name}"

  # Filename pattern
  filename_pattern: "{camera_name}_{timestamp}.mp4"

  # Disk space management
  min_free_space_gb: 10
  auto_cleanup: false
  max_session_age_days: 30
```

---

## Safety Configuration

**Location**: `config/config.yaml` → `safety`

### TTC (Time-to-Collision) Settings

```yaml
safety:
  # TTC calculation
  ttc:
    enabled: true

    # Warning thresholds (seconds)
    critical_threshold: 2.0
    warning_threshold: 4.0

    # Calculation method
    method: "constant_velocity"  # constant_velocity, kalman

    # Update interval (frames)
    update_interval: 1

    # Minimum velocity for TTC calculation (m/s)
    min_velocity: 0.5
```

### Near Miss Detection

```yaml
safety:
  # Near miss detection
  near_miss:
    enabled: true

    # Distance threshold (meters)
    distance_threshold: 2.0

    # TTC threshold (seconds)
    ttc_threshold: 2.5

    # Minimum duration (frames)
    min_duration: 5
```

### Event Logging

```yaml
safety:
  # Event logging
  events:
    # Auto-save events
    auto_save: true

    # Event types to log
    log_types:
      - "near_miss"
      - "ttc_warning"
      - "collision_warning"
      - "sudden_braking"
      - "lane_change"

    # Include video clips
    save_clips: true
    clip_duration_sec: 10  # Total duration (5s before, 5s after)
```

---

## Analytics Configuration

**Location**: `config/config.yaml` → `analytics`

### Dashboard Settings

```yaml
analytics:
  # Enable analytics
  enabled: true

  # Dashboard update interval (ms)
  update_interval_ms: 1000

  # Metrics retention
  retention_seconds: 3600

  # Maximum samples per metric
  max_samples: 10000

  # Auto-start aggregation
  auto_start_aggregation: true

  # Aggregation intervals
  aggregation:
    - interval: "1s"
      retention: 3600  # 1 hour
    - interval: "1m"
      retention: 86400  # 1 day
```

### Visualization Settings

```yaml
analytics:
  # Visualizations
  visualizations:
    # Time series charts
    time_series:
      time_window_seconds: 60
      line_width: 2
      grid: true

    # Heatmaps
    heatmap:
      grid_size: [20, 20]
      colormap: "hot"

    # Statistics cards
    stats_cards:
      update_interval_ms: 1000
      show_delta: true
```

---

## API Configuration

**Location**: `config/api.yaml`

### Server Settings

```yaml
api:
  # Server
  server:
    host: "0.0.0.0"
    port: 8000
    workers: 4

    # SSL/TLS
    ssl:
      enabled: false
      cert_file: "ssl/cert.pem"
      key_file: "ssl/key.pem"

  # CORS
  cors:
    enabled: true
    allowed_origins:
      - "http://localhost:3000"
      - "https://your-domain.com"
    allowed_methods: ["GET", "POST", "PUT", "DELETE"]
    allowed_headers: ["*"]

  # Authentication
  auth:
    enabled: true
    type: "api_key"  # api_key, jwt
    api_keys_file: "config/api_keys.yaml"

    # JWT settings (if type = jwt)
    jwt:
      secret_key: "your-secret-key-change-this"
      algorithm: "HS256"
      expiration_minutes: 60

  # Rate limiting
  rate_limiting:
    enabled: true
    requests_per_minute: 100
    requests_per_hour: 1000
```

### WebSocket Settings

```yaml
api:
  # WebSocket
  websocket:
    enabled: true
    max_connections: 100
    ping_interval_sec: 30
    ping_timeout_sec: 10
```

---

## Database Configuration

**Location**: `config/config.yaml` → `database`

### SQLite (Default)

```yaml
database:
  type: "sqlite"
  path: "trinity.db"

  # Connection pool
  pool_size: 5
  max_overflow: 10
  pool_timeout: 30

  # Options
  echo_sql: false  # Log SQL queries
```

### PostgreSQL

```yaml
database:
  type: "postgresql"
  host: "localhost"
  port: 5432
  database: "trinity"
  username: "trinity_user"
  password: "your_password"

  # Connection pool
  pool_size: 10
  max_overflow: 20
  pool_timeout: 30
```

---

## Performance Tuning

### For Maximum Speed (Real-time)

```yaml
detection:
  model: "yolov8n"
  input_size: 640
  half: true
  batch_size: 1

tracking:
  enabled: true
  max_age: 20

recording:
  codec: "h264"
  quality: "medium"

analytics:
  enabled: false  # Disable if not needed
```

### For Maximum Accuracy (Offline Processing)

```yaml
detection:
  model: "yolov8m"
  input_size: 1280
  conf_threshold: 0.20
  half: false

tracking:
  enabled: true
  max_age: 50
  min_hits: 5

recording:
  codec: "h265"
  quality: "high"
```

### For Low Memory Systems

```yaml
system:
  performance:
    max_memory_mb: 4096
    num_workers: 2

detection:
  model: "yolov8n"
  input_size: 320
  batch_size: 1

analytics:
  max_samples: 1000
  retention_seconds: 600
```

---

## Environment Variables

Override configuration via environment variables:

```bash
# System
export TRINITY_DATA_DIR="/data/trinity"
export TRINITY_LOG_LEVEL="DEBUG"

# Detection
export TRINITY_DETECTION_MODEL="yolov8m"
export TRINITY_DETECTION_DEVICE="cuda:0"

# API
export TRINITY_API_HOST="0.0.0.0"
export TRINITY_API_PORT="8000"
export TRINITY_API_KEY="your_secret_api_key"

# Database
export TRINITY_DB_TYPE="postgresql"
export TRINITY_DB_HOST="localhost"
export TRINITY_DB_USER="trinity"
export TRINITY_DB_PASSWORD="password"

# Performance
export TRINITY_USE_GPU="true"
export TRINITY_GPU_ID="0"
export TRINITY_NUM_WORKERS="4"
```

**Priority**: Environment variables override config file settings.

---

## Configuration Validation

Validate your configuration:

```bash
python -m trinity.config.validate
```

Output:
```
✓ System configuration valid
✓ Detection configuration valid
✓ Tracking configuration valid
✗ Camera configuration invalid: Camera 1 source URL is unreachable
✓ API configuration valid
```

---

## Configuration Examples

### Example 1: Single Camera, Real-time Detection

```yaml
system:
  data_dir: "./data"
  logging:
    level: "INFO"

detection:
  model: "yolov8n"
  device: "cuda:0"
  input_size: 640
  conf_threshold: 0.30

tracking:
  enabled: true

cameras:
  - id: 1
    name: "Main Camera"
    source:
      type: "rtsp"
      url: "rtsp://192.168.1.100:554/stream1"
    resolution: {width: 1920, height: 1080}
    fps: 30

recording:
  codec: "h264"
  quality: "high"
```

### Example 2: Multi-camera, Maximum Accuracy

```yaml
system:
  data_dir: "/mnt/storage/trinity"
  performance:
    use_gpu: true
    gpu_id: 0

detection:
  model: "yolov8m"
  device: "cuda:0"
  input_size: 1280
  conf_threshold: 0.25

tracking:
  enabled: true
  deepsort:
    max_age: 50
    min_hits: 5

cameras:
  - id: 1
    name: "Front"
    source: {type: "rtsp", url: "rtsp://192.168.1.100:554/stream1"}
  - id: 2
    name: "Rear"
    source: {type: "rtsp", url: "rtsp://192.168.1.101:554/stream1"}
  - id: 3
    name: "Left"
    source: {type: "rtsp", url: "rtsp://192.168.1.102:554/stream1"}
  - id: 4
    name: "Right"
    source: {type: "rtsp", url: "rtsp://192.168.1.103:554/stream1"}

analytics:
  enabled: true
  update_interval_ms: 1000
```

---

## Best Practices

1. **Start with defaults**: Use `config.example.yaml` as template
2. **Test incrementally**: Change one setting at a time
3. **Monitor performance**: Use analytics to track impact of changes
4. **Document changes**: Comment your modifications
5. **Backup configs**: Version control your configuration files
6. **Validate**: Run validation before deployment
7. **Environment-specific**: Use different configs for dev/test/prod

---

## Next Steps

- **Installation**: [INSTALLATION.md](INSTALLATION.md)
- **User Manual**: [USER_MANUAL.md](USER_MANUAL.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

**Document Version**: 1.0.0
**Last Updated**: November 2025
