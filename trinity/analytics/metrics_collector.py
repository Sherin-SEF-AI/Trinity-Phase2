"""
Trinity Metrics Collector
Collects and stores system metrics for analytics dashboard
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Deque
from collections import deque, defaultdict
import threading
import time
import numpy as np
from loguru import logger


class MetricType(Enum):
    """Types of metrics to collect"""
    # Performance metrics
    FPS = "fps"
    DETECTION_TIME = "detection_time_ms"
    TRACKING_TIME = "tracking_time_ms"
    TOTAL_PIPELINE_TIME = "total_pipeline_time_ms"

    # Detection metrics
    DETECTIONS_COUNT = "detections_count"
    TRACKS_COUNT = "tracks_count"

    # Safety metrics
    MIN_TTC = "min_ttc"
    NEAR_MISS_COUNT = "near_miss_count"
    EVENTS_COUNT = "events_count"

    # Edge case metrics
    EDGE_CASES_COUNT = "edge_cases_count"

    # System metrics
    CPU_USAGE = "cpu_usage_percent"
    MEMORY_USAGE = "memory_usage_mb"
    GPU_USAGE = "gpu_usage_percent"
    GPU_MEMORY = "gpu_memory_mb"


@dataclass
class MetricSample:
    """A single metric sample"""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricStatistics:
    """Statistical summary of a metric"""
    count: int
    mean: float
    std: float
    min: float
    max: float
    median: float
    p95: float
    p99: float


class MetricsCollector:
    """
    Collects and manages system metrics

    Features:
    - Time-series data storage with configurable retention
    - Real-time statistics calculation
    - Automatic aggregation (per-second, per-minute, per-hour)
    - Thread-safe metric updates
    - Memory-efficient circular buffers
    """

    def __init__(
        self,
        retention_seconds: int = 3600,  # 1 hour default
        max_samples_per_metric: int = 10000
    ):
        """
        Initialize metrics collector

        Args:
            retention_seconds: How long to keep metrics in memory
            max_samples_per_metric: Maximum samples per metric (for memory management)
        """
        self.retention_seconds = retention_seconds
        self.max_samples = max_samples_per_metric

        # Time-series data: {metric_type: deque of MetricSample}
        self.metrics: Dict[MetricType, Deque[MetricSample]] = defaultdict(
            lambda: deque(maxlen=self.max_samples)
        )

        # Aggregated data: {metric_type: {period: deque of (timestamp, value)}}
        self.aggregated_1s: Dict[MetricType, Deque] = defaultdict(
            lambda: deque(maxlen=3600)  # 1 hour of 1-second data
        )
        self.aggregated_1m: Dict[MetricType, Deque] = defaultdict(
            lambda: deque(maxlen=1440)  # 1 day of 1-minute data
        )

        # Lock for thread safety
        self.lock = threading.RLock()

        # Aggregation thread
        self.aggregation_running = False
        self.aggregation_thread: Optional[threading.Thread] = None

        logger.info(f"Metrics collector initialized (retention: {retention_seconds}s)")

    # ========================================================================
    # Metric Recording
    # ========================================================================

    def record(
        self,
        metric_type: MetricType,
        value: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record a metric sample

        Args:
            metric_type: Type of metric
            value: Metric value
            metadata: Optional metadata for the sample
        """
        sample = MetricSample(
            timestamp=datetime.now(),
            value=value,
            metadata=metadata or {}
        )

        with self.lock:
            self.metrics[metric_type].append(sample)

    def record_batch(self, metrics: Dict[MetricType, float]):
        """
        Record multiple metrics at once

        Args:
            metrics: Dictionary of {metric_type: value}
        """
        timestamp = datetime.now()

        with self.lock:
            for metric_type, value in metrics.items():
                sample = MetricSample(timestamp=timestamp, value=value)
                self.metrics[metric_type].append(sample)

    # ========================================================================
    # Data Retrieval
    # ========================================================================

    def get_recent(
        self,
        metric_type: MetricType,
        seconds: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[MetricSample]:
        """
        Get recent samples for a metric

        Args:
            metric_type: Type of metric
            seconds: Only return samples from last N seconds
            limit: Maximum number of samples to return

        Returns:
            List of metric samples (newest first)
        """
        with self.lock:
            samples = list(self.metrics[metric_type])

        # Filter by time if specified
        if seconds:
            cutoff = datetime.now() - timedelta(seconds=seconds)
            samples = [s for s in samples if s.timestamp >= cutoff]

        # Limit number of samples
        if limit:
            samples = samples[-limit:]

        return list(reversed(samples))

    def get_time_series(
        self,
        metric_type: MetricType,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> tuple[List[datetime], List[float]]:
        """
        Get time series data (timestamps and values)

        Args:
            metric_type: Type of metric
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Tuple of (timestamps, values)
        """
        samples = self.get_recent(metric_type)

        # Filter by time range
        if start_time or end_time:
            filtered = []
            for s in samples:
                if start_time and s.timestamp < start_time:
                    continue
                if end_time and s.timestamp > end_time:
                    continue
                filtered.append(s)
            samples = filtered

        timestamps = [s.timestamp for s in samples]
        values = [s.value for s in samples]

        return timestamps, values

    def get_aggregated(
        self,
        metric_type: MetricType,
        period: str = "1s",
        limit: int = 100
    ) -> tuple[List[datetime], List[float]]:
        """
        Get aggregated time series data

        Args:
            metric_type: Type of metric
            period: Aggregation period ("1s" or "1m")
            limit: Maximum number of points to return

        Returns:
            Tuple of (timestamps, values)
        """
        with self.lock:
            if period == "1s":
                data = list(self.aggregated_1s[metric_type])
            elif period == "1m":
                data = list(self.aggregated_1m[metric_type])
            else:
                raise ValueError(f"Unsupported period: {period}")

        data = data[-limit:]

        if not data:
            return [], []

        timestamps = [item[0] for item in data]
        values = [item[1] for item in data]

        return timestamps, values

    # ========================================================================
    # Statistics
    # ========================================================================

    def get_statistics(
        self,
        metric_type: MetricType,
        seconds: Optional[int] = None
    ) -> Optional[MetricStatistics]:
        """
        Calculate statistics for a metric

        Args:
            metric_type: Type of metric
            seconds: Only use samples from last N seconds

        Returns:
            MetricStatistics or None if no data
        """
        samples = self.get_recent(metric_type, seconds=seconds)

        if not samples:
            return None

        values = np.array([s.value for s in samples])

        return MetricStatistics(
            count=len(values),
            mean=float(np.mean(values)),
            std=float(np.std(values)),
            min=float(np.min(values)),
            max=float(np.max(values)),
            median=float(np.median(values)),
            p95=float(np.percentile(values, 95)),
            p99=float(np.percentile(values, 99))
        )

    def get_latest(self, metric_type: MetricType) -> Optional[float]:
        """Get the latest value for a metric"""
        with self.lock:
            if not self.metrics[metric_type]:
                return None
            return self.metrics[metric_type][-1].value

    def get_all_statistics(
        self,
        seconds: Optional[int] = None
    ) -> Dict[MetricType, MetricStatistics]:
        """
        Get statistics for all metrics

        Args:
            seconds: Only use samples from last N seconds

        Returns:
            Dictionary of {metric_type: statistics}
        """
        stats = {}

        for metric_type in self.metrics.keys():
            stat = self.get_statistics(metric_type, seconds=seconds)
            if stat:
                stats[metric_type] = stat

        return stats

    # ========================================================================
    # Aggregation
    # ========================================================================

    def start_aggregation(self):
        """Start background aggregation thread"""
        if self.aggregation_running:
            logger.warning("Aggregation already running")
            return

        self.aggregation_running = True
        self.aggregation_thread = threading.Thread(
            target=self._aggregation_loop,
            daemon=True
        )
        self.aggregation_thread.start()

        logger.info("Metrics aggregation started")

    def stop_aggregation(self):
        """Stop background aggregation thread"""
        if not self.aggregation_running:
            return

        self.aggregation_running = False

        if self.aggregation_thread:
            self.aggregation_thread.join(timeout=5)

        logger.info("Metrics aggregation stopped")

    def _aggregation_loop(self):
        """Background loop for aggregating metrics"""
        last_1s_time = time.time()
        last_1m_time = time.time()

        while self.aggregation_running:
            try:
                current_time = time.time()

                # Aggregate every second
                if current_time - last_1s_time >= 1.0:
                    self._aggregate_period("1s")
                    last_1s_time = current_time

                # Aggregate every minute
                if current_time - last_1m_time >= 60.0:
                    self._aggregate_period("1m")
                    last_1m_time = current_time

                # Clean old data
                self._cleanup_old_data()

                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in aggregation loop: {e}")
                time.sleep(1)

    def _aggregate_period(self, period: str):
        """Aggregate metrics for a time period"""
        timestamp = datetime.now()

        with self.lock:
            for metric_type in self.metrics.keys():
                # Get recent samples
                if period == "1s":
                    seconds = 1
                    target_dict = self.aggregated_1s
                elif period == "1m":
                    seconds = 60
                    target_dict = self.aggregated_1m
                else:
                    continue

                samples = self.get_recent(metric_type, seconds=seconds)

                if samples:
                    # Calculate mean value
                    values = [s.value for s in samples]
                    mean_value = np.mean(values)

                    # Store aggregated point
                    target_dict[metric_type].append((timestamp, float(mean_value)))

    def _cleanup_old_data(self):
        """Remove data older than retention period"""
        cutoff = datetime.now() - timedelta(seconds=self.retention_seconds)

        with self.lock:
            for metric_type in list(self.metrics.keys()):
                samples = self.metrics[metric_type]

                # Remove old samples
                while samples and samples[0].timestamp < cutoff:
                    samples.popleft()

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def clear(self, metric_type: Optional[MetricType] = None):
        """
        Clear metrics data

        Args:
            metric_type: Type of metric to clear (None = all)
        """
        with self.lock:
            if metric_type:
                self.metrics[metric_type].clear()
                self.aggregated_1s[metric_type].clear()
                self.aggregated_1m[metric_type].clear()
            else:
                self.metrics.clear()
                self.aggregated_1s.clear()
                self.aggregated_1m.clear()

        logger.info(f"Cleared metrics: {metric_type or 'all'}")

    def get_metric_types(self) -> List[MetricType]:
        """Get list of metric types being collected"""
        with self.lock:
            return list(self.metrics.keys())

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of collector state"""
        with self.lock:
            return {
                'metric_types': len(self.metrics),
                'total_samples': sum(len(samples) for samples in self.metrics.values()),
                'retention_seconds': self.retention_seconds,
                'max_samples': self.max_samples,
                'aggregation_running': self.aggregation_running,
                'metrics': {
                    mt.value: {
                        'samples': len(self.metrics[mt]),
                        'latest': self.get_latest(mt)
                    }
                    for mt in self.metrics.keys()
                }
            }
