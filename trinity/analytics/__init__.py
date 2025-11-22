"""
Trinity Phase 5.1 - Analytics Dashboard
Real-time metrics visualization and session analytics
"""

__version__ = "1.0.0"

from .dashboard import AnalyticsDashboard, MetricType
from .metrics_collector import MetricsCollector
from .visualizations import TimeSeriesChart, HeatmapChart, StatisticsCard

__all__ = [
    'AnalyticsDashboard',
    'MetricType',
    'MetricsCollector',
    'TimeSeriesChart',
    'HeatmapChart',
    'StatisticsCard'
]
