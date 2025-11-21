# Trinity Phase 2 - Main Application Dockerfile
FROM nvidia/cuda:12.3.0-cudnn8-devel-ubuntu22.04

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    CUDA_HOME=/usr/local/cuda \
    PATH=/usr/local/cuda/bin:$PATH \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-dev \
    python3-opencv \
    git \
    wget \
    curl \
    build-essential \
    cmake \
    pkg-config \
    libssl-dev \
    # Qt6 dependencies
    qt6-base-dev \
    libqt6widgets6 \
    libqt6gui6 \
    libqt6core6 \
    libxcb-xinerama0 \
    libxkbcommon-x11-0 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    # Video and camera dependencies
    ffmpeg \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    v4l-utils \
    # OpenCV dependencies
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libgtk-3-dev \
    # 3D visualization dependencies
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    freeglut3-dev \
    # PostgreSQL client
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python3 -m pip install --upgrade pip setuptools wheel

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install PyTorch with CUDA support
RUN pip install torch==2.2.0 torchvision==0.17.0 --index-url https://download.pytorch.org/whl/cu121

# Copy application code
COPY . .

# Install the package in development mode
RUN pip install -e .

# Create necessary directories
RUN mkdir -p /app/data /app/recordings /app/exports /app/logs /app/models/weights

# Download YOLOv8 model (optional, can be done at runtime)
RUN python3 -c "from ultralytics import YOLO; YOLO('yolov8x.pt')" || true

# Expose ports
EXPOSE 8000 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import cv2; print('OK')" || exit 1

# Entry point
CMD ["python3", "-m", "trinity.main"]
