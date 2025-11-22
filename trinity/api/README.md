# Trinity REST API

FastAPI-based REST API with WebSocket support for the Trinity AV Testing Platform.

## Features

- **RESTful Endpoints** - Complete CRUD operations for all Trinity features
- **WebSocket Support** - Real-time updates for detections, events, and system status
- **Auto-Generated Documentation** - Interactive API docs at `/docs`
- **CORS Support** - Cross-origin resource sharing enabled
- **Type Safety** - Pydantic models for request/response validation

---

## Quick Start

### Installation

```bash
# Install API dependencies
pip install fastapi uvicorn websockets python-multipart

# Run the API server
python -m trinity.api.main

# Or use uvicorn directly
uvicorn trinity.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Access Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## API Endpoints

### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/sessions` | List all test sessions |
| POST | `/api/v1/sessions` | Create new session |
| GET | `/api/v1/sessions/{id}` | Get session details |
| DELETE | `/api/v1/sessions/{id}` | Delete session |

### Cameras

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/cameras` | List all cameras |
| GET | `/api/v1/cameras/{id}` | Get camera status |

### Detections

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/detections` | List detections (with filters) |
| GET | `/api/v1/detections/current` | Get current frame detections |

### Tracks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/tracks` | List object tracks |
| GET | `/api/v1/tracks/{id}` | Get track details |

### Safety & Events

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/safety/events` | List safety events |
| GET | `/api/v1/safety/metrics` | Get safety metrics |

### Edge Cases

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/edge-cases` | List edge cases |
| GET | `/api/v1/edge-cases/statistics` | Get statistics |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/system/status` | Get system status |
| GET | `/api/v1/system/stats` | Get detailed statistics |
| GET | `/health` | Health check |

---

## WebSocket Endpoints

### Main WebSocket

**Endpoint:** `ws://localhost:8000/ws`

**Subscribe to streams:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'subscribe',
        streams: ['detections', 'events', 'metrics']
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

### Detection Stream

**Endpoint:** `ws://localhost:8000/ws/detections`

Real-time detection updates at 10 Hz.

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/detections');

ws.onmessage = (event) => {
    const detections = JSON.parse(event.data);
    // {timestamp: "2025-11-22T...", detections: [...]}
};
```

### Events Stream

**Endpoint:** `ws://localhost:8000/ws/events`

Real-time safety event notifications.

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/events');

ws.onmessage = (event) => {
    const safetyEvent = JSON.parse(event.data);
    console.log('Safety Event:', safetyEvent);
};
```

---

## Usage Examples

### Python Client

```python
import requests
import json

API_BASE = "http://localhost:8000/api/v1"

# Create session
session_data = {
    "name": "Test Session 1",
    "test_type": "scenario",
    "description": "Lane change scenario",
    "av_vehicle_id": "AV001"
}

response = requests.post(f"{API_BASE}/sessions", json=session_data)
session = response.json()
print(f"Created session: {session['id']}")

# List detections
response = requests.get(f"{API_BASE}/detections", params={
    "session_id": session['id'],
    "class_name": "car",
    "limit": 50
})
detections = response.json()
print(f"Found {len(detections)} detections")

# Get system status
response = requests.get(f"{API_BASE}/system/status")
status = response.json()
print(f"System status: {status['status']}")
print(f"Uptime: {status['uptime_seconds']}s")
```

### JavaScript Client

```javascript
// Create session
const createSession = async () => {
    const response = await fetch('http://localhost:8000/api/v1/sessions', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            name: 'Test Session 1',
            test_type: 'scenario',
            av_vehicle_id: 'AV001'
        })
    });
    
    const session = await response.json();
    console.log('Created session:', session.id);
    return session;
};

// List cameras
const getCameras = async () => {
    const response = await fetch('http://localhost:8000/api/v1/cameras');
    const cameras = await response.json();
    
    cameras.forEach(cam => {
        console.log(`Camera ${cam.camera_id}: ${cam.fps} FPS, ${cam.resolution.join('x')}`);
    });
};

// WebSocket for real-time updates
const ws = new WebSocket('ws://localhost:8000/ws/detections');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(`Received ${data.detections.length} detections`);
};
```

### cURL Examples

```bash
# Health check
curl http://localhost:8000/health

# List sessions
curl http://localhost:8000/api/v1/sessions

# Create session
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Session",
    "test_type": "free_roam",
    "av_vehicle_id": "AV001"
  }'

# Get system status
curl http://localhost:8000/api/v1/system/status

# List edge cases with filters
curl "http://localhost:8000/api/v1/edge-cases?category=near_collision&min_score=0.7"
```

---

## Response Models

### SessionResponse

```json
{
  "id": 1,
  "name": "Test Session",
  "test_type": "free_roam",
  "start_time": "2025-11-22T10:30:00",
  "end_time": null,
  "status": "active",
  "av_vehicle_id": "AV001"
}
```

### DetectionResponse

```json
{
  "detection_id": 123,
  "session_id": 1,
  "camera_id": 0,
  "frame_number": 450,
  "class_name": "car",
  "confidence": 0.95,
  "bbox": [100, 200, 50, 80],
  "timestamp": "2025-11-22T10:30:15"
}
```

### SystemStatus

```json
{
  "status": "running",
  "version": "1.0.0",
  "active_session": 1,
  "cameras_active": 3,
  "total_cameras": 3,
  "detection_enabled": true,
  "tracking_enabled": true,
  "av_monitoring_enabled": true,
  "uptime_seconds": 3600.5
}
```

---

## Configuration

### CORS Settings

Edit `trinity/api/main.py` to configure allowed origins:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Server Settings

```bash
# Development mode with auto-reload
uvicorn trinity.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn trinity.api.main:app --host 0.0.0.0 --port 8000 --workers 4

# With HTTPS
uvicorn trinity.api.main:app --host 0.0.0.0 --port 443 \
  --ssl-keyfile=/path/to/key.pem \
  --ssl-certfile=/path/to/cert.pem
```

---

## Integration with Trinity

The API is designed to work with the Trinity platform. Full integration example:

```python
from trinity.core.camera_manager import CameraManager
from trinity.detection.detection_system import DetectionTrackingSystem
from trinity.av_monitoring.av_monitoring_system import AVMonitoringSystem
from trinity.api.main import app, manager as ws_manager

# Initialize Trinity systems
camera_manager = CameraManager(config)
detection_system = DetectionTrackingSystem(config)
av_monitoring = AVMonitoringSystem(config)

# In your main loop, broadcast updates via WebSocket
async def main_loop():
    while running:
        # Get detections
        frames = camera_manager.get_synchronized_frames()
        result = detection_system.process_frames(frames)
        
        # Broadcast to WebSocket clients
        await ws_manager.broadcast(json.dumps({
            'type': 'detections',
            'data': [
                {
                    'track_id': t.track_id,
                    'class_name': t.class_name,
                    'bbox': list(t.bbox),
                    'confidence': t.confidence
                }
                for t in result.global_tracks
            ]
        }))
```

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- **200** - Success
- **201** - Created
- **400** - Bad Request
- **404** - Not Found
- **500** - Internal Server Error

Error response format:

```json
{
  "detail": "Error description"
}
```

---

## Testing

```bash
# Install testing dependencies
pip install pytest httpx

# Run API tests
pytest tests/api/
```

---

## Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY trinity/ trinity/

CMD ["uvicorn", "trinity.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Systemd Service

```ini
[Unit]
Description=Trinity API Server
After=network.target

[Service]
Type=simple
User=trinity
WorkingDirectory=/opt/trinity
ExecStart=/opt/trinity/venv/bin/uvicorn trinity.api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Security Considerations

**Note:** This is a development API. For production deployment:

1. **Enable Authentication** - Add JWT or API key authentication
2. **Use HTTPS** - SSL/TLS encryption for all communication
3. **Rate Limiting** - Prevent abuse with rate limits
4. **Input Validation** - Validate all user inputs
5. **CORS** - Restrict to specific origins
6. **Logging** - Log all API access
7. **Secrets Management** - Use environment variables for sensitive data

---

## License

Copyright © 2025 Sherin-SEF-AI
Part of Trinity Phase 2 - Autonomous Vehicle Testing Platform
