"""
Trinity Phase 5.2 - Report Generation System
Automated PDF/HTML/Excel reports for test sessions
"""

__version__ = "1.0.0"

from .report_generator import ReportGenerator, ReportFormat, ReportConfig
from .template_engine import TemplateEngine
from .chart_generator import ChartGenerator

__all__ = [
    'ReportGenerator',
    'ReportFormat',
    'ReportConfig',
    'TemplateEngine',
    'ChartGenerator'
]
