"""
Trinity Phase 2 - Database Models
SQLAlchemy ORM models for the AV testing platform
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text,
    ForeignKey, JSON, Enum, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


# ============================================================================
# Enumerations
# ============================================================================

class TestSessionStatus(enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABORTED = "aborted"
    PAUSED = "paused"


class ObjectClass(enum.Enum):
    PERSON = "person"
    BICYCLE = "bicycle"
    CAR = "car"
    MOTORCYCLE = "motorcycle"
    BUS = "bus"
    TRUCK = "truck"
    TRAFFIC_LIGHT = "traffic_light"
    STOP_SIGN = "stop_sign"
    DOG = "dog"
    CAT = "cat"
    DEER = "deer"
    CONE = "cone"
    BARRIER = "barrier"
    UNKNOWN = "unknown"


class EventType(enum.Enum):
    NEAR_MISS = "near_miss"
    COLLISION = "collision"
    HARD_BRAKE = "hard_brake"
    INTERVENTION = "intervention"
    EDGE_CASE = "edge_case"
    ANOMALY = "anomaly"
    RULE_VIOLATION = "rule_violation"
    DISENGAGEMENT = "disengagement"


class PerceptionMode(enum.Enum):
    MANUAL = "manual"
    AUTONOMOUS = "autonomous"
    DISENGAGED = "disengaged"


class ScenarioType(enum.Enum):
    INTERSECTION = "intersection"
    PEDESTRIAN_CROSSING = "pedestrian_crossing"
    LANE_CHANGE = "lane_change"
    PARKING = "parking"
    EMERGENCY_BRAKE = "emergency_brake"
    CUT_IN_CUT_OUT = "cut_in_cut_out"
    FREE_ROAM = "free_roam"
    CUSTOM = "custom"


# ============================================================================
# Core Models
# ============================================================================

class TestSession(Base):
    """Test session record"""
    __tablename__ = 'test_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime)
    duration_seconds = Column(Float)

    test_type = Column(Enum(ScenarioType), nullable=False)
    status = Column(Enum(TestSessionStatus), default=TestSessionStatus.ACTIVE)

    # Environmental conditions
    weather_condition = Column(String(100))
    lighting_condition = Column(String(100))
    temperature = Column(Float)

    # AV information
    av_vehicle_id = Column(String(100))
    av_license_plate = Column(String(20))
    safety_driver_id = Column(String(100))

    # Metadata
    notes = Column(Text)
    config_snapshot = Column(JSON)  # Configuration used for this session

    # Relationships
    detections = relationship("DetectedObject", back_populates="session", cascade="all, delete-orphan")
    tracks = relationship("Track", back_populates="session", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="session", cascade="all, delete-orphan")
    av_states = relationship("AVVehicleState", back_populates="session", cascade="all, delete-orphan")
    perception_validations = relationship("PerceptionValidation", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_test_sessions_start_time', 'start_time'),
        Index('idx_test_sessions_status', 'status'),
        Index('idx_test_sessions_av_vehicle_id', 'av_vehicle_id'),
    )


class Camera(Base):
    """Camera configuration and calibration"""
    __tablename__ = 'cameras'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    device_id = Column(Integer, nullable=False)

    # Position (world coordinates)
    position_x = Column(Float, nullable=False)
    position_y = Column(Float, nullable=False)
    position_z = Column(Float, nullable=False)

    # Orientation (roll, pitch, yaw in degrees)
    orientation_roll = Column(Float, default=0.0)
    orientation_pitch = Column(Float, default=0.0)
    orientation_yaw = Column(Float, default=0.0)

    # Calibration
    intrinsic_matrix = Column(JSON)  # 3x3 camera matrix
    distortion_coeffs = Column(JSON)  # Distortion coefficients
    extrinsic_matrix = Column(JSON)  # 4x4 transformation matrix

    # Camera settings
    resolution_width = Column(Integer, nullable=False)
    resolution_height = Column(Integer, nullable=False)
    fps = Column(Integer, nullable=False)

    calibration_date = Column(DateTime)
    calibration_error = Column(Float)  # Reprojection error

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    detections = relationship("DetectedObject", back_populates="camera")


class DetectedObject(Base):
    """Individual object detection in a frame"""
    __tablename__ = 'detected_objects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('test_sessions.id'), nullable=False)
    camera_id = Column(Integer, ForeignKey('cameras.id'), nullable=False)

    frame_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Detection information
    object_class = Column(Enum(ObjectClass), nullable=False)
    track_id = Column(Integer)  # Global track ID across cameras
    confidence = Column(Float, nullable=False)

    # 2D Bounding box (in image coordinates)
    bbox_x = Column(Float, nullable=False)
    bbox_y = Column(Float, nullable=False)
    bbox_width = Column(Float, nullable=False)
    bbox_height = Column(Float, nullable=False)

    # 3D World position
    world_position_x = Column(Float)
    world_position_y = Column(Float)
    world_position_z = Column(Float)

    # Motion
    velocity_x = Column(Float)
    velocity_y = Column(Float)
    speed = Column(Float)
    heading = Column(Float)  # Degrees

    # Additional attributes
    occlusion_level = Column(Integer)  # 0-3
    truncation = Column(Boolean, default=False)

    # Relationships
    session = relationship("TestSession", back_populates="detections")
    camera = relationship("Camera", back_populates="detections")

    __table_args__ = (
        Index('idx_detections_session_frame', 'session_id', 'frame_number'),
        Index('idx_detections_track_id', 'track_id'),
        Index('idx_detections_timestamp', 'timestamp'),
        Index('idx_detections_class', 'object_class'),
    )


class Track(Base):
    """Multi-frame object track"""
    __tablename__ = 'tracks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('test_sessions.id'), nullable=False)

    track_id = Column(Integer, nullable=False)  # Track ID within session
    object_class = Column(Enum(ObjectClass), nullable=False)

    # Lifecycle
    first_seen = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    total_frames = Column(Integer, nullable=False)
    total_cameras = Column(Integer)  # Number of cameras that saw this object

    # Trajectory (array of {timestamp, x, y, z, vx, vy, speed, heading})
    trajectory = Column(JSON, nullable=False)

    # Statistics
    average_speed = Column(Float)
    max_speed = Column(Float)
    min_speed = Column(Float)

    average_confidence = Column(Float)

    # Flags
    is_av_vehicle = Column(Boolean, default=False)
    is_static = Column(Boolean, default=False)

    # Metadata
    notes = Column(Text)

    # Relationships
    session = relationship("TestSession", back_populates="tracks")

    __table_args__ = (
        Index('idx_tracks_session_id', 'session_id'),
        Index('idx_tracks_track_id', 'track_id'),
        Index('idx_tracks_class', 'object_class'),
        Index('idx_tracks_is_av', 'is_av_vehicle'),
        UniqueConstraint('session_id', 'track_id', name='uq_session_track'),
    )


class AVVehicleState(Base):
    """Autonomous vehicle state snapshots"""
    __tablename__ = 'av_vehicle_state'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('test_sessions.id'), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Position and orientation
    position_x = Column(Float, nullable=False)
    position_y = Column(Float, nullable=False)
    position_z = Column(Float)
    heading = Column(Float)  # Degrees

    # Motion
    speed = Column(Float)  # m/s
    acceleration = Column(Float)  # m/s^2
    lateral_acceleration = Column(Float)

    # Control inputs
    steering_angle = Column(Float)  # Degrees
    brake_pressure = Column(Float)  # Percentage
    throttle_position = Column(Float)  # Percentage
    gear = Column(String(10))

    # Indicators
    turn_signal = Column(String(10))  # left, right, hazard, none

    # Mode
    perception_mode = Column(Enum(PerceptionMode), nullable=False)

    # Distance metrics
    distance_traveled = Column(Float)  # Cumulative distance in session

    # Relationships
    session = relationship("TestSession", back_populates="av_states")

    __table_args__ = (
        Index('idx_av_state_session_timestamp', 'session_id', 'timestamp'),
    )


class Event(Base):
    """Safety and edge case events"""
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('test_sessions.id'), nullable=False)

    event_type = Column(Enum(EventType), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    severity = Column(Integer, nullable=False)  # 1-5 scale

    description = Column(Text, nullable=False)

    # Involved objects (array of track IDs)
    involved_tracks = Column(JSON)

    # Metrics
    ttc = Column(Float)  # Time to collision (seconds)
    distance = Column(Float)  # Minimum distance (meters)
    relative_speed = Column(Float)  # Relative speed (m/s)

    # Location
    location_x = Column(Float)
    location_y = Column(Float)
    location_z = Column(Float)

    # Media
    video_clip_path = Column(String(500))
    snapshot_paths = Column(JSON)  # Array of image paths

    # Flags
    is_edge_case = Column(Boolean, default=False)
    requires_review = Column(Boolean, default=False)
    reviewed = Column(Boolean, default=False)
    reviewer_notes = Column(Text)

    # Relationships
    session = relationship("TestSession", back_populates="events")
    edge_case = relationship("EdgeCase", back_populates="event", uselist=False)

    __table_args__ = (
        Index('idx_events_session_id', 'session_id'),
        Index('idx_events_type', 'event_type'),
        Index('idx_events_severity', 'severity'),
        Index('idx_events_is_edge_case', 'is_edge_case'),
        Index('idx_events_timestamp', 'timestamp'),
    )


class EdgeCase(Base):
    """Detailed edge case analysis"""
    __tablename__ = 'edge_cases'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey('events.id'), unique=True, nullable=False)

    case_type = Column(String(100), nullable=False)

    # Environmental factors
    environmental_factors = Column(JSON)  # {weather, lighting, traffic_density, etc.}

    # AV response
    av_response = Column(String(50))  # success, failure, partial
    av_reaction_time = Column(Float)  # seconds

    # Analysis
    root_cause_analysis = Column(Text)
    contributing_factors = Column(JSON)  # Array of factors

    # Reproducibility
    reproducibility_score = Column(Float)  # 0.0-1.0
    reproduction_attempts = Column(Integer, default=0)
    reproduction_successes = Column(Integer, default=0)

    # CARLA export
    carla_scenario_path = Column(String(500))
    carla_scenario_generated = Column(Boolean, default=False)

    # Similar cases (for clustering)
    similar_cases = Column(JSON)  # Array of edge_case IDs
    cluster_id = Column(Integer)

    # Review status
    reviewed = Column(Boolean, default=False)
    reviewer_id = Column(String(100))
    reviewer_notes = Column(Text)
    review_date = Column(DateTime)

    # Priority
    priority = Column(Integer)  # 1-5, with 5 being highest

    # Relationships
    event = relationship("Event", back_populates="edge_case")

    __table_args__ = (
        Index('idx_edge_cases_case_type', 'case_type'),
        Index('idx_edge_cases_reproducibility', 'reproducibility_score'),
        Index('idx_edge_cases_cluster', 'cluster_id'),
        Index('idx_edge_cases_priority', 'priority'),
    )


class PerceptionValidation(Base):
    """Comparison between ground truth and AV perception"""
    __tablename__ = 'perception_validation'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('test_sessions.id'), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    frame_number = Column(Integer, nullable=False)

    # Ground truth objects (from infrastructure cameras)
    ground_truth_objects = Column(JSON, nullable=False)

    # AV detected objects
    av_detected_objects = Column(JSON, nullable=False)

    # Matching results
    matched_pairs = Column(JSON)  # Array of {gt_id, av_id, iou, distance, etc.}

    # Metrics
    true_positives = Column(Integer, nullable=False)
    false_positives = Column(Integer, nullable=False)
    false_negatives = Column(Integer, nullable=False)

    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)

    # Localization errors
    avg_position_error = Column(Float)  # meters
    avg_velocity_error = Column(Float)  # m/s
    avg_heading_error = Column(Float)  # degrees

    # Per-class metrics
    class_metrics = Column(JSON)

    # Relationships
    session = relationship("TestSession", back_populates="perception_validations")

    __table_args__ = (
        Index('idx_perception_validation_session', 'session_id'),
        Index('idx_perception_validation_timestamp', 'timestamp'),
    )


class Scenario(Base):
    """Test scenario definitions"""
    __tablename__ = 'scenarios'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)

    scenario_type = Column(Enum(ScenarioType), nullable=False)

    # Parameters
    parameters = Column(JSON, nullable=False)  # Scenario-specific parameters

    # Pass/fail criteria
    pass_criteria = Column(JSON, nullable=False)

    # CARLA scenario
    carla_scenario_path = Column(String(500))

    # Metadata
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Statistics
    times_executed = Column(Integer, default=0)
    times_passed = Column(Integer, default=0)
    times_failed = Column(Integer, default=0)
    success_rate = Column(Float)

    # Tags for organization
    tags = Column(JSON)  # Array of tags

    is_active = Column(Boolean, default=True)


class Annotation(Base):
    """Manual annotations for dataset creation"""
    __tablename__ = 'annotations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('test_sessions.id'), nullable=False)
    camera_id = Column(Integer, ForeignKey('cameras.id'), nullable=False)

    frame_number = Column(Integer, nullable=False)

    # Object information
    object_id = Column(Integer)  # Track ID if available
    object_class = Column(Enum(ObjectClass), nullable=False)

    # 2D Bounding box
    bbox_x = Column(Float, nullable=False)
    bbox_y = Column(Float, nullable=False)
    bbox_width = Column(Float, nullable=False)
    bbox_height = Column(Float, nullable=False)

    # 3D Bounding box (optional)
    bbox_3d = Column(JSON)  # {center: [x,y,z], dimensions: [l,w,h], rotation: yaw}

    # Attributes
    occlusion_level = Column(Integer, default=0)  # 0-3
    truncation = Column(Boolean, default=False)
    pose = Column(String(50))  # standing, sitting, etc.

    # Quality
    is_crowd = Column(Boolean, default=False)
    is_occluded = Column(Boolean, default=False)
    is_difficult = Column(Boolean, default=False)

    # Annotation metadata
    annotator_id = Column(String(100), nullable=False)
    annotation_timestamp = Column(DateTime, default=datetime.utcnow)
    annotation_time_seconds = Column(Float)  # Time taken to annotate

    # Validation
    is_validated = Column(Boolean, default=False)
    validator_id = Column(String(100))
    validation_timestamp = Column(DateTime)
    validation_notes = Column(Text)

    __table_args__ = (
        Index('idx_annotations_session_frame', 'session_id', 'frame_number'),
        Index('idx_annotations_class', 'object_class'),
        Index('idx_annotations_validated', 'is_validated'),
    )


class Dataset(Base):
    """Dataset exports for ML training"""
    __tablename__ = 'datasets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)

    # Source sessions
    sessions = Column(JSON, nullable=False)  # Array of session IDs

    # Statistics
    total_frames = Column(Integer, nullable=False)
    total_annotations = Column(Integer, nullable=False)
    total_objects = Column(Integer, nullable=False)

    # Class distribution
    class_distribution = Column(JSON)

    # Splits
    train_split_percentage = Column(Float, nullable=False)
    val_split_percentage = Column(Float, nullable=False)
    test_split_percentage = Column(Float, nullable=False)

    train_frames = Column(Integer)
    val_frames = Column(Integer)
    test_frames = Column(Integer)

    # Export
    export_format = Column(String(50), nullable=False)  # coco, kitti, nuscenes, custom
    export_path = Column(String(500))

    # Metadata
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Version control
    version = Column(String(50))
    parent_dataset_id = Column(Integer, ForeignKey('datasets.id'))

    # Flags
    is_published = Column(Boolean, default=False)

    __table_args__ = (
        Index('idx_datasets_name', 'name'),
        Index('idx_datasets_format', 'export_format'),
    )


class SystemMetrics(Base):
    """System performance metrics"""
    __tablename__ = 'system_metrics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Processing performance
    detection_fps = Column(Float)
    tracking_fps = Column(Float)
    overall_fps = Column(Float)

    # Latency
    camera_latency_ms = Column(Float)
    detection_latency_ms = Column(Float)
    tracking_latency_ms = Column(Float)
    total_latency_ms = Column(Float)

    # Resource usage
    cpu_usage_percent = Column(Float)
    gpu_usage_percent = Column(Float)
    memory_usage_gb = Column(Float)
    gpu_memory_usage_gb = Column(Float)
    disk_usage_gb = Column(Float)

    # Camera health
    active_cameras = Column(Integer)
    frame_drop_count = Column(Integer)

    # Database
    database_size_gb = Column(Float)

    __table_args__ = (
        Index('idx_system_metrics_timestamp', 'timestamp'),
    )


# ============================================================================
# Helper Functions
# ============================================================================

def init_database(engine):
    """Initialize database schema"""
    Base.metadata.create_all(engine)


def drop_database(engine):
    """Drop all tables (use with caution!)"""
    Base.metadata.drop_all(engine)
