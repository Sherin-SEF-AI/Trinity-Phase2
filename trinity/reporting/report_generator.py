"""
Trinity Report Generator
Generates comprehensive test reports in PDF, HTML, and Excel formats
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import json
from loguru import logger

# PDF generation
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, Image, PageBreak, KeepTogether
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("ReportLab not available - PDF generation disabled")

# Excel generation
try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.chart import BarChart, LineChart, PieChart, Reference
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    logger.warning("openpyxl not available - Excel generation disabled")

# HTML generation (Jinja2)
try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    logger.warning("Jinja2 not available - HTML generation disabled")

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np


# ============================================================================
# Enums and Data Classes
# ============================================================================

class ReportFormat(Enum):
    """Supported report formats"""
    PDF = "pdf"
    HTML = "html"
    EXCEL = "xlsx"
    JSON = "json"


class ReportType(Enum):
    """Types of reports"""
    SESSION_SUMMARY = "session_summary"
    SAFETY_ANALYSIS = "safety_analysis"
    EDGE_CASE_ANALYSIS = "edge_case_analysis"
    PERCEPTION_VALIDATION = "perception_validation"
    FULL_REPORT = "full_report"


@dataclass
class ReportConfig:
    """Configuration for report generation"""

    # Basic settings
    title: str = "Trinity Test Report"
    subtitle: Optional[str] = None
    author: str = "Trinity Platform"
    company: str = "Autonomous Vehicle Testing Suite"

    # Format settings
    format: ReportFormat = ReportFormat.PDF
    page_size: str = "letter"  # letter or A4

    # Content settings
    include_charts: bool = True
    include_images: bool = True
    include_statistics: bool = True
    include_raw_data: bool = False

    # Chart settings
    chart_dpi: int = 150
    chart_style: str = "seaborn-v0_8-darkgrid"

    # Output settings
    output_dir: Path = field(default_factory=lambda: Path("reports"))
    filename_template: str = "{report_type}_{session_id}_{timestamp}.{ext}"

    # Branding
    logo_path: Optional[Path] = None
    color_primary: str = "#2c3e50"
    color_secondary: str = "#3498db"
    color_success: str = "#27ae60"
    color_warning: str = "#f39c12"
    color_danger: str = "#e74c3c"


@dataclass
class SessionSummary:
    """Summary data for a test session"""
    session_id: int
    session_name: str
    test_type: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: float
    av_vehicle_id: Optional[str]

    # Statistics
    total_frames: int = 0
    total_detections: int = 0
    total_tracks: int = 0
    total_events: int = 0
    total_edge_cases: int = 0

    # Performance
    avg_fps: float = 0.0
    avg_detection_time_ms: float = 0.0
    avg_tracking_time_ms: float = 0.0

    # Detections by class
    detections_by_class: Dict[str, int] = field(default_factory=dict)

    # Events by type
    events_by_type: Dict[str, int] = field(default_factory=dict)
    events_by_severity: Dict[str, int] = field(default_factory=dict)

    # Edge cases
    edge_cases_by_category: Dict[str, int] = field(default_factory=dict)
    edge_cases_by_severity: Dict[str, int] = field(default_factory=dict)

    # Safety metrics
    min_ttc: Optional[float] = None
    avg_ttc: Optional[float] = None
    near_miss_count: int = 0
    hard_braking_count: int = 0

    # Camera info
    cameras_used: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'session_id': self.session_id,
            'session_name': self.session_name,
            'test_type': self.test_type,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'av_vehicle_id': self.av_vehicle_id,
            'statistics': {
                'total_frames': self.total_frames,
                'total_detections': self.total_detections,
                'total_tracks': self.total_tracks,
                'total_events': self.total_events,
                'total_edge_cases': self.total_edge_cases,
            },
            'performance': {
                'avg_fps': self.avg_fps,
                'avg_detection_time_ms': self.avg_detection_time_ms,
                'avg_tracking_time_ms': self.avg_tracking_time_ms,
            },
            'detections_by_class': self.detections_by_class,
            'events_by_type': self.events_by_type,
            'events_by_severity': self.events_by_severity,
            'edge_cases_by_category': self.edge_cases_by_category,
            'edge_cases_by_severity': self.edge_cases_by_severity,
            'safety_metrics': {
                'min_ttc': self.min_ttc,
                'avg_ttc': self.avg_ttc,
                'near_miss_count': self.near_miss_count,
                'hard_braking_count': self.hard_braking_count,
            },
            'cameras_used': self.cameras_used,
        }


# ============================================================================
# Report Generator
# ============================================================================

class ReportGenerator:
    """
    Generates comprehensive test reports in multiple formats

    Features:
    - PDF reports with charts and tables
    - HTML reports with interactive elements
    - Excel reports with formatted data and charts
    - JSON exports for programmatic access
    - Customizable templates
    - Scheduled report generation
    """

    def __init__(self, config: Optional[ReportConfig] = None):
        """
        Initialize report generator

        Args:
            config: Report configuration (uses defaults if None)
        """
        self.config = config or ReportConfig()

        # Create output directory
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        # Set matplotlib style
        try:
            plt.style.use(self.config.chart_style)
        except:
            logger.warning(f"Chart style '{self.config.chart_style}' not available, using default")

        # Initialize Jinja2 environment for HTML templates
        if JINJA2_AVAILABLE:
            template_dir = Path(__file__).parent / "templates"
            if template_dir.exists():
                self.jinja_env = Environment(
                    loader=FileSystemLoader(str(template_dir)),
                    autoescape=select_autoescape(['html', 'xml'])
                )
            else:
                self.jinja_env = None
                logger.warning(f"Template directory not found: {template_dir}")
        else:
            self.jinja_env = None

        logger.info("Report generator initialized")

    # ========================================================================
    # Main Report Generation Methods
    # ========================================================================

    def generate_session_report(
        self,
        session_summary: SessionSummary,
        report_type: ReportType = ReportType.FULL_REPORT,
        output_format: Optional[ReportFormat] = None
    ) -> Path:
        """
        Generate a comprehensive session report

        Args:
            session_summary: Session data
            report_type: Type of report to generate
            output_format: Output format (uses config default if None)

        Returns:
            Path to generated report file
        """
        fmt = output_format or self.config.format

        # Generate filename
        filename = self._generate_filename(
            report_type=report_type.value,
            session_id=session_summary.session_id,
            ext=fmt.value
        )
        output_path = self.config.output_dir / filename

        logger.info(f"Generating {fmt.value.upper()} report: {output_path}")

        # Generate report based on format
        if fmt == ReportFormat.PDF:
            if not PDF_AVAILABLE:
                raise RuntimeError("PDF generation requires reportlab package")
            self._generate_pdf_report(session_summary, output_path, report_type)

        elif fmt == ReportFormat.HTML:
            if not JINJA2_AVAILABLE:
                raise RuntimeError("HTML generation requires jinja2 package")
            self._generate_html_report(session_summary, output_path, report_type)

        elif fmt == ReportFormat.EXCEL:
            if not EXCEL_AVAILABLE:
                raise RuntimeError("Excel generation requires openpyxl package")
            self._generate_excel_report(session_summary, output_path, report_type)

        elif fmt == ReportFormat.JSON:
            self._generate_json_report(session_summary, output_path, report_type)

        else:
            raise ValueError(f"Unsupported format: {fmt}")

        logger.success(f"Report generated: {output_path}")
        return output_path

    # ========================================================================
    # PDF Generation
    # ========================================================================

    def _generate_pdf_report(
        self,
        summary: SessionSummary,
        output_path: Path,
        report_type: ReportType
    ):
        """Generate PDF report"""

        # Create PDF document
        page_size = A4 if self.config.page_size == "A4" else letter
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=page_size,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )

        # Build story (content)
        story = []
        styles = getSampleStyleSheet()

        # Title page
        story.extend(self._build_pdf_title_page(summary, styles))
        story.append(PageBreak())

        # Executive summary
        story.extend(self._build_pdf_executive_summary(summary, styles))
        story.append(Spacer(1, 0.2*inch))

        # Session details
        story.extend(self._build_pdf_session_details(summary, styles))
        story.append(Spacer(1, 0.2*inch))

        # Statistics
        if self.config.include_statistics:
            story.extend(self._build_pdf_statistics(summary, styles))
            story.append(Spacer(1, 0.2*inch))

        # Charts
        if self.config.include_charts:
            story.extend(self._build_pdf_charts(summary, styles))

        # Safety analysis
        if report_type in [ReportType.SAFETY_ANALYSIS, ReportType.FULL_REPORT]:
            story.append(PageBreak())
            story.extend(self._build_pdf_safety_section(summary, styles))

        # Edge case analysis
        if report_type in [ReportType.EDGE_CASE_ANALYSIS, ReportType.FULL_REPORT]:
            story.append(PageBreak())
            story.extend(self._build_pdf_edge_case_section(summary, styles))

        # Build PDF
        doc.build(story)

    def _build_pdf_title_page(self, summary: SessionSummary, styles) -> List:
        """Build PDF title page"""
        elements = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor(self.config.color_primary),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        elements.append(Paragraph(self.config.title, title_style))

        # Subtitle
        if self.config.subtitle:
            subtitle_style = ParagraphStyle(
                'Subtitle',
                parent=styles['Normal'],
                fontSize=14,
                textColor=colors.grey,
                spaceAfter=20,
                alignment=TA_CENTER
            )
            elements.append(Paragraph(self.config.subtitle, subtitle_style))

        elements.append(Spacer(1, 0.5*inch))

        # Session info table
        session_data = [
            ['Session Name:', summary.session_name],
            ['Session ID:', str(summary.session_id)],
            ['Test Type:', summary.test_type.upper()],
            ['Start Time:', summary.start_time.strftime('%Y-%m-%d %H:%M:%S')],
            ['End Time:', summary.end_time.strftime('%Y-%m-%d %H:%M:%S') if summary.end_time else 'In Progress'],
            ['Duration:', f"{summary.duration_seconds / 3600:.2f} hours"],
        ]

        if summary.av_vehicle_id:
            session_data.append(['AV Vehicle:', summary.av_vehicle_id])

        session_table = Table(session_data, colWidths=[2*inch, 4*inch])
        session_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor(self.config.color_primary)),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        elements.append(session_table)
        elements.append(Spacer(1, 0.5*inch))

        # Report metadata
        meta_style = ParagraphStyle(
            'Meta',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        elements.append(Paragraph(
            f"Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            meta_style
        ))
        elements.append(Paragraph(f"Author: {self.config.author}", meta_style))

        return elements

    def _build_pdf_executive_summary(self, summary: SessionSummary, styles) -> List:
        """Build executive summary section"""
        elements = []

        # Section title
        elements.append(Paragraph("Executive Summary", styles['Heading1']))
        elements.append(Spacer(1, 0.1*inch))

        # Summary text
        summary_text = f"""
        This report summarizes the test session <b>{summary.session_name}</b> conducted on
        {summary.start_time.strftime('%B %d, %Y')}. The session captured <b>{summary.total_frames:,}</b>
        frames over a duration of <b>{summary.duration_seconds / 3600:.2f}</b> hours,
        detecting <b>{summary.total_detections:,}</b> objects across <b>{summary.total_tracks:,}</b> tracks.
        """

        if summary.total_events > 0:
            summary_text += f"""
            <br/><br/>
            The analysis identified <b>{summary.total_events}</b> safety events requiring attention,
            with <b>{summary.near_miss_count}</b> near-miss incidents detected.
            """

        if summary.total_edge_cases > 0:
            summary_text += f"""
            <br/><br/>
            Additionally, <b>{summary.total_edge_cases}</b> edge cases were automatically detected,
            providing valuable scenarios for dataset curation and system validation.
            """

        elements.append(Paragraph(summary_text, styles['BodyText']))

        return elements

    def _build_pdf_session_details(self, summary: SessionSummary, styles) -> List:
        """Build session details section"""
        elements = []

        elements.append(Paragraph("Session Details", styles['Heading2']))
        elements.append(Spacer(1, 0.1*inch))

        # Performance metrics table
        perf_data = [
            ['Metric', 'Value'],
            ['Average FPS', f"{summary.avg_fps:.2f}"],
            ['Avg Detection Time', f"{summary.avg_detection_time_ms:.2f} ms"],
            ['Avg Tracking Time', f"{summary.avg_tracking_time_ms:.2f} ms"],
            ['Cameras Used', ', '.join(map(str, summary.cameras_used))],
        ]

        perf_table = Table(perf_data, colWidths=[3*inch, 3*inch])
        perf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.config.color_primary)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))

        elements.append(perf_table)

        return elements

    def _build_pdf_statistics(self, summary: SessionSummary, styles) -> List:
        """Build statistics section"""
        elements = []

        elements.append(Paragraph("Detection Statistics", styles['Heading2']))
        elements.append(Spacer(1, 0.1*inch))

        # Detection by class
        if summary.detections_by_class:
            det_data = [['Object Class', 'Count', 'Percentage']]
            total_det = sum(summary.detections_by_class.values())

            for cls, count in sorted(
                summary.detections_by_class.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                percentage = (count / total_det * 100) if total_det > 0 else 0
                det_data.append([cls.capitalize(), f"{count:,}", f"{percentage:.1f}%"])

            det_table = Table(det_data, colWidths=[2*inch, 2*inch, 2*inch])
            det_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.config.color_secondary)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))

            elements.append(det_table)

        return elements

    def _build_pdf_charts(self, summary: SessionSummary, styles) -> List:
        """Build charts section"""
        elements = []

        elements.append(PageBreak())
        elements.append(Paragraph("Visual Analysis", styles['Heading1']))
        elements.append(Spacer(1, 0.1*inch))

        # Generate charts
        chart_paths = self._generate_charts(summary)

        # Add charts to PDF
        for chart_name, chart_path in chart_paths.items():
            if chart_path.exists():
                elements.append(Paragraph(chart_name.replace('_', ' ').title(), styles['Heading2']))
                elements.append(Spacer(1, 0.05*inch))

                img = Image(str(chart_path), width=6*inch, height=4*inch)
                elements.append(img)
                elements.append(Spacer(1, 0.2*inch))

        return elements

    def _build_pdf_safety_section(self, summary: SessionSummary, styles) -> List:
        """Build safety analysis section"""
        elements = []

        elements.append(Paragraph("Safety Analysis", styles['Heading1']))
        elements.append(Spacer(1, 0.1*inch))

        # Safety metrics summary
        safety_text = f"""
        The safety analysis module monitored all vehicle interactions throughout the test session.
        """

        if summary.min_ttc is not None:
            safety_text += f"""
            <br/><br/>
            <b>Time-to-Collision (TTC) Metrics:</b><br/>
            Minimum TTC: {summary.min_ttc:.2f} seconds<br/>
            Average TTC: {summary.avg_ttc:.2f} seconds
            """

        if summary.near_miss_count > 0:
            safety_text += f"""
            <br/><br/>
            <b style="color: {self.config.color_danger}">Near-Miss Events: {summary.near_miss_count}</b><br/>
            Near-miss events were detected when objects came within 2.0 meters of each other.
            """

        if summary.hard_braking_count > 0:
            safety_text += f"""
            <br/><br/>
            <b style="color: {self.config.color_warning}">Hard Braking Events: {summary.hard_braking_count}</b><br/>
            Hard braking events (deceleration > 4.0 m/s²) were detected.
            """

        elements.append(Paragraph(safety_text, styles['BodyText']))
        elements.append(Spacer(1, 0.2*inch))

        # Events by severity
        if summary.events_by_severity:
            sev_data = [['Severity', 'Count']]
            for sev, count in sorted(summary.events_by_severity.items()):
                sev_data.append([sev.upper(), str(count)])

            sev_table = Table(sev_data, colWidths=[3*inch, 3*inch])
            sev_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.config.color_danger)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))

            elements.append(Paragraph("Events by Severity", styles['Heading2']))
            elements.append(Spacer(1, 0.05*inch))
            elements.append(sev_table)

        return elements

    def _build_pdf_edge_case_section(self, summary: SessionSummary, styles) -> List:
        """Build edge case analysis section"""
        elements = []

        elements.append(Paragraph("Edge Case Analysis", styles['Heading1']))
        elements.append(Spacer(1, 0.1*inch))

        edge_text = f"""
        The edge case detection system automatically identified {summary.total_edge_cases}
        scenarios of interest for dataset curation and system validation.
        """

        elements.append(Paragraph(edge_text, styles['BodyText']))
        elements.append(Spacer(1, 0.2*inch))

        # Edge cases by category
        if summary.edge_cases_by_category:
            cat_data = [['Category', 'Count']]
            for cat, count in sorted(
                summary.edge_cases_by_category.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                cat_data.append([cat.replace('_', ' ').title(), str(count)])

            cat_table = Table(cat_data, colWidths=[3*inch, 3*inch])
            cat_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.config.color_secondary)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))

            elements.append(Paragraph("Edge Cases by Category", styles['Heading2']))
            elements.append(Spacer(1, 0.05*inch))
            elements.append(cat_table)

        return elements

    # ========================================================================
    # HTML Generation
    # ========================================================================

    def _generate_html_report(
        self,
        summary: SessionSummary,
        output_path: Path,
        report_type: ReportType
    ):
        """Generate HTML report"""

        # Generate charts
        chart_paths = self._generate_charts(summary)

        # Convert chart paths to relative paths or base64
        charts_data = {}
        for name, path in chart_paths.items():
            if path.exists():
                # Use relative path
                charts_data[name] = path.name

        # Prepare template data
        template_data = {
            'config': self.config,
            'summary': summary,
            'report_type': report_type.value,
            'generated_time': datetime.now(),
            'charts': charts_data,
        }

        # Render template or use basic HTML
        if self.jinja_env:
            try:
                template = self.jinja_env.get_template('report_template.html')
                html_content = template.render(**template_data)
            except Exception as e:
                logger.warning(f"Template rendering failed: {e}, using basic HTML")
                html_content = self._generate_basic_html(summary, chart_paths)
        else:
            html_content = self._generate_basic_html(summary, chart_paths)

        # Write HTML file
        output_path.write_text(html_content, encoding='utf-8')

    def _generate_basic_html(
        self,
        summary: SessionSummary,
        chart_paths: Dict[str, Path]
    ) -> str:
        """Generate basic HTML report without templates"""

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.config.title} - Session {summary.session_id}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, {self.config.color_primary} 0%, {self.config.color_secondary} 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
        }}
        .section {{
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: {self.config.color_primary};
            border-bottom: 2px solid {self.config.color_secondary};
            padding-bottom: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid {self.config.color_secondary};
        }}
        .stat-card .label {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}
        .stat-card .value {{
            font-size: 1.8em;
            font-weight: bold;
            color: {self.config.color_primary};
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        table th, table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        table th {{
            background-color: {self.config.color_primary};
            color: white;
        }}
        table tr:hover {{
            background-color: #f5f5f5;
        }}
        .chart {{
            margin: 20px 0;
            text-align: center;
        }}
        .chart img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 40px;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{self.config.title}</h1>
        <p>Session: {summary.session_name} (ID: {summary.session_id})</p>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="section">
        <h2>Executive Summary</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">Total Frames</div>
                <div class="value">{summary.total_frames:,}</div>
            </div>
            <div class="stat-card">
                <div class="label">Detections</div>
                <div class="value">{summary.total_detections:,}</div>
            </div>
            <div class="stat-card">
                <div class="label">Tracks</div>
                <div class="value">{summary.total_tracks:,}</div>
            </div>
            <div class="stat-card">
                <div class="label">Events</div>
                <div class="value">{summary.total_events}</div>
            </div>
            <div class="stat-card">
                <div class="label">Edge Cases</div>
                <div class="value">{summary.total_edge_cases}</div>
            </div>
            <div class="stat-card">
                <div class="label">Average FPS</div>
                <div class="value">{summary.avg_fps:.1f}</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Session Details</h2>
        <table>
            <tr><td><strong>Test Type</strong></td><td>{summary.test_type.upper()}</td></tr>
            <tr><td><strong>Start Time</strong></td><td>{summary.start_time.strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
            <tr><td><strong>End Time</strong></td><td>{summary.end_time.strftime('%Y-%m-%d %H:%M:%S') if summary.end_time else 'In Progress'}</td></tr>
            <tr><td><strong>Duration</strong></td><td>{summary.duration_seconds / 3600:.2f} hours</td></tr>
            <tr><td><strong>AV Vehicle</strong></td><td>{summary.av_vehicle_id or 'N/A'}</td></tr>
        </table>
    </div>
"""

        # Add charts
        if chart_paths:
            html += '    <div class="section">\n        <h2>Visual Analysis</h2>\n'
            for name, path in chart_paths.items():
                if path.exists():
                    html += f'        <div class="chart">\n            <h3>{name.replace("_", " ").title()}</h3>\n'
                    html += f'            <img src="{path.name}" alt="{name}">\n        </div>\n'
            html += '    </div>\n'

        # Add detection statistics
        if summary.detections_by_class:
            html += '    <div class="section">\n        <h2>Detection Statistics</h2>\n'
            html += '        <table>\n            <tr><th>Object Class</th><th>Count</th><th>Percentage</th></tr>\n'
            total_det = sum(summary.detections_by_class.values())
            for cls, count in sorted(summary.detections_by_class.items(), key=lambda x: x[1], reverse=True):
                pct = (count / total_det * 100) if total_det > 0 else 0
                html += f'            <tr><td>{cls.capitalize()}</td><td>{count:,}</td><td>{pct:.1f}%</td></tr>\n'
            html += '        </table>\n    </div>\n'

        # Footer
        html += f"""
    <div class="footer">
        <p>{self.config.company}</p>
        <p>{self.config.author}</p>
    </div>
</body>
</html>
"""

        return html

    # ========================================================================
    # Excel Generation
    # ========================================================================

    def _generate_excel_report(
        self,
        summary: SessionSummary,
        output_path: Path,
        report_type: ReportType
    ):
        """Generate Excel report with formatted data and charts"""

        wb = openpyxl.Workbook()

        # Remove default sheet
        wb.remove(wb.active)

        # Add worksheets
        ws_summary = wb.create_sheet("Summary")
        ws_detections = wb.create_sheet("Detections")
        ws_safety = wb.create_sheet("Safety")
        ws_edge_cases = wb.create_sheet("Edge Cases")

        # Build summary sheet
        self._build_excel_summary_sheet(ws_summary, summary)

        # Build detections sheet
        self._build_excel_detections_sheet(ws_detections, summary)

        # Build safety sheet
        self._build_excel_safety_sheet(ws_safety, summary)

        # Build edge cases sheet
        self._build_excel_edge_cases_sheet(ws_edge_cases, summary)

        # Save workbook
        wb.save(output_path)

    def _build_excel_summary_sheet(self, ws, summary: SessionSummary):
        """Build Excel summary sheet"""

        # Title
        ws['A1'] = self.config.title
        ws['A1'].font = Font(size=16, bold=True, color="FFFFFF")
        ws['A1'].fill = PatternFill(start_color=self.config.color_primary.replace('#', ''), fill_type="solid")
        ws.merge_cells('A1:B1')

        # Session info
        row = 3
        ws[f'A{row}'] = "Session Name:"
        ws[f'B{row}'] = summary.session_name
        ws[f'A{row}'].font = Font(bold=True)

        row += 1
        ws[f'A{row}'] = "Session ID:"
        ws[f'B{row}'] = summary.session_id
        ws[f'A{row}'].font = Font(bold=True)

        row += 1
        ws[f'A{row}'] = "Test Type:"
        ws[f'B{row}'] = summary.test_type.upper()
        ws[f'A{row}'].font = Font(bold=True)

        row += 1
        ws[f'A{row}'] = "Start Time:"
        ws[f'B{row}'] = summary.start_time.strftime('%Y-%m-%d %H:%M:%S')
        ws[f'A{row}'].font = Font(bold=True)

        row += 2
        ws[f'A{row}'] = "Statistics"
        ws[f'A{row}'].font = Font(size=14, bold=True)

        # Statistics table
        row += 1
        stats = [
            ['Total Frames', summary.total_frames],
            ['Total Detections', summary.total_detections],
            ['Total Tracks', summary.total_tracks],
            ['Total Events', summary.total_events],
            ['Total Edge Cases', summary.total_edge_cases],
            ['Average FPS', f"{summary.avg_fps:.2f}"],
        ]

        for stat_name, stat_value in stats:
            ws[f'A{row}'] = stat_name
            ws[f'B{row}'] = stat_value
            ws[f'A{row}'].font = Font(bold=True)
            row += 1

        # Auto-adjust column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 30

    def _build_excel_detections_sheet(self, ws, summary: SessionSummary):
        """Build Excel detections sheet"""

        # Header
        ws['A1'] = "Object Class"
        ws['B1'] = "Count"
        ws['C1'] = "Percentage"

        for col in ['A1', 'B1', 'C1']:
            ws[col].font = Font(bold=True, color="FFFFFF")
            ws[col].fill = PatternFill(start_color=self.config.color_secondary.replace('#', ''), fill_type="solid")

        # Data
        row = 2
        total_det = sum(summary.detections_by_class.values())

        for cls, count in sorted(summary.detections_by_class.items(), key=lambda x: x[1], reverse=True):
            ws[f'A{row}'] = cls.capitalize()
            ws[f'B{row}'] = count
            pct = (count / total_det * 100) if total_det > 0 else 0
            ws[f'C{row}'] = f"{pct:.1f}%"
            row += 1

        # Add chart
        if summary.detections_by_class:
            chart = PieChart()
            chart.title = "Detections by Class"

            labels = Reference(ws, min_col=1, min_row=2, max_row=row-1)
            data = Reference(ws, min_col=2, min_row=1, max_row=row-1)

            chart.add_data(data, titles_from_data=True)
            chart.set_categories(labels)

            ws.add_chart(chart, "E2")

        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 15

    def _build_excel_safety_sheet(self, ws, summary: SessionSummary):
        """Build Excel safety sheet"""

        # Title
        ws['A1'] = "Safety Metrics"
        ws['A1'].font = Font(size=14, bold=True)

        row = 3
        metrics = [
            ['Minimum TTC', f"{summary.min_ttc:.2f}s" if summary.min_ttc else 'N/A'],
            ['Average TTC', f"{summary.avg_ttc:.2f}s" if summary.avg_ttc else 'N/A'],
            ['Near-Miss Count', summary.near_miss_count],
            ['Hard Braking Count', summary.hard_braking_count],
        ]

        for metric_name, metric_value in metrics:
            ws[f'A{row}'] = metric_name
            ws[f'B{row}'] = metric_value
            ws[f'A{row}'].font = Font(bold=True)
            row += 1

        # Events by severity
        if summary.events_by_severity:
            row += 2
            ws[f'A{row}'] = "Events by Severity"
            ws[f'A{row}'].font = Font(size=14, bold=True)

            row += 1
            ws[f'A{row}'] = "Severity"
            ws[f'B{row}'] = "Count"
            ws[f'A{row}'].font = Font(bold=True, color="FFFFFF")
            ws[f'B{row}'].font = Font(bold=True, color="FFFFFF")
            ws[f'A{row}'].fill = PatternFill(start_color="C0504D", fill_type="solid")
            ws[f'B{row}'].fill = PatternFill(start_color="C0504D", fill_type="solid")

            row += 1
            for sev, count in sorted(summary.events_by_severity.items()):
                ws[f'A{row}'] = sev.upper()
                ws[f'B{row}'] = count
                row += 1

        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 20

    def _build_excel_edge_cases_sheet(self, ws, summary: SessionSummary):
        """Build Excel edge cases sheet"""

        # Header
        ws['A1'] = "Category"
        ws['B1'] = "Count"

        for col in ['A1', 'B1']:
            ws[col].font = Font(bold=True, color="FFFFFF")
            ws[col].fill = PatternFill(start_color=self.config.color_secondary.replace('#', ''), fill_type="solid")

        # Data
        row = 2
        for cat, count in sorted(summary.edge_cases_by_category.items(), key=lambda x: x[1], reverse=True):
            ws[f'A{row}'] = cat.replace('_', ' ').title()
            ws[f'B{row}'] = count
            row += 1

        # Add bar chart
        if summary.edge_cases_by_category:
            chart = BarChart()
            chart.title = "Edge Cases by Category"
            chart.y_axis.title = "Count"

            data = Reference(ws, min_col=2, min_row=1, max_row=row-1)
            cats = Reference(ws, min_col=1, min_row=2, max_row=row-1)

            chart.add_data(data, titles_from_data=True)
            chart.set_categories(cats)

            ws.add_chart(chart, "D2")

        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 15

    # ========================================================================
    # JSON Generation
    # ========================================================================

    def _generate_json_report(
        self,
        summary: SessionSummary,
        output_path: Path,
        report_type: ReportType
    ):
        """Generate JSON report"""

        report_data = {
            'report_type': report_type.value,
            'generated_at': datetime.now().isoformat(),
            'config': {
                'title': self.config.title,
                'author': self.config.author,
            },
            'session': summary.to_dict()
        }

        with output_path.open('w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

    # ========================================================================
    # Chart Generation
    # ========================================================================

    def _generate_charts(self, summary: SessionSummary) -> Dict[str, Path]:
        """Generate all charts and return paths"""

        chart_paths = {}

        # Detections by class pie chart
        if summary.detections_by_class:
            path = self._create_detections_pie_chart(summary)
            if path:
                chart_paths['detections_by_class'] = path

        # Events by severity bar chart
        if summary.events_by_severity:
            path = self._create_events_bar_chart(summary)
            if path:
                chart_paths['events_by_severity'] = path

        # Edge cases by category bar chart
        if summary.edge_cases_by_category:
            path = self._create_edge_cases_bar_chart(summary)
            if path:
                chart_paths['edge_cases_by_category'] = path

        return chart_paths

    def _create_detections_pie_chart(self, summary: SessionSummary) -> Optional[Path]:
        """Create detections by class pie chart"""

        try:
            fig, ax = plt.subplots(figsize=(10, 6), dpi=self.config.chart_dpi)

            classes = list(summary.detections_by_class.keys())
            counts = list(summary.detections_by_class.values())

            # Create pie chart
            wedges, texts, autotexts = ax.pie(
                counts,
                labels=[c.capitalize() for c in classes],
                autopct='%1.1f%%',
                startangle=90
            )

            # Style
            for text in texts:
                text.set_fontsize(10)
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(9)
                autotext.set_weight('bold')

            ax.set_title('Detections by Object Class', fontsize=14, fontweight='bold')

            # Save
            output_path = self.config.output_dir / f"chart_detections_{summary.session_id}.png"
            plt.tight_layout()
            plt.savefig(output_path, dpi=self.config.chart_dpi, bbox_inches='tight')
            plt.close()

            return output_path

        except Exception as e:
            logger.error(f"Error creating detections chart: {e}")
            return None

    def _create_events_bar_chart(self, summary: SessionSummary) -> Optional[Path]:
        """Create events by severity bar chart"""

        try:
            fig, ax = plt.subplots(figsize=(10, 6), dpi=self.config.chart_dpi)

            severities = list(summary.events_by_severity.keys())
            counts = list(summary.events_by_severity.values())

            # Color map
            color_map = {
                'low': self.config.color_success,
                'medium': self.config.color_warning,
                'high': self.config.color_danger,
                'critical': '#8B0000'
            }
            colors_list = [color_map.get(s.lower(), self.config.color_secondary) for s in severities]

            # Create bar chart
            bars = ax.bar(range(len(severities)), counts, color=colors_list)

            ax.set_xlabel('Severity', fontsize=12)
            ax.set_ylabel('Count', fontsize=12)
            ax.set_title('Safety Events by Severity', fontsize=14, fontweight='bold')
            ax.set_xticks(range(len(severities)))
            ax.set_xticklabels([s.upper() for s in severities])

            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}',
                       ha='center', va='bottom', fontweight='bold')

            # Save
            output_path = self.config.output_dir / f"chart_events_{summary.session_id}.png"
            plt.tight_layout()
            plt.savefig(output_path, dpi=self.config.chart_dpi, bbox_inches='tight')
            plt.close()

            return output_path

        except Exception as e:
            logger.error(f"Error creating events chart: {e}")
            return None

    def _create_edge_cases_bar_chart(self, summary: SessionSummary) -> Optional[Path]:
        """Create edge cases by category bar chart"""

        try:
            fig, ax = plt.subplots(figsize=(12, 6), dpi=self.config.chart_dpi)

            # Sort by count
            sorted_items = sorted(
                summary.edge_cases_by_category.items(),
                key=lambda x: x[1],
                reverse=True
            )

            categories = [item[0].replace('_', ' ').title() for item in sorted_items]
            counts = [item[1] for item in sorted_items]

            # Create horizontal bar chart for better label readability
            bars = ax.barh(range(len(categories)), counts, color=self.config.color_secondary)

            ax.set_xlabel('Count', fontsize=12)
            ax.set_ylabel('Category', fontsize=12)
            ax.set_title('Edge Cases by Category', fontsize=14, fontweight='bold')
            ax.set_yticks(range(len(categories)))
            ax.set_yticklabels(categories)

            # Add value labels on bars
            for i, bar in enumerate(bars):
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2.,
                       f'{int(width)}',
                       ha='left', va='center', fontweight='bold', fontsize=9)

            # Save
            output_path = self.config.output_dir / f"chart_edge_cases_{summary.session_id}.png"
            plt.tight_layout()
            plt.savefig(output_path, dpi=self.config.chart_dpi, bbox_inches='tight')
            plt.close()

            return output_path

        except Exception as e:
            logger.error(f"Error creating edge cases chart: {e}")
            return None

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _generate_filename(
        self,
        report_type: str,
        session_id: int,
        ext: str
    ) -> str:
        """Generate report filename"""

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        return self.config.filename_template.format(
            report_type=report_type,
            session_id=session_id,
            timestamp=timestamp,
            ext=ext
        )
