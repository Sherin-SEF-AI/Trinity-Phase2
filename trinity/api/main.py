"""
Trinity Phase 5 - FastAPI Application
REST API with WebSocket support for Trinity AV Testing Platform
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import asyncio
import json
from loguru import logger

# Import Trinity modules (these would be available when API is run)
from trinity.database.models import TestSession, Camera, DetectedObject, Track, Event
from trinity.database.queries import (
    get_all_sessions, get_session_by_id, create_test_session,
    get_session_detections, get_session_tracks
)

# Pydantic models for request/response
from pydantic import BaseModel, Field


# ============================================================================
# Pydantic Models
# ============================================================================

class SessionCreate(BaseModel):
    name: str
    test_type: str = "free_roam"
    description: Optional[str] = None
    av_vehicle_id: Optional[str] = None


class SessionResponse(BaseModel):
    id: int
    name: str
    test_type: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    av_vehicle_id: Optional[str]


class CameraStatus(BaseModel):
    camera_id: int
    name: str
    is_active: bool
    fps: float
    resolution: tuple[int, int]
    frame_count: int


class DetectionResponse(BaseModel):
    detection_id: int
    session_id: int
    camera_id: int
    frame_number: int
    class_name: str
    confidence: float
    bbox: List[float]  # [x, y, w, h]
    timestamp: datetime


class TrackResponse(BaseModel):
    track_id: int
    session_id: int
    object_class: str
    first_frame: int
    last_frame: int
    total_frames: int
    is_av_vehicle: bool
    trajectory: List[Dict]  # List of position dicts


class SafetyEventResponse(BaseModel):
    event_id: int
    event_type: str
    severity: str
    timestamp: datetime
    description: str
    involved_tracks: List[int]
    frame_number: int


class EdgeCaseResponse(BaseModel):
    edge_case_id: str
    category: str
    severity: str
    score: float
    timestamp: datetime
    description: str
    frame_number: int


class SystemStatus(BaseModel):
    status: str
    version: str
    active_session: Optional[int]
    cameras_active: int
    total_cameras: int
    detection_enabled: bool
    tracking_enabled: bool
    av_monitoring_enabled: bool
    uptime_seconds: float


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Trinity AV Testing API",
    description="REST API for Trinity Phase 2 - Autonomous Vehicle Testing & Validation Suite",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state (in production, use proper state management)
active_sessions = {}
websocket_connections = []
system_start_time = datetime.now()


# ============================================================================
# REST API Endpoints
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "message": "Trinity AV Testing API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "sessions": "/api/v1/sessions",
            "cameras": "/api/v1/cameras",
            "detections": "/api/v1/detections",
            "tracks": "/api/v1/tracks",
            "safety": "/api/v1/safety",
            "edge_cases": "/api/v1/edge-cases",
            "system": "/api/v1/system",
            "websocket": "/ws"
        }
    }


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


# Session Management
@app.get("/api/v1/sessions", response_model=List[SessionResponse], tags=["Sessions"])
async def list_sessions(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None
):
    """List all test sessions"""
    # In production, this would query the database
    # For now, return mock data
    sessions = []
    return sessions


@app.post("/api/v1/sessions", response_model=SessionResponse, tags=["Sessions"])
async def create_session(session: SessionCreate):
    """Create a new test session"""
    # In production, this would create a session in the database
    new_session = SessionResponse(
        id=1,
        name=session.name,
        test_type=session.test_type,
        start_time=datetime.now(),
        end_time=None,
        status="active",
        av_vehicle_id=session.av_vehicle_id
    )
    
    # Notify WebSocket clients
    await broadcast_message({
        "type": "session_created",
        "data": new_session.dict()
    })
    
    return new_session


@app.get("/api/v1/sessions/{session_id}", response_model=SessionResponse, tags=["Sessions"])
async def get_session(session_id: int):
    """Get session by ID"""
    # Mock response
    return SessionResponse(
        id=session_id,
        name=f"Session {session_id}",
        test_type="free_roam",
        start_time=datetime.now(),
        end_time=None,
        status="active",
        av_vehicle_id="AV001"
    )


@app.delete("/api/v1/sessions/{session_id}", tags=["Sessions"])
async def delete_session(session_id: int):
    """Delete a session"""
    return {"message": f"Session {session_id} deleted"}


# Camera Management
@app.get("/api/v1/cameras", response_model=List[CameraStatus], tags=["Cameras"])
async def list_cameras():
    """List all cameras and their status"""
    cameras = [
        CameraStatus(
            camera_id=i,
            name=f"Camera {i+1}",
            is_active=True,
            fps=30.0,
            resolution=(1920, 1080),
            frame_count=1000
        )
        for i in range(3)
    ]
    return cameras


@app.get("/api/v1/cameras/{camera_id}", response_model=CameraStatus, tags=["Cameras"])
async def get_camera(camera_id: int):
    """Get camera status"""
    return CameraStatus(
        camera_id=camera_id,
        name=f"Camera {camera_id}",
        is_active=True,
        fps=30.0,
        resolution=(1920, 1080),
        frame_count=1000
    )


# Detections
@app.get("/api/v1/detections", response_model=List[DetectionResponse], tags=["Detections"])
async def list_detections(
    session_id: Optional[int] = None,
    camera_id: Optional[int] = None,
    class_name: Optional[str] = None,
    limit: int = 100
):
    """List detections with optional filtering"""
    # Mock response
    return []


@app.get("/api/v1/detections/current", tags=["Detections"])
async def get_current_detections():
    """Get current frame detections from all cameras"""
    return {
        "timestamp": datetime.now().isoformat(),
        "cameras": [
            {
                "camera_id": i,
                "detections": []
            }
            for i in range(3)
        ]
    }


# Tracks
@app.get("/api/v1/tracks", response_model=List[TrackResponse], tags=["Tracks"])
async def list_tracks(
    session_id: Optional[int] = None,
    class_name: Optional[str] = None,
    is_av: Optional[bool] = None,
    limit: int = 100
):
    """List object tracks"""
    return []


@app.get("/api/v1/tracks/{track_id}", response_model=TrackResponse, tags=["Tracks"])
async def get_track(track_id: int):
    """Get track by ID"""
    return TrackResponse(
        track_id=track_id,
        session_id=1,
        object_class="car",
        first_frame=0,
        last_frame=100,
        total_frames=100,
        is_av_vehicle=False,
        trajectory=[]
    )


# Safety & Events
@app.get("/api/v1/safety/events", response_model=List[SafetyEventResponse], tags=["Safety"])
async def list_safety_events(
    session_id: Optional[int] = None,
    severity: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100
):
    """List safety events"""
    return []


@app.get("/api/v1/safety/metrics", tags=["Safety"])
async def get_safety_metrics(session_id: Optional[int] = None):
    """Get safety metrics for session"""
    return {
        "session_id": session_id,
        "total_events": 0,
        "by_severity": {},
        "by_type": {},
        "ttc_stats": {
            "min": None,
            "max": None,
            "avg": None
        }
    }


# Edge Cases
@app.get("/api/v1/edge-cases", response_model=List[EdgeCaseResponse], tags=["Edge Cases"])
async def list_edge_cases(
    session_id: Optional[int] = None,
    category: Optional[str] = None,
    min_score: Optional[float] = None,
    limit: int = 100
):
    """List detected edge cases"""
    return []


@app.get("/api/v1/edge-cases/statistics", tags=["Edge Cases"])
async def get_edge_case_statistics(session_id: Optional[int] = None):
    """Get edge case statistics"""
    return {
        "total_cases": 0,
        "by_category": {},
        "by_severity": {},
        "avg_score": 0.0
    }


# System Status
@app.get("/api/v1/system/status", response_model=SystemStatus, tags=["System"])
async def get_system_status():
    """Get system status"""
    uptime = (datetime.now() - system_start_time).total_seconds()
    
    return SystemStatus(
        status="running",
        version="1.0.0",
        active_session=None,
        cameras_active=3,
        total_cameras=3,
        detection_enabled=True,
        tracking_enabled=True,
        av_monitoring_enabled=True,
        uptime_seconds=uptime
    )


@app.get("/api/v1/system/stats", tags=["System"])
async def get_system_stats():
    """Get detailed system statistics"""
    return {
        "sessions": {
            "total": 0,
            "active": 0,
            "completed": 0
        },
        "detections": {
            "total": 0,
            "per_class": {}
        },
        "tracks": {
            "total": 0,
            "active": 0
        },
        "performance": {
            "avg_fps": 30.0,
            "detection_latency_ms": 50.0,
            "tracking_latency_ms": 15.0
        }
    }


# ============================================================================
# WebSocket Support
# ============================================================================

class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific client"""
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "subscribe":
                # Subscribe to specific data streams
                streams = message.get("streams", [])
                await websocket.send_json({
                    "type": "subscribed",
                    "streams": streams
                })
            
            elif message.get("type") == "ping":
                # Heartbeat
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.websocket("/ws/detections")
async def websocket_detections(websocket: WebSocket):
    """WebSocket for real-time detection updates"""
    await websocket.accept()
    
    try:
        while True:
            # Send detection updates (mock data)
            detections = {
                "timestamp": datetime.now().isoformat(),
                "detections": []
            }
            await websocket.send_json(detections)
            await asyncio.sleep(0.1)  # 10 Hz updates
            
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket for real-time safety events"""
    await websocket.accept()
    
    try:
        while True:
            await asyncio.sleep(1)  # Wait for events
            
    except WebSocketDisconnect:
        pass


# ============================================================================
# Helper Functions
# ============================================================================

async def broadcast_message(message: Dict[str, Any]):
    """Broadcast message to all WebSocket clients"""
    message_str = json.dumps(message)
    await manager.broadcast(message_str)


# ============================================================================
# Startup & Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Execute on application startup"""
    logger.info("Trinity API starting up...")
    logger.info(f"API documentation available at: http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Execute on application shutdown"""
    logger.info("Trinity API shutting down...")
    
    # Close all WebSocket connections
    for connection in manager.active_connections:
        await connection.close()


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "trinity.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
