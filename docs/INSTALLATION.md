# Trinity Phase 2 - Installation Guide

This guide provides detailed installation instructions for the Trinity AV Testing Platform.

## Table of Contents

- [System Requirements](#system-requirements)
- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
  - [Method 1: Standard Installation](#method-1-standard-installation)
  - [Method 2: Development Installation](#method-2-development-installation)
  - [Method 3: Docker Installation](#method-3-docker-installation)
- [Post-Installation Setup](#post-installation-setup)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Optional Components](#optional-components)

---

## System Requirements

### Minimum Requirements
- **OS**: Ubuntu 20.04+ / Windows 10+ / macOS 11+
- **CPU**: 4-core processor (Intel i5 or equivalent)
- **RAM**: 8 GB
- **GPU**: NVIDIA GPU with 4GB VRAM (for YOLO detection)
- **Storage**: 10 GB available space
- **Python**: 3.8 - 3.11

### Recommended Requirements
- **OS**: Ubuntu 22.04 LTS
- **CPU**: 8-core processor (Intel i7/i9 or AMD Ryzen 7/9)
- **RAM**: 16 GB or more
- **GPU**: NVIDIA RTX 3060 or better with 8GB+ VRAM
- **Storage**: 50 GB SSD
- **Python**: 3.10

### GPU Support
- NVIDIA GPU with CUDA support is **required** for real-time detection
- CUDA 11.8 or 12.1 recommended
- cuDNN 8.6+ required

---

## Prerequisites

### 1. Install Python

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3.10 python3.10-dev python3.10-venv
```

#### macOS
```bash
brew install python@3.10
```

#### Windows
Download and install Python 3.10 from [python.org](https://www.python.org/downloads/)

### 2. Install CUDA and cuDNN (for GPU support)

#### Ubuntu
```bash
# Install CUDA 12.1
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin
sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600
wget https://developer.download.nvidia.com/compute/cuda/12.1.0/local_installers/cuda-repo-ubuntu2204-12-1-local_12.1.0-530.30.02-1_amd64.deb
sudo dpkg -i cuda-repo-ubuntu2204-12-1-local_12.1.0-530.30.02-1_amd64.deb
sudo cp /var/cuda-repo-ubuntu2204-12-1-local/cuda-*-keyring.gpg /usr/share/keyrings/
sudo apt-get update
sudo apt-get -y install cuda
```

Add to `~/.bashrc`:
```bash
export PATH=/usr/local/cuda-12.1/bin${PATH:+:${PATH}}
export LD_LIBRARY_PATH=/usr/local/cuda-12.1/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
```

#### Windows
Download and install CUDA Toolkit from [NVIDIA Developer](https://developer.nvidia.com/cuda-downloads)

### 3. Install System Dependencies

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y \
    build-essential \
    cmake \
    git \
    libopencv-dev \
    python3-opencv \
    libqt6-dev \
    qt6-base-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1
```

#### macOS
```bash
brew install cmake opencv qt6
```

#### Windows
- Install Visual Studio 2019+ with C++ support
- Install CMake from [cmake.org](https://cmake.org/download/)

---

## Installation Methods

### Method 1: Standard Installation

This method is recommended for most users.

#### Step 1: Clone the Repository
```bash
git clone https://github.com/Sherin-SEF-AI/Trinity-Phase2.git
cd Trinity-Phase2
```

#### Step 2: Create Virtual Environment
```bash
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Step 3: Upgrade pip
```bash
pip install --upgrade pip setuptools wheel
```

#### Step 4: Install PyTorch with CUDA Support
```bash
# For CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# For CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# For CPU only (not recommended)
pip install torch torchvision torchaudio
```

Verify PyTorch installation:
```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA Available: {torch.cuda.is_available()}')"
```

#### Step 5: Install NumPy (specific version required)
```bash
# CRITICAL: Install NumPy 1.x first (lap package requires NumPy <2.0)
pip install "numpy<2.0"
```

#### Step 6: Install Core Dependencies
```bash
pip install -r requirements.txt
```

**Note**: If you encounter errors with the `lap` package:
```bash
# Install lap separately with verbose output
pip install lap==0.4.0 --verbose

# If compilation fails, install pre-built wheel:
pip install lap==0.4.0 --only-binary :all:
```

#### Step 7: Install Trinity Package
```bash
pip install -e .
```

#### Step 8: Download YOLO Models
```bash
# Create models directory
mkdir -p models/yolo

# Download YOLOv8 models
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -O models/yolo/yolov8n.pt
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt -O models/yolo/yolov8s.pt
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m.pt -O models/yolo/yolov8m.pt
```

---

### Method 2: Development Installation

For contributors and developers who want to modify the code.

#### Step 1-6: Same as Standard Installation

#### Step 7: Install Development Dependencies
```bash
pip install -r requirements-dev.txt
```

This installs additional tools:
- pytest (testing)
- black (code formatting)
- flake8 (linting)
- mypy (type checking)
- sphinx (documentation)

#### Step 8: Install Pre-commit Hooks
```bash
pip install pre-commit
pre-commit install
```

#### Step 9: Run Tests
```bash
pytest tests/
```

---

### Method 3: Docker Installation

For containerized deployment (Docker setup coming in Phase 6.4).

```bash
# Build the image
docker build -t trinity-phase2 .

# Run the container
docker run --gpus all -p 8000:8000 -v $(pwd)/data:/app/data trinity-phase2
```

---

## Post-Installation Setup

### 1. Initialize Database
```bash
python -c "from trinity.database.models import init_db; init_db('sqlite:///trinity.db')"
```

### 2. Create Configuration File
```bash
cp config/config.example.yaml config/config.yaml
```

Edit `config/config.yaml` with your settings (see [Configuration Guide](CONFIGURATION.md)).

### 3. Set Up Camera Configuration (Optional)
```bash
mkdir -p data/calibration
# Add your camera calibration files
```

### 4. Configure API Keys (Optional)
If using cloud storage or external services:
```bash
export TRINITY_CLOUD_KEY="your_api_key"
export TRINITY_CLOUD_SECRET="your_secret"
```

---

## Verification

### 1. Verify Installation
```bash
python -c "import trinity; print(trinity.__version__)"
```

### 2. Check GPU Access
```bash
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'GPU Count: {torch.cuda.device_count()}')"
```

### 3. Test YOLO Detection
```bash
python scripts/test_detection.py --model models/yolo/yolov8n.pt --source data/test_video.mp4
```

### 4. Run Basic Test
```bash
python -m trinity.main --mode test --duration 10
```

### 5. Launch GUI
```bash
python -m trinity.gui.main_window
```

### 6. Test REST API
```bash
# Terminal 1: Start API server
python -m trinity.api.server

# Terminal 2: Test endpoint
curl http://localhost:8000/api/v1/health
```

---

## Troubleshooting

### Issue 1: NumPy Version Conflict

**Error**: `ERROR: pip's dependency resolver does not currently take into account all the packages that are installed`

**Solution**:
```bash
pip uninstall numpy -y
pip install "numpy<2.0"
pip install -r requirements.txt
```

### Issue 2: lap Package Installation Fails

**Error**: `error: Microsoft Visual C++ 14.0 or greater is required`

**Solution (Windows)**:
1. Install Visual Studio Build Tools
2. Or use pre-built wheel:
```bash
pip install lap==0.4.0 --only-binary :all:
```

**Solution (Linux)**:
```bash
sudo apt install build-essential python3-dev
pip install lap==0.4.0
```

### Issue 3: PyQt6 Import Error

**Error**: `ImportError: libEGL.so.1: cannot open shared object file`

**Solution (Linux)**:
```bash
sudo apt install libxcb-xinerama0 libxcb-cursor0 libegl1
```

**Solution (macOS)**:
```bash
brew install qt6
```

### Issue 4: CUDA Out of Memory

**Error**: `RuntimeError: CUDA out of memory`

**Solutions**:
1. Use smaller YOLO model (yolov8n instead of yolov8m)
2. Reduce batch size in config
3. Lower camera resolution
4. Enable CPU fallback:
```python
# In config.yaml
detection:
  device: 'cpu'
```

### Issue 5: Camera Not Detected

**Error**: `Failed to open camera`

**Solution**:
```bash
# Linux: Check camera permissions
sudo usermod -a -G video $USER
# Log out and log back in

# Test camera
ls /dev/video*
v4l2-ctl --list-devices
```

### Issue 6: Slow Performance

**Symptoms**: FPS < 5

**Solutions**:
1. Verify GPU is being used:
```python
python -c "import torch; print(torch.cuda.is_available())"
```

2. Use faster YOLO model (yolov8n)
3. Reduce camera resolution to 1280x720
4. Disable unnecessary features:
```yaml
# In config.yaml
tracking:
  enabled: false  # Disable if only detection needed
analytics:
  enabled: false
```

### Issue 7: Database Locked

**Error**: `database is locked`

**Solution**:
```bash
# Close all Trinity instances
pkill -f trinity

# Remove lock file
rm trinity.db-journal

# Restart
python -m trinity.gui.main_window
```

---

## Optional Components

### 1. Install pyqtgraph for Enhanced Visualizations

```bash
pip install pyqtgraph
```

This enables high-performance real-time charts in the analytics dashboard.

### 2. Install CARLA Simulator (Phase 4.2 - Not yet implemented)

```bash
# Download CARLA 0.9.15
wget https://carla-releases.s3.us-east-005.backblazeb2.com/Linux/CARLA_0.9.15.tar.gz
tar -xzf CARLA_0.9.15.tar.gz -C ~/carla
```

### 3. Install Additional Export Format Support

```bash
# For nuScenes format
pip install nuscenes-devkit

# For additional 3D visualization
pip install open3d
```

### 4. Install Documentation Tools

```bash
pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints
```

Build documentation:
```bash
cd docs
make html
```

### 5. Install Monitoring Tools

```bash
# GPU monitoring
pip install gpustat
gpustat -i 1

# System monitoring
pip install psutil
```

---

## Next Steps

After successful installation:

1. **Read the User Manual**: [USER_MANUAL.md](USER_MANUAL.md)
2. **Configure the System**: [CONFIGURATION.md](CONFIGURATION.md)
3. **Run Your First Test**: See [Quick Start](../README.md#quick-start)
4. **Explore the API**: [API_REFERENCE.md](API_REFERENCE.md)

---

## Getting Help

- **GitHub Issues**: [Report a bug](https://github.com/Sherin-SEF-AI/Trinity-Phase2/issues)
- **Documentation**: [Full documentation](https://github.com/Sherin-SEF-AI/Trinity-Phase2/tree/main/docs)
- **Email**: sherin@sef-ai.com

---

## Version Information

- **Document Version**: 1.0.0
- **Last Updated**: November 2025
- **Trinity Version**: Phase 2 (72% complete)
