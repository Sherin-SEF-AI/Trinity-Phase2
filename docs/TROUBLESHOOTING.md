# Trinity Phase 2 - Troubleshooting Guide

Comprehensive troubleshooting guide for the Trinity AV Testing Platform.

## Table of Contents

- [Quick Diagnosis](#quick-diagnosis)
- [Installation Issues](#installation-issues)
- [Camera Issues](#camera-issues)
- [Detection Issues](#detection-issues)
- [Performance Issues](#performance-issues)
- [Recording Issues](#recording-issues)
- [GUI Issues](#gui-issues)
- [API Issues](#api-issues)
- [Database Issues](#database-issues)
- [System Issues](#system-issues)
- [Getting Help](#getting-help)

---

## Quick Diagnosis

### Run System Check

```bash
python -m trinity.diagnostics.check_system
```

**Output**:
```
Trinity System Diagnostics
==========================

✓ Python version: 3.10.12
✓ CUDA available: Yes (12.1)
✓ GPU detected: NVIDIA RTX 3060 (12GB)
✗ PyQt6 import: Failed (missing dependency)
✓ Models found: yolov8n.pt, yolov8s.pt
✓ Database: Connected (SQLite)
✗ Camera 1: Connection failed

Summary: 2 issues found
```

### Check Logs

```bash
# View latest logs
tail -f logs/trinity.log

# Search for errors
grep ERROR logs/trinity.log

# View logs from specific date
grep "2025-11-22" logs/trinity.log
```

---

## Installation Issues

### Issue: NumPy Version Conflict

**Symptoms**:
- `pip` reports dependency conflicts
- Import errors mentioning NumPy
- `lap` package installation fails

**Error Message**:
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed
```

**Solution**:
```bash
# Uninstall all numpy versions
pip uninstall numpy -y

# Install compatible version
pip install "numpy<2.0"

# Reinstall requirements
pip install -r requirements.txt
```

**Verification**:
```bash
python -c "import numpy; print(numpy.__version__)"
# Should output: 1.26.x
```

---

### Issue: lap Package Compilation Fails

**Symptoms**:
- Error during `pip install lap`
- Missing compiler errors
- Link errors

**Error Message (Windows)**:
```
error: Microsoft Visual C++ 14.0 or greater is required
```

**Error Message (Linux)**:
```
error: command 'gcc' failed with exit status 1
```

**Solution (Windows)**:
1. Install Visual Studio Build Tools:
   - Download from: https://visualstudio.microsoft.com/downloads/
   - Select "Desktop development with C++"
   - Install

2. Or use pre-built wheel:
```bash
pip install lap==0.4.0 --only-binary :all:
```

**Solution (Linux)**:
```bash
# Ubuntu/Debian
sudo apt install build-essential python3-dev

# CentOS/RHEL
sudo yum install gcc gcc-c++ python3-devel

# Then install lap
pip install lap==0.4.0
```

**Verification**:
```bash
python -c "import lap; print('lap installed successfully')"
```

---

### Issue: PyTorch CUDA Not Available

**Symptoms**:
- `torch.cuda.is_available()` returns `False`
- Detection runs on CPU (very slow)

**Solution 1: Reinstall PyTorch with CUDA**:
```bash
# Uninstall current PyTorch
pip uninstall torch torchvision torchaudio -y

# Install with CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Or CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**Solution 2: Check CUDA Installation**:
```bash
# Check CUDA version
nvidia-smi

# Check CUDA compiler
nvcc --version

# Set CUDA paths (add to ~/.bashrc)
export PATH=/usr/local/cuda-12.1/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-12.1/lib64:$LD_LIBRARY_PATH
```

**Verification**:
```bash
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"
```

---

### Issue: PyQt6 Import Error

**Symptoms**:
- `ImportError: libEGL.so.1: cannot open shared object file`
- GUI fails to launch

**Solution (Ubuntu/Debian)**:
```bash
sudo apt install -y \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libegl1 \
    libxkbcommon-x11-0 \
    libgl1-mesa-glx
```

**Solution (Fedora/CentOS)**:
```bash
sudo dnf install -y \
    xcb-util-cursor \
    mesa-libEGL
```

**Solution (macOS)**:
```bash
brew install qt6
```

**Verification**:
```bash
python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK')"
```

---

## Camera Issues

### Issue: Camera Not Detected

**Symptoms**:
- "Failed to open camera" error
- No video feed in GUI

**Solution 1: Check Camera Connection**:
```bash
# Linux: List video devices
ls -l /dev/video*

# Check device info
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext
```

**Solution 2: Check Permissions (Linux)**:
```bash
# Add user to video group
sudo usermod -a -G video $USER

# Log out and log back in, then verify
groups | grep video
```

**Solution 3: Test Camera**:
```bash
# Using ffmpeg
ffmpeg -f v4l2 -list_formats all -i /dev/video0

# Using OpenCV
python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera Failed'); cap.release()"
```

---

### Issue: RTSP Stream Connection Failed

**Symptoms**:
- "RTSP connection timeout"
- No video from IP camera

**Solution 1: Verify RTSP URL**:
```bash
# Test with ffplay
ffplay rtsp://admin:password@192.168.1.100:554/stream1

# Test with VLC
vlc rtsp://admin:password@192.168.1.100:554/stream1
```

**Solution 2: Check Network**:
```bash
# Ping camera
ping 192.168.1.100

# Check port
nc -zv 192.168.1.100 554

# Check firewall
sudo ufw status
```

**Solution 3: Try Alternative URLs**:
```
# Common RTSP URL patterns:
rtsp://ip:port/stream1
rtsp://ip:port/h264
rtsp://ip:port/live/0/main
rtsp://ip:port/cam/realmonitor?channel=1&subtype=0

# With authentication:
rtsp://username:password@ip:port/stream1
```

**Solution 4: Increase Timeout**:
```yaml
# In config/cameras.yaml
cameras:
  - id: 1
    stream:
      timeout_sec: 30  # Increase timeout
      buffer_size: 20
      transport: "tcp"  # Try TCP instead of UDP
```

---

### Issue: Low Quality or Choppy Video

**Symptoms**:
- Pixelated video
- Frame drops
- Stuttering

**Solution 1: Adjust Buffer Size**:
```yaml
cameras:
  - id: 1
    stream:
      buffer_size: 30  # Increase buffer
```

**Solution 2: Lower Resolution**:
```yaml
cameras:
  - id: 1
    resolution:
      width: 1280  # Down from 1920
      height: 720  # Down from 1080
```

**Solution 3: Check Network Bandwidth**:
```bash
# Test bandwidth to camera
iperf3 -c 192.168.1.100

# Check network latency
ping -c 100 192.168.1.100 | tail -n 3
```

---

## Detection Issues

### Issue: No Detections

**Symptoms**:
- Detection count stays at 0
- No bounding boxes shown

**Solution 1: Lower Confidence Threshold**:
```yaml
detection:
  conf_threshold: 0.15  # Lower from 0.25
```

**Solution 2: Check Model Path**:
```bash
# Verify model exists
ls -lh models/yolo/yolov8n.pt

# Re-download if needed
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -O models/yolo/yolov8n.pt
```

**Solution 3: Test with Sample Image**:
```python
from ultralytics import YOLO

model = YOLO('models/yolo/yolov8n.pt')
results = model('path/to/test_image.jpg')

print(f"Detections: {len(results[0].boxes)}")
for box in results[0].boxes:
    print(f"Class: {box.cls}, Confidence: {box.conf}")
```

---

### Issue: Poor Detection Accuracy

**Symptoms**:
- Many false positives
- Missing obvious objects
- Incorrect classifications

**Solution 1: Use Larger Model**:
```yaml
detection:
  model: "yolov8m"  # Upgrade from yolov8n
  input_size: 1280   # Increase from 640
```

**Solution 2: Adjust Thresholds**:
```yaml
detection:
  conf_threshold: 0.30  # Increase to reduce false positives
  nms_threshold: 0.40   # Adjust NMS
```

**Solution 3: Improve Lighting**:
- Ensure adequate lighting for cameras
- Avoid direct sunlight/glare
- Use proper exposure settings

**Solution 4: Fine-tune on Your Data**:
```bash
# Export your data
python -m trinity.datasets.export --session session_001 --format coco

# Fine-tune YOLO (requires training script)
yolo train data=your_data.yaml model=yolov8n.pt epochs=50
```

---

### Issue: Detection Too Slow

**Symptoms**:
- FPS < 5
- High detection latency
- System lag

**Solution 1: Use Faster Model**:
```yaml
detection:
  model: "yolov8n"  # Fastest model
  input_size: 640    # Standard size
  half: true         # Enable FP16
```

**Solution 2: Verify GPU Usage**:
```bash
# Monitor GPU
nvidia-smi -l 1

# Check Trinity is using GPU
python -c "from trinity.detection import YOLODetector; det = YOLODetector(); print(f'Device: {det.device}')"
```

**Solution 3: Reduce Processing Load**:
```yaml
detection:
  max_det: 100  # Limit max detections

cameras:
  - id: 1
    resolution: {width: 1280, height: 720}  # Lower resolution
    fps: 20  # Reduce FPS
```

---

## Performance Issues

### Issue: Low FPS

**Symptoms**:
- FPS < 10
- Slow processing
- Delayed visualization

**Diagnosis**:
```bash
# Check system resources
htop

# Check GPU usage
nvidia-smi

# Profile Trinity
python -m trinity.main --profile --duration 30
```

**Solution 1: Optimize Detection**:
```yaml
detection:
  model: "yolov8n"
  input_size: 640
  half: true
  batch_size: 1

tracking:
  enabled: false  # Disable if not needed
```

**Solution 2: Reduce Cameras**:
```yaml
# Use fewer cameras simultaneously
cameras:
  - id: 1  # Only use one camera for testing
```

**Solution 3: Disable Analytics**:
```yaml
analytics:
  enabled: false  # Disable during recording
```

**Solution 4: Hardware Upgrade**:
- Consider faster GPU (RTX 3060 → RTX 4070+)
- Increase RAM (16GB minimum)
- Use SSD for storage

---

### Issue: High Memory Usage

**Symptoms**:
- System runs out of memory
- OOM (Out of Memory) errors
- System swap usage high

**Solution 1: Limit Buffer Sizes**:
```yaml
cameras:
  - id: 1
    stream:
      buffer_size: 5  # Reduce buffer

analytics:
  max_samples: 1000  # Reduce samples
  retention_seconds: 600  # Reduce retention
```

**Solution 2: Use Memory-Efficient Model**:
```yaml
detection:
  model: "yolov8n"  # Smallest model
  half: true        # FP16 uses less memory
```

**Solution 3: Monitor and Limit**:
```python
# Add to config
system:
  resources:
    max_memory_mb: 8192  # Limit memory usage
```

---

### Issue: GPU Out of Memory

**Symptoms**:
- `RuntimeError: CUDA out of memory`
- Detection fails intermittently

**Solution 1: Reduce Batch Size**:
```yaml
detection:
  batch_size: 1  # Process one image at a time
```

**Solution 2: Use Smaller Model**:
```yaml
detection:
  model: "yolov8n"  # Smallest model
  input_size: 640   # Reduce from 1280
```

**Solution 3: Enable Memory Management**:
```python
import torch
torch.cuda.empty_cache()  # Clear cache periodically
```

**Solution 4: Check Other Processes**:
```bash
# Check what's using GPU
nvidia-smi

# Kill other GPU processes
kill <PID>
```

---

## Recording Issues

### Issue: Video Not Saving

**Symptoms**:
- Recording completes but no video files
- Empty output directory

**Solution 1: Check Disk Space**:
```bash
df -h

# Trinity needs at least 10GB free
```

**Solution 2: Check Permissions**:
```bash
# Check write permissions
ls -ld data/sessions/

# Fix permissions
chmod -R 755 data/
```

**Solution 3: Verify Output Path**:
```yaml
recording:
  output_dir: "data/sessions"  # Ensure path exists

# Create if needed
mkdir -p data/sessions
```

---

### Issue: Corrupted Video Files

**Symptoms**:
- Video files won't play
- "File corrupted" errors
- Incomplete recordings

**Solution 1: Ensure Clean Stop**:
- Always use "Stop Recording" button
- Don't force quit during recording

**Solution 2: Use Reliable Codec**:
```yaml
recording:
  codec: "h264"  # Most compatible
  format: "mp4"
```

**Solution 3: Check Disk Health**:
```bash
# Check for disk errors
sudo smartctl -a /dev/sda

# Check filesystem
sudo fsck /dev/sda1
```

---

### Issue: Large File Sizes

**Symptoms**:
- Video files > 1GB/minute
- Disk fills up quickly

**Solution 1: Adjust Quality**:
```yaml
recording:
  quality: "medium"  # Down from "high"
  bitrate_mbps: 5    # Down from 10
```

**Solution 2: Use Better Compression**:
```yaml
recording:
  codec: "h265"  # Better compression than h264
```

**Solution 3: Lower Resolution**:
```yaml
cameras:
  - id: 1
    resolution: {width: 1280, height: 720}  # Down from 1080p
```

---

## GUI Issues

### Issue: GUI Won't Launch

**Symptoms**:
- Window doesn't appear
- Import errors
- Crashes on startup

**Solution 1: Check PyQt6**:
```bash
python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK')"
```

**Solution 2: Check Display**:
```bash
# Linux: Check DISPLAY variable
echo $DISPLAY

# If empty, set it
export DISPLAY=:0
```

**Solution 3: Run with Debug**:
```bash
python -m trinity.gui.main_window --debug
```

---

### Issue: GUI Freezing

**Symptoms**:
- Interface becomes unresponsive
- "Not Responding" message

**Solution 1: Reduce Update Rate**:
```yaml
analytics:
  update_interval_ms: 2000  # Increase from 1000
```

**Solution 2: Use Separate Thread**:
Already implemented in Trinity, but verify:
```python
# Detection runs in separate thread
# GUI should remain responsive
```

**Solution 3: Close Unused Windows**:
- Close analytics dashboard when not needed
- Minimize camera feeds

---

## API Issues

### Issue: API Not Starting

**Symptoms**:
- "Address already in use" error
- API server won't start

**Solution 1: Check Port**:
```bash
# Check if port 8000 is in use
sudo lsof -i :8000

# Kill process using port
kill <PID>
```

**Solution 2: Use Different Port**:
```yaml
api:
  server:
    port: 8080  # Change from 8000
```

**Solution 3: Check Firewall**:
```bash
# Ubuntu/Debian
sudo ufw allow 8000

# CentOS/RHEL
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

---

### Issue: API 401 Unauthorized

**Symptoms**:
- All requests return 401
- "Unauthorized" error

**Solution 1: Check API Key**:
```bash
# Generate new key
python -m trinity.api.generate_key --name "test"

# Use in request
curl -H "X-API-Key: your_key" http://localhost:8000/api/v1/health
```

**Solution 2: Disable Auth (Testing Only)**:
```yaml
api:
  auth:
    enabled: false  # ONLY for testing
```

---

## Database Issues

### Issue: Database Locked

**Symptoms**:
- "database is locked" error
- SQLite errors

**Solution 1: Close Other Instances**:
```bash
# Find Trinity processes
ps aux | grep trinity

# Kill all
pkill -f trinity
```

**Solution 2: Remove Lock File**:
```bash
# Only if no Trinity processes running
rm trinity.db-journal
rm trinity.db-wal
```

**Solution 3: Use PostgreSQL**:
```yaml
database:
  type: "postgresql"  # Better for concurrent access
  # ... postgres config
```

---

### Issue: Database Corruption

**Symptoms**:
- "database disk image is malformed"
- Data loss

**Solution 1: Backup and Restore**:
```bash
# Dump data
sqlite3 trinity.db .dump > backup.sql

# Create new database
rm trinity.db
sqlite3 trinity.db < backup.sql
```

**Solution 2: Integrity Check**:
```bash
sqlite3 trinity.db "PRAGMA integrity_check;"
```

---

## System Issues

### Issue: High CPU Usage

**Symptoms**:
- CPU at 100%
- System slowdown

**Solution 1: Limit Workers**:
```yaml
system:
  performance:
    num_workers: 2  # Reduce from 4
```

**Solution 2: Nice/Priority**:
```bash
# Run with lower priority
nice -n 10 python -m trinity.main
```

---

### Issue: Thermal Throttling

**Symptoms**:
- Performance degrades over time
- GPU frequency drops

**Solution 1: Monitor Temperatures**:
```bash
# GPU temperature
nvidia-smi --query-gpu=temperature.gpu --format=csv

# CPU temperature
sensors
```

**Solution 2: Improve Cooling**:
- Clean dust from fans
- Ensure proper airflow
- Use cooling pad (laptops)

**Solution 3: Limit GPU Power**:
```bash
# Limit GPU power to 150W (from 200W)
sudo nvidia-smi -pl 150
```

---

## Getting Help

### Collect Diagnostics

Before requesting support, collect diagnostics:

```bash
# Run full diagnostics
python -m trinity.diagnostics.collect_all

# Output: trinity_diagnostics_2025-11-22.zip
```

### Enable Debug Logging

```yaml
system:
  logging:
    level: "DEBUG"
    file: "logs/trinity_debug.log"
```

### Support Channels

1. **GitHub Issues**: https://github.com/Sherin-SEF-AI/Trinity-Phase2/issues
   - Search existing issues first
   - Provide diagnostics file
   - Include logs and error messages

2. **Email**: sherin@sef-ai.com
   - Attach diagnostics
   - Describe steps to reproduce
   - Include system information

3. **Documentation**: https://github.com/Sherin-SEF-AI/Trinity-Phase2/tree/main/docs
   - Check all relevant docs
   - Review FAQ sections

### Information to Provide

When requesting help, include:

1. **System Information**:
   - OS and version
   - Python version
   - GPU model and driver version
   - CUDA version

2. **Trinity Information**:
   - Trinity version
   - Configuration files
   - Diagnostics output

3. **Error Information**:
   - Complete error message
   - Stack trace
   - Steps to reproduce
   - Recent logs

4. **What You've Tried**:
   - Solutions attempted
   - Results of those attempts

---

## Common Error Messages

### Error: "Failed to load model"

**Cause**: Model file missing or corrupted

**Solution**:
```bash
# Re-download model
cd models/yolo
rm yolov8n.pt
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
```

---

### Error: "No module named 'trinity'"

**Cause**: Trinity not installed or wrong virtual environment

**Solution**:
```bash
# Activate virtual environment
source venv/bin/activate

# Install Trinity
pip install -e .
```

---

### Error: "CUDA error: out of memory"

**Cause**: GPU memory full

**Solution**: See [GPU Out of Memory](#issue-gpu-out-of-memory)

---

### Error: "Can't allocate write + execute memory"

**Cause**: macOS security restrictions

**Solution**:
```bash
# Allow PyTorch to use specific memory
export PYTORCH_ENABLE_MPS_FALLBACK=1
```

---

## Preventive Maintenance

### Regular Tasks

**Daily**:
- Check disk space
- Monitor system logs
- Verify backups

**Weekly**:
- Clear old sessions
- Update models if needed
- Check for updates

**Monthly**:
- Full system diagnostics
- Database optimization
- Performance benchmarking

### System Health Check

```bash
# Run weekly
python -m trinity.maintenance.check_health
```

---

**Document Version**: 1.0.0
**Last Updated**: November 2025
