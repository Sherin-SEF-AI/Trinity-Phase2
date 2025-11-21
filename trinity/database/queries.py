"""
Trinity Phase 2 - Database Query Helpers
Common database queries and operations
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from loguru import logger

from trinity.database.models import (
    TestSession, Camera, DetectedObject, Track, AVVehicleState,
    Event, EdgeCase, PerceptionValidation, Scenario, Annotation,
    Dataset, SystemMetrics, TestSessionStatus, ObjectClass, EventType
)


# ============================================================================
# Test Session Queries
# ============================================================================

def create_test_session(
    session: Session,
    name: str,
    test_type: str,
    description: Optional[str] = None,
    av_vehicle_id: Optional[str] = None,
    weather_condition: Optional[str] = None,
    lighting_condition: Optional[str] = None,
    **kwargs
) -> TestSession:
    """Create a new test session"""
    test_session = TestSession(
        name=name,
        description=description,
        test_type=test_type,
        av_vehicle_id=av_vehicle_id,
        weather_condition=weather_condition,
        lighting_condition=lighting_condition,
        status=TestSessionStatus.ACTIVE,
        **kwargs
    )
    session.add(test_session)
    session.commit()
    session.refresh(test_session)
    logger.info(f"Created test session: {name} (ID: {test_session.id})")
    return test_session


def end_test_session(session: Session, session_id: int) -> TestSession:
    """End a test session"""
    test_session = session.query(TestSession).filter_by(id=session_id).first()
    if test_session:
        test_session.end_time = datetime.utcnow()
        test_session.duration_seconds = (
            test_session.end_time - test_session.start_time
        ).total_seconds()
        test_session.status = TestSessionStatus.COMPLETED
        session.commit()
        logger.info(f"Ended test session {session_id} (Duration: {test_session.duration_seconds:.1f}s)")
    return test_session


def get_active_sessions(session: Session) -> List[TestSession]:
    """Get all active test sessions"""
    return session.query(TestSession).filter_by(
        status=TestSessionStatus.ACTIVE
    ).all()


def get_recent_sessions(session: Session, days: int = 7) -> List[TestSession]:
    """Get test sessions from the last N days"""
    since = datetime.utcnow() - timedelta(days=days)
    return session.query(TestSession).filter(
        TestSession.start_time >= since
    ).order_by(desc(TestSession.start_time)).all()


# ============================================================================
# Camera Queries
# ============================================================================

def get_active_cameras(session: Session) -> List[Camera]:
    """Get all active cameras"""
    return session.query(Camera).filter_by(is_active=True).all()


def get_camera_by_name(session: Session, name: str) -> Optional[Camera]:
    """Get camera by name"""
    return session.query(Camera).filter_by(name=name).first()


def update_camera_calibration(
    session: Session,
    camera_id: int,
    intrinsic_matrix: List[List[float]],
    distortion_coeffs: List[float],
    extrinsic_matrix: Optional[List[List[float]]] = None,
    calibration_error: Optional[float] = None
) -> Camera:
    """Update camera calibration data"""
    camera = session.query(Camera).filter_by(id=camera_id).first()
    if camera:
        camera.intrinsic_matrix = intrinsic_matrix
        camera.distortion_coeffs = distortion_coeffs
        if extrinsic_matrix:
            camera.extrinsic_matrix = extrinsic_matrix
        camera.calibration_error = calibration_error
        camera.calibration_date = datetime.utcnow()
        session.commit()
        logger.info(f"Updated calibration for camera {camera.name}")
    return camera


# ============================================================================
# Detection and Tracking Queries
# ============================================================================

def add_detection(
    session: Session,
    session_id: int,
    camera_id: int,
    frame_number: int,
    object_class: ObjectClass,
    bbox: tuple,
    confidence: float,
    track_id: Optional[int] = None,
    world_position: Optional[tuple] = None,
    velocity: Optional[tuple] = None,
    **kwargs
) -> DetectedObject:
    """Add a detected object"""
    detection = DetectedObject(
        session_id=session_id,
        camera_id=camera_id,
        frame_number=frame_number,
        object_class=object_class,
        bbox_x=bbox[0],
        bbox_y=bbox[1],
        bbox_width=bbox[2],
        bbox_height=bbox[3],
        confidence=confidence,
        track_id=track_id,
        timestamp=datetime.utcnow(),
        **kwargs
    )

    if world_position:
        detection.world_position_x = world_position[0]
        detection.world_position_y = world_position[1]
        detection.world_position_z = world_position[2]

    if velocity:
        detection.velocity_x = velocity[0]
        detection.velocity_y = velocity[1]

    session.add(detection)
    return detection


def batch_add_detections(session: Session, detections: List[Dict[str, Any]]):
    """Batch add multiple detections (more efficient)"""
    objects = [DetectedObject(**det) for det in detections]
    session.bulk_save_objects(objects)
    session.commit()


def get_detections_in_frame(
    session: Session,
    session_id: int,
    frame_number: int
) -> List[DetectedObject]:
    """Get all detections in a specific frame"""
    return session.query(DetectedObject).filter_by(
        session_id=session_id,
        frame_number=frame_number
    ).all()


def create_track(
    session: Session,
    session_id: int,
    track_id: int,
    object_class: ObjectClass,
    trajectory: List[Dict],
    is_av_vehicle: bool = False,
    **kwargs
) -> Track:
    """Create a new track"""
    first_point = trajectory[0]
    last_point = trajectory[-1]

    speeds = [p.get('speed', 0) for p in trajectory if p.get('speed') is not None]

    track = Track(
        session_id=session_id,
        track_id=track_id,
        object_class=object_class,
        first_seen=first_point['timestamp'],
        last_seen=last_point['timestamp'],
        total_frames=len(trajectory),
        trajectory=trajectory,
        average_speed=sum(speeds) / len(speeds) if speeds else 0,
        max_speed=max(speeds) if speeds else 0,
        min_speed=min(speeds) if speeds else 0,
        is_av_vehicle=is_av_vehicle,
        **kwargs
    )

    session.add(track)
    session.commit()
    session.refresh(track)
    return track


def get_tracks_by_class(
    session: Session,
    session_id: int,
    object_class: ObjectClass
) -> List[Track]:
    """Get all tracks of a specific class in a session"""
    return session.query(Track).filter_by(
        session_id=session_id,
        object_class=object_class
    ).all()


def get_av_track(session: Session, session_id: int) -> Optional[Track]:
    """Get the AV vehicle track for a session"""
    return session.query(Track).filter_by(
        session_id=session_id,
        is_av_vehicle=True
    ).first()


# ============================================================================
# Event and Edge Case Queries
# ============================================================================

def create_event(
    session: Session,
    session_id: int,
    event_type: EventType,
    severity: int,
    description: str,
    involved_tracks: Optional[List[int]] = None,
    is_edge_case: bool = False,
    **kwargs
) -> Event:
    """Create a new event"""
    event = Event(
        session_id=session_id,
        event_type=event_type,
        severity=severity,
        description=description,
        involved_tracks=involved_tracks or [],
        is_edge_case=is_edge_case,
        timestamp=datetime.utcnow(),
        **kwargs
    )

    session.add(event)
    session.commit()
    session.refresh(event)
    logger.warning(f"Event created: {event_type.value} (Severity: {severity})")
    return event


def get_events_by_severity(
    session: Session,
    session_id: int,
    min_severity: int = 3
) -> List[Event]:
    """Get events above a certain severity level"""
    return session.query(Event).filter(
        Event.session_id == session_id,
        Event.severity >= min_severity
    ).order_by(desc(Event.timestamp)).all()


def get_edge_cases(
    session: Session,
    unreviewed_only: bool = False,
    min_priority: Optional[int] = None
) -> List[EdgeCase]:
    """Get edge cases with optional filters"""
    query = session.query(EdgeCase)

    if unreviewed_only:
        query = query.filter_by(reviewed=False)

    if min_priority:
        query = query.filter(EdgeCase.priority >= min_priority)

    return query.order_by(desc(EdgeCase.priority)).all()


def create_edge_case(
    session: Session,
    event_id: int,
    case_type: str,
    environmental_factors: Dict,
    av_response: str,
    **kwargs
) -> EdgeCase:
    """Create an edge case from an event"""
    edge_case = EdgeCase(
        event_id=event_id,
        case_type=case_type,
        environmental_factors=environmental_factors,
        av_response=av_response,
        **kwargs
    )

    session.add(edge_case)

    # Update the event
    event = session.query(Event).filter_by(id=event_id).first()
    if event:
        event.is_edge_case = True

    session.commit()
    session.refresh(edge_case)
    logger.info(f"Edge case created: {case_type} (ID: {edge_case.id})")
    return edge_case


# ============================================================================
# Perception Validation Queries
# ============================================================================

def add_perception_validation(
    session: Session,
    session_id: int,
    frame_number: int,
    ground_truth_objects: List[Dict],
    av_detected_objects: List[Dict],
    metrics: Dict[str, float],
    **kwargs
) -> PerceptionValidation:
    """Add perception validation results"""
    validation = PerceptionValidation(
        session_id=session_id,
        frame_number=frame_number,
        timestamp=datetime.utcnow(),
        ground_truth_objects=ground_truth_objects,
        av_detected_objects=av_detected_objects,
        true_positives=metrics.get('true_positives', 0),
        false_positives=metrics.get('false_positives', 0),
        false_negatives=metrics.get('false_negatives', 0),
        precision=metrics.get('precision', 0.0),
        recall=metrics.get('recall', 0.0),
        f1_score=metrics.get('f1_score', 0.0),
        avg_position_error=metrics.get('avg_position_error'),
        avg_velocity_error=metrics.get('avg_velocity_error'),
        avg_heading_error=metrics.get('avg_heading_error'),
        **kwargs
    )

    session.add(validation)
    session.commit()
    return validation


def get_perception_metrics_summary(
    session: Session,
    session_id: int
) -> Dict[str, float]:
    """Get average perception metrics for a session"""
    results = session.query(
        func.avg(PerceptionValidation.precision).label('avg_precision'),
        func.avg(PerceptionValidation.recall).label('avg_recall'),
        func.avg(PerceptionValidation.f1_score).label('avg_f1'),
        func.avg(PerceptionValidation.avg_position_error).label('avg_pos_error'),
    ).filter_by(session_id=session_id).first()

    return {
        'avg_precision': float(results.avg_precision or 0),
        'avg_recall': float(results.avg_recall or 0),
        'avg_f1_score': float(results.avg_f1 or 0),
        'avg_position_error': float(results.avg_pos_error or 0),
    }


# ============================================================================
# Annotation Queries
# ============================================================================

def add_annotation(
    session: Session,
    session_id: int,
    camera_id: int,
    frame_number: int,
    object_class: ObjectClass,
    bbox: tuple,
    annotator_id: str,
    **kwargs
) -> Annotation:
    """Add a manual annotation"""
    annotation = Annotation(
        session_id=session_id,
        camera_id=camera_id,
        frame_number=frame_number,
        object_class=object_class,
        bbox_x=bbox[0],
        bbox_y=bbox[1],
        bbox_width=bbox[2],
        bbox_height=bbox[3],
        annotator_id=annotator_id,
        annotation_timestamp=datetime.utcnow(),
        **kwargs
    )

    session.add(annotation)
    session.commit()
    session.refresh(annotation)
    return annotation


def get_unannotated_frames(
    session: Session,
    session_id: int,
    limit: int = 100
) -> List[int]:
    """Get frame numbers that need annotation"""
    # This is a simplified version - in reality you'd want more complex logic
    annotated_frames = session.query(Annotation.frame_number.distinct()).filter_by(
        session_id=session_id
    ).all()

    annotated_frame_numbers = {f[0] for f in annotated_frames}

    # Get total frames in session (from detections)
    max_frame = session.query(func.max(DetectedObject.frame_number)).filter_by(
        session_id=session_id
    ).scalar()

    if not max_frame:
        return []

    # Return frames without annotations
    return [f for f in range(0, max_frame + 1, 30) if f not in annotated_frame_numbers][:limit]


# ============================================================================
# Statistics and Analytics
# ============================================================================

def get_session_statistics(session: Session, session_id: int) -> Dict[str, Any]:
    """Get comprehensive statistics for a session"""
    test_session = session.query(TestSession).filter_by(id=session_id).first()
    if not test_session:
        return {}

    # Count detections by class
    detection_counts = session.query(
        DetectedObject.object_class,
        func.count(DetectedObject.id).label('count')
    ).filter_by(session_id=session_id).group_by(DetectedObject.object_class).all()

    # Count tracks
    total_tracks = session.query(Track).filter_by(session_id=session_id).count()

    # Count events by type
    event_counts = session.query(
        Event.event_type,
        func.count(Event.id).label('count')
    ).filter_by(session_id=session_id).group_by(Event.event_type).all()

    # Count edge cases
    edge_case_count = session.query(Event).filter_by(
        session_id=session_id,
        is_edge_case=True
    ).count()

    return {
        'session_id': session_id,
        'session_name': test_session.name,
        'duration_seconds': test_session.duration_seconds,
        'status': test_session.status.value,
        'detection_counts': {dc[0].value: dc[1] for dc in detection_counts},
        'total_tracks': total_tracks,
        'event_counts': {ec[0].value: ec[1] for ec in event_counts},
        'edge_case_count': edge_case_count,
    }


def record_system_metrics(
    session: Session,
    detection_fps: float,
    tracking_fps: float,
    overall_fps: float,
    latency_ms: Dict[str, float],
    resource_usage: Dict[str, float]
) -> SystemMetrics:
    """Record system performance metrics"""
    metrics = SystemMetrics(
        detection_fps=detection_fps,
        tracking_fps=tracking_fps,
        overall_fps=overall_fps,
        camera_latency_ms=latency_ms.get('camera', 0),
        detection_latency_ms=latency_ms.get('detection', 0),
        tracking_latency_ms=latency_ms.get('tracking', 0),
        total_latency_ms=latency_ms.get('total', 0),
        cpu_usage_percent=resource_usage.get('cpu', 0),
        gpu_usage_percent=resource_usage.get('gpu', 0),
        memory_usage_gb=resource_usage.get('memory', 0),
        gpu_memory_usage_gb=resource_usage.get('gpu_memory', 0),
        timestamp=datetime.utcnow()
    )

    session.add(metrics)
    session.commit()
    return metrics
