# Trinity Phase 2 - API Reference

Complete REST API and WebSocket documentation for Trinity AV Testing Platform.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [REST API Endpoints](#rest-api-endpoints)
  - [Health & Status](#health--status)
  - [Sessions](#sessions)
  - [Detection](#detection)
  - [Tracking](#tracking)
  - [Metrics](#metrics)
  - [Reports](#reports)
  - [Edge Cases](#edge-cases)
  - [Datasets](#datasets)
- [WebSocket API](#websocket-api)
- [Data Models](#data-models)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)

---

## Overview

Trinity provides a RESTful API and WebSocket interface for programmatic access to all platform features.

**Base Features**:
- RESTful API with JSON responses
- WebSocket for real-time streaming
- OpenAPI/Swagger documentation
- Rate limiting and authentication
- CORS support for web clients

**Use Cases**:
- Remote monitoring and control
- Integration with CI/CD pipelines
- Custom dashboards and tools
- Automated testing workflows
- Data export and analysis

---

## Authentication

### API Key Authentication

All API requests require an API key in the header.

**Request Header**:
```http
X-API-Key: your_api_key_here
```

**Generating API Key**:
```bash
python -m trinity.api.generate_key --name "My Application"
```

**Example**:
```bash
curl -H "X-API-Key: abc123def456" http://localhost:8000/api/v1/sessions
```

### Token Authentication (Optional)

For enhanced security, use JWT tokens:

**Login**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

**Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Using Token**:
```bash
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  http://localhost:8000/api/v1/sessions
```

---

## Base URL

**Development**:
```
http://localhost:8000/api/v1
```

**Production** (configure in `config/api.yaml`):
```
https://your-domain.com/api/v1
```

**API Documentation**:
```
http://localhost:8000/docs          # Swagger UI
http://localhost:8000/redoc         # ReDoc
http://localhost:8000/openapi.json  # OpenAPI spec
```

---

## REST API Endpoints

### Health & Status

#### GET /health

Check API health status.

**Request**:
```bash
curl http://localhost:8000/api/v1/health
```

**Response**:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "uptime_seconds": 3600,
  "timestamp": "2025-11-22T10:30:00Z"
}
```

#### GET /status

Get system status and statistics.

**Request**:
```bash
curl http://localhost:8000/api/v1/status
```

**Response**:
```json
{
  "system": {
    "cpu_percent": 45.2,
    "memory_percent": 62.8,
    "gpu_percent": 78.5,
    "disk_free_gb": 125.4
  },
  "sessions": {
    "active": 1,
    "total": 42
  },
  "processing": {
    "fps": 28.5,
    "detection_time_ms": 18.2,
    "tracking_time_ms": 5.3
  }
}
```

---

### Sessions

#### GET /sessions

List all sessions with optional filtering.

**Parameters**:
- `limit` (int): Maximum number of results (default: 50)
- `offset` (int): Offset for pagination (default: 0)
- `status` (str): Filter by status (active/completed/failed)
- `start_date` (str): Filter by start date (ISO 8601)
- `end_date` (str): Filter by end date (ISO 8601)

**Request**:
```bash
curl "http://localhost:8000/api/v1/sessions?limit=10&status=completed"
```

**Response**:
```json
{
  "total": 42,
  "limit": 10,
  "offset": 0,
  "sessions": [
    {
      "id": "session_001",
      "name": "Highway Test - Sunny Day",
      "status": "completed",
      "start_time": "2025-11-22T09:00:00Z",
      "end_time": "2025-11-22T10:30:00Z",
      "duration_seconds": 5400,
      "cameras": [1, 2],
      "detections_count": 15420,
      "tracks_count": 342,
      "events_count": 28,
      "edge_cases_count": 12
    }
  ]
}
```

#### POST /sessions/start

Start a new recording session.

**Request Body**:
```json
{
  "name": "Test Session",
  "description": "Testing new detection model",
  "location": "Test Track A",
  "cameras": [1, 2, 3],
  "config": {
    "detection_enabled": true,
    "tracking_enabled": true,
    "edge_case_detection": true,
    "video_codec": "h264",
    "video_quality": "high"
  }
}
```

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/sessions/start \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_key" \
  -d @session_config.json
```

**Response**:
```json
{
  "session_id": "session_042",
  "status": "recording",
  "start_time": "2025-11-22T11:00:00Z",
  "cameras_active": [1, 2, 3],
  "message": "Session started successfully"
}
```

#### POST /sessions/{session_id}/stop

Stop an active recording session.

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/sessions/session_042/stop \
  -H "X-API-Key: your_key"
```

**Response**:
```json
{
  "session_id": "session_042",
  "status": "completed",
  "end_time": "2025-11-22T12:00:00Z",
  "duration_seconds": 3600,
  "stats": {
    "frames_processed": 108000,
    "detections": 12450,
    "tracks": 287,
    "events": 15,
    "edge_cases": 8
  }
}
```

#### GET /sessions/{session_id}

Get detailed session information.

**Request**:
```bash
curl http://localhost:8000/api/v1/sessions/session_042
```

**Response**:
```json
{
  "id": "session_042",
  "name": "Test Session",
  "status": "completed",
  "start_time": "2025-11-22T11:00:00Z",
  "end_time": "2025-11-22T12:00:00Z",
  "duration_seconds": 3600,
  "location": "Test Track A",
  "cameras": [
    {
      "id": 1,
      "name": "Front Camera",
      "frames_captured": 108000,
      "resolution": [1920, 1080]
    }
  ],
  "statistics": {
    "detections_by_class": {
      "car": 8420,
      "person": 2150,
      "bicycle": 1880
    },
    "avg_fps": 28.5,
    "avg_detection_time_ms": 18.2,
    "tracks_created": 287,
    "events": 15,
    "edge_cases": 8
  },
  "files": {
    "videos": [
      "/data/sessions/session_042/camera_1.mp4"
    ],
    "metadata": "/data/sessions/session_042/metadata.json",
    "detections": "/data/sessions/session_042/detections.json"
  }
}
```

#### DELETE /sessions/{session_id}

Delete a session and all associated data.

**Request**:
```bash
curl -X DELETE http://localhost:8000/api/v1/sessions/session_042 \
  -H "X-API-Key: your_key"
```

**Response**:
```json
{
  "message": "Session deleted successfully",
  "session_id": "session_042"
}
```

---

### Detection

#### POST /detection/detect

Run detection on a single image or frame.

**Request Body** (multipart/form-data):
```
image: <file>
model: yolov8n
confidence: 0.25
device: cuda:0
```

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/detection/detect \
  -F "image=@test_image.jpg" \
  -F "model=yolov8n" \
  -F "confidence=0.25"
```

**Response**:
```json
{
  "detections": [
    {
      "class": "car",
      "confidence": 0.89,
      "bbox": [100, 150, 300, 400],
      "bbox_normalized": [0.1, 0.15, 0.3, 0.4]
    },
    {
      "class": "person",
      "confidence": 0.76,
      "bbox": [450, 200, 550, 500],
      "bbox_normalized": [0.45, 0.2, 0.55, 0.5]
    }
  ],
  "processing_time_ms": 18.5,
  "image_size": [1920, 1080]
}
```

#### GET /detection/models

List available detection models.

**Request**:
```bash
curl http://localhost:8000/api/v1/detection/models
```

**Response**:
```json
{
  "models": [
    {
      "name": "yolov8n",
      "size_mb": 6.3,
      "speed": "fast",
      "accuracy": "medium"
    },
    {
      "name": "yolov8s",
      "size_mb": 22.5,
      "speed": "medium",
      "accuracy": "good"
    },
    {
      "name": "yolov8m",
      "size_mb": 52.0,
      "speed": "medium",
      "accuracy": "high"
    }
  ]
}
```

---

### Tracking

#### GET /tracking/tracks

Get current active tracks.

**Request**:
```bash
curl http://localhost:8000/api/v1/tracking/tracks
```

**Response**:
```json
{
  "tracks": [
    {
      "track_id": 1,
      "class": "car",
      "state": "active",
      "age": 45,
      "hits": 42,
      "current_bbox": [120, 160, 320, 420],
      "velocity": [2.5, 0.3],
      "position_3d": [5.2, 12.3, 0.0]
    }
  ],
  "total_active": 12
}
```

#### GET /tracking/trajectories/{track_id}

Get trajectory for a specific track.

**Request**:
```bash
curl http://localhost:8000/api/v1/tracking/trajectories/1
```

**Response**:
```json
{
  "track_id": 1,
  "class": "car",
  "trajectory": [
    {
      "frame": 100,
      "timestamp": "2025-11-22T11:00:05.000Z",
      "bbox": [100, 150, 300, 400],
      "position_3d": [5.0, 12.0, 0.0],
      "velocity": [2.5, 0.3]
    }
  ],
  "total_points": 45
}
```

---

### Metrics

#### GET /metrics/current

Get current real-time metrics.

**Request**:
```bash
curl http://localhost:8000/api/v1/metrics/current
```

**Response**:
```json
{
  "timestamp": "2025-11-22T11:05:30Z",
  "fps": 28.5,
  "detection_time_ms": 18.2,
  "tracking_time_ms": 5.3,
  "total_pipeline_time_ms": 23.5,
  "detections_count": 45,
  "tracks_count": 12,
  "events_count": 3,
  "edge_cases_count": 1,
  "min_ttc": 4.2
}
```

#### GET /metrics/history

Get historical metrics.

**Parameters**:
- `metric` (str): Metric type (fps, detection_time, etc.)
- `start_time` (str): Start time (ISO 8601)
- `end_time` (str): End time (ISO 8601)
- `interval` (str): Aggregation interval (1s, 1m, 1h)

**Request**:
```bash
curl "http://localhost:8000/api/v1/metrics/history?metric=fps&interval=1m"
```

**Response**:
```json
{
  "metric": "fps",
  "interval": "1m",
  "data": [
    {
      "timestamp": "2025-11-22T11:00:00Z",
      "value": 28.5,
      "min": 25.2,
      "max": 30.1,
      "avg": 28.5
    }
  ]
}
```

---

### Reports

#### POST /reports/generate

Generate a session report.

**Request Body**:
```json
{
  "session_id": "session_042",
  "format": "pdf",
  "sections": [
    "executive_summary",
    "detection_stats",
    "safety_analysis",
    "edge_cases"
  ],
  "include_visualizations": true
}
```

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/reports/generate \
  -H "Content-Type: application/json" \
  -d @report_config.json
```

**Response**:
```json
{
  "report_id": "report_123",
  "status": "generating",
  "estimated_time_seconds": 30
}
```

#### GET /reports/{report_id}

Get report generation status or download.

**Request**:
```bash
curl http://localhost:8000/api/v1/reports/report_123
```

**Response** (in progress):
```json
{
  "report_id": "report_123",
  "status": "generating",
  "progress_percent": 45
}
```

**Response** (completed):
```json
{
  "report_id": "report_123",
  "status": "completed",
  "download_url": "/api/v1/reports/report_123/download",
  "file_size_mb": 12.5,
  "generated_at": "2025-11-22T11:10:00Z"
}
```

#### GET /reports/{report_id}/download

Download generated report.

**Request**:
```bash
curl -O http://localhost:8000/api/v1/reports/report_123/download
```

---

### Edge Cases

#### GET /edge-cases

List detected edge cases.

**Parameters**:
- `session_id` (str): Filter by session
- `category` (str): Filter by category
- `severity` (str): Filter by severity (low/medium/high/critical)
- `limit` (int): Maximum results

**Request**:
```bash
curl "http://localhost:8000/api/v1/edge-cases?session_id=session_042&severity=high"
```

**Response**:
```json
{
  "edge_cases": [
    {
      "id": "ec_001",
      "session_id": "session_042",
      "category": "occlusion",
      "severity": "high",
      "confidence": 0.92,
      "timestamp": "2025-11-22T11:15:30Z",
      "frame_number": 27900,
      "description": "Complete occlusion of vehicle by truck",
      "clip_url": "/api/v1/edge-cases/ec_001/clip",
      "thumbnail_url": "/api/v1/edge-cases/ec_001/thumbnail"
    }
  ],
  "total": 8
}
```

#### GET /edge-cases/{edge_case_id}/clip

Download edge case video clip.

**Request**:
```bash
curl -O http://localhost:8000/api/v1/edge-cases/ec_001/clip
```

---

### Datasets

#### POST /datasets/export

Export session data in various formats.

**Request Body**:
```json
{
  "session_id": "session_042",
  "format": "coco",
  "split": "train",
  "include_images": true,
  "include_annotations": true
}
```

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/datasets/export \
  -H "Content-Type: application/json" \
  -d @export_config.json
```

**Response**:
```json
{
  "export_id": "export_789",
  "status": "processing",
  "estimated_time_seconds": 120
}
```

#### GET /datasets/{export_id}

Check export status or download.

**Request**:
```bash
curl http://localhost:8000/api/v1/datasets/export_789
```

**Response**:
```json
{
  "export_id": "export_789",
  "status": "completed",
  "download_url": "/api/v1/datasets/export_789/download",
  "file_size_mb": 450.2,
  "format": "coco"
}
```

---

## WebSocket API

Real-time data streaming via WebSocket.

### Connection

**Endpoint**: `ws://localhost:8000/ws/{stream_type}`

**Stream Types**:
- `detections`: Real-time detection results
- `tracking`: Active tracks
- `metrics`: System metrics
- `events`: Safety events and edge cases

### Example: Detections Stream

```python
import asyncio
import websockets
import json

async def stream_detections():
    uri = "ws://localhost:8000/ws/detections"

    async with websockets.connect(uri) as websocket:
        # Send subscription message
        await websocket.send(json.dumps({
            "action": "subscribe",
            "filters": {
                "classes": ["car", "person"],
                "min_confidence": 0.5
            }
        }))

        # Receive detections
        while True:
            message = await websocket.recv()
            data = json.loads(message)

            print(f"Frame {data['frame_number']}: {len(data['detections'])} detections")
            for det in data['detections']:
                print(f"  {det['class']}: {det['confidence']:.2f}")

asyncio.run(stream_detections())
```

### Example: Metrics Stream

```python
async def stream_metrics():
    uri = "ws://localhost:8000/ws/metrics"

    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({
            "action": "subscribe",
            "interval_ms": 1000  # Update every second
        }))

        while True:
            message = await websocket.recv()
            metrics = json.loads(message)

            print(f"FPS: {metrics['fps']:.1f}, "
                  f"Detections: {metrics['detections_count']}, "
                  f"TTC: {metrics['min_ttc']:.1f}s")

asyncio.run(stream_metrics())
```

---

## Data Models

### Detection

```json
{
  "class": "string",
  "confidence": "float (0-1)",
  "bbox": "[x1, y1, x2, y2]",
  "bbox_normalized": "[x1, y1, x2, y2] (0-1)",
  "keypoints": "[[x, y, confidence], ...]",
  "segmentation": "[[x, y], ...]"
}
```

### Track

```json
{
  "track_id": "integer",
  "class": "string",
  "state": "active | lost | deleted",
  "age": "integer (frames)",
  "hits": "integer",
  "bbox": "[x1, y1, x2, y2]",
  "velocity": "[vx, vy]",
  "position_3d": "[x, y, z]"
}
```

### Session

```json
{
  "id": "string",
  "name": "string",
  "status": "active | paused | completed | failed",
  "start_time": "ISO 8601",
  "end_time": "ISO 8601",
  "duration_seconds": "integer",
  "cameras": "[camera_id, ...]",
  "statistics": "object"
}
```

---

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": "Additional error details",
    "timestamp": "2025-11-22T11:00:00Z"
  }
}
```

### HTTP Status Codes

- `200 OK`: Success
- `201 Created`: Resource created
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Missing or invalid API key
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

### Common Error Codes

- `INVALID_INPUT`: Invalid request parameters
- `SESSION_NOT_FOUND`: Session ID not found
- `SESSION_ALREADY_ACTIVE`: Cannot start session (already active)
- `MODEL_NOT_FOUND`: Detection model not found
- `INSUFFICIENT_RESOURCES`: Not enough system resources
- `PROCESSING_FAILED`: Processing failed
- `RATE_LIMIT_EXCEEDED`: Too many requests

---

## Rate Limiting

Default limits:
- 100 requests per minute per API key
- 1000 requests per hour per API key

Headers returned:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1700654400
```

---

## Examples

### Python Client

```python
import requests

class TrinityClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}

    def start_session(self, name, cameras):
        response = requests.post(
            f"{self.base_url}/sessions/start",
            headers=self.headers,
            json={"name": name, "cameras": cameras}
        )
        return response.json()

    def get_metrics(self):
        response = requests.get(
            f"{self.base_url}/metrics/current",
            headers=self.headers
        )
        return response.json()

# Usage
client = TrinityClient("http://localhost:8000/api/v1", "your_api_key")
session = client.start_session("Test", [1, 2])
print(f"Session started: {session['session_id']}")
```

### JavaScript Client

```javascript
class TrinityClient {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
  }

  async startSession(name, cameras) {
    const response = await fetch(`${this.baseUrl}/sessions/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey
      },
      body: JSON.stringify({ name, cameras })
    });
    return response.json();
  }

  async getMetrics() {
    const response = await fetch(`${this.baseUrl}/metrics/current`, {
      headers: { 'X-API-Key': this.apiKey }
    });
    return response.json();
  }
}

// Usage
const client = new TrinityClient('http://localhost:8000/api/v1', 'your_api_key');
const session = await client.startSession('Test', [1, 2]);
console.log(`Session started: ${session.session_id}`);
```

---

**Document Version**: 1.0.0
**Last Updated**: November 2025
**API Version**: v1
