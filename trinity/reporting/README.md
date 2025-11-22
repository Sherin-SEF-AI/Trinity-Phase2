# Trinity Report Generation System

**Phase 5.2** - Automated PDF/HTML/Excel Reports with Scheduling

---

## Overview

The Trinity Report Generation System provides comprehensive, automated report generation for AV test sessions with support for multiple output formats, customizable templates, rich visualizations, and scheduled delivery.

### Key Features

✅ **Multiple Formats** - PDF, HTML, Excel, JSON
✅ **Rich Visualizations** - Charts, graphs, heatmaps
✅ **Customizable Templates** - Create custom report layouts
✅ **Scheduled Reports** - Daily, weekly, monthly, session-end
✅ **Professional Styling** - Branded, polished output
✅ **Automated Delivery** - Email integration ready

---

## Quick Start

### Basic Usage

```python
from trinity.reporting import ReportGenerator, ReportConfig, SessionSummary, ReportFormat
from datetime import datetime

# Configure report generator
config = ReportConfig(
    title="Trinity Test Report",
    author="Your Name",
    company="Your Organization",
    format=ReportFormat.PDF,
    include_charts=True
)

generator = ReportGenerator(config)

# Create session summary
summary = SessionSummary(
    session_id=1,
    session_name="Highway Test Run",
    test_type="scenario",
    start_time=datetime(2025, 11, 22, 10, 0, 0),
    end_time=datetime(2025, 11, 22, 12, 30, 0),
    duration_seconds=9000,
    total_frames=27000,
    total_detections=15420,
    total_tracks=320,
    total_events=12,
    total_edge_cases=5,
    avg_fps=30.0,
    detections_by_class={
        'car': 8500,
        'pedestrian': 3200,
        'cyclist': 1500,
        'truck': 2220
    },
    events_by_severity={
        'low': 8,
        'medium': 3,
        'high': 1
    }
)

# Generate report
report_path = generator.generate_session_report(summary)
print(f"Report generated: {report_path}")
```

### Multiple Formats

```python
# Generate PDF
pdf_report = generator.generate_session_report(
    summary,
    output_format=ReportFormat.PDF
)

# Generate HTML
html_report = generator.generate_session_report(
    summary,
    output_format=ReportFormat.HTML
)

# Generate Excel
excel_report = generator.generate_session_report(
    summary,
    output_format=ReportFormat.EXCEL
)

# Generate JSON
json_report = generator.generate_session_report(
    summary,
    output_format=ReportFormat.JSON
)
```

---

## Report Formats

### PDF Reports

Professional PDF reports with:
- Title page with session metadata
- Executive summary
- Detailed statistics tables
- Rich charts and visualizations
- Safety analysis section
- Edge case analysis section
- Page numbers and headers

**Dependencies:** `reportlab`, `matplotlib`

```python
from trinity.reporting import ReportFormat, ReportType

generator.generate_session_report(
    summary,
    report_type=ReportType.FULL_REPORT,
    output_format=ReportFormat.PDF
)
```

### HTML Reports

Interactive HTML reports with:
- Responsive design
- Modern styling with CSS grid
- Embedded charts
- Hover effects
- Print-friendly layout

**Dependencies:** `jinja2` (optional for templates), `matplotlib`

```python
generator.generate_session_report(
    summary,
    report_type=ReportType.SESSION_SUMMARY,
    output_format=ReportFormat.HTML
)
```

### Excel Reports

Multi-sheet Excel workbooks with:
- Summary sheet with key metrics
- Detection statistics with charts
- Safety metrics
- Edge case analysis
- Formatted tables and conditional formatting

**Dependencies:** `openpyxl`, `matplotlib`

```python
generator.generate_session_report(
    summary,
    report_type=ReportType.FULL_REPORT,
    output_format=ReportFormat.EXCEL
)
```

### JSON Reports

Structured JSON for programmatic access:

```python
generator.generate_session_report(
    summary,
    output_format=ReportFormat.JSON
)
```

---

## Report Types

### Session Summary
Quick overview of test session:
- Session metadata
- Key statistics
- Detection summary
- Basic charts

```python
ReportType.SESSION_SUMMARY
```

### Safety Analysis
Detailed safety metrics:
- Time-to-Collision (TTC) analysis
- Near-miss events
- Hard braking detection
- Events by severity
- Safety recommendations

```python
ReportType.SAFETY_ANALYSIS
```

### Edge Case Analysis
Edge case detection results:
- Cases by category
- Cases by severity
- Detailed case list
- Dataset curation recommendations

```python
ReportType.EDGE_CASE_ANALYSIS
```

### Perception Validation
Perception system performance:
- MOTA/MOTP metrics
- Detection accuracy
- Tracking performance
- Confusion matrix

```python
ReportType.PERCEPTION_VALIDATION
```

### Full Report
Complete report with all sections:
- All of the above
- Performance metrics
- Recommendations

```python
ReportType.FULL_REPORT
```

---

## Customization

### Report Configuration

```python
from trinity.reporting import ReportConfig
from pathlib import Path

config = ReportConfig(
    # Basic settings
    title="Custom Report Title",
    subtitle="Optional Subtitle",
    author="John Doe",
    company="ACME Testing Corp",

    # Format settings
    format=ReportFormat.PDF,
    page_size="letter",  # or "A4"

    # Content settings
    include_charts=True,
    include_images=True,
    include_statistics=True,
    include_raw_data=False,

    # Chart settings
    chart_dpi=150,
    chart_style="seaborn-v0_8-darkgrid",

    # Output settings
    output_dir=Path("reports/custom"),
    filename_template="{report_type}_{session_id}_{timestamp}.{ext}",

    # Branding
    logo_path=Path("assets/logo.png"),
    color_primary="#2c3e50",
    color_secondary="#3498db",
    color_success="#27ae60",
    color_warning="#f39c12",
    color_danger="#e74c3c"
)
```

### Custom Templates

```python
from trinity.reporting import TemplateEngine, ReportTemplate, TemplateSection

# Initialize template engine
template_engine = TemplateEngine()

# Create custom template
custom_template = template_engine.create_custom_template(
    name="safety_only",
    description="Safety-focused report",
    base_template="full_report",
    enabled_sections=[
        "title_page",
        "executive_summary",
        "safety_analysis",
        "charts"
    ]
)

# Save template
template_engine.save_template(custom_template)
```

### Custom Charts

```python
from trinity.reporting import ChartGenerator, ChartConfig

# Configure chart generator
chart_config = ChartConfig(
    dpi=200,
    figsize=(12, 8),
    primary_color="#1e3a5f",
    secondary_color="#4a90e2"
)

chart_gen = ChartGenerator(chart_config)

# Generate custom charts
chart_gen.create_pie_chart(
    data={'car': 100, 'pedestrian': 50, 'cyclist': 25},
    title="Detection Distribution",
    output_path=Path("charts/custom_pie.png")
)

chart_gen.create_bar_chart(
    data={'Session 1': 45, 'Session 2': 62, 'Session 3': 38},
    title="Events by Session",
    output_path=Path("charts/custom_bar.png"),
    horizontal=True
)
```

---

## Scheduled Reports

### Setup Scheduler

```python
from trinity.reporting import ReportScheduler, ScheduledReport
from trinity.reporting import ScheduleFrequency, ReportType, ReportFormat

# Create scheduler
scheduler = ReportScheduler()

# Daily summary at 6 PM
daily_schedule = ScheduledReport(
    name="daily_summary",
    report_type=ReportType.SESSION_SUMMARY,
    format=ReportFormat.HTML,
    frequency=ScheduleFrequency.DAILY,
    hour=18  # 6 PM
)

scheduler.add_schedule(daily_schedule)

# Weekly full report on Monday at 9 AM
weekly_schedule = ScheduledReport(
    name="weekly_full",
    report_type=ReportType.FULL_REPORT,
    format=ReportFormat.PDF,
    frequency=ScheduleFrequency.WEEKLY,
    day_of_week=0,  # Monday
    hour=9
)

scheduler.add_schedule(weekly_schedule)

# Start scheduler
scheduler.start()
```

### Session-End Reports

```python
# Create session-end report
session_end = ScheduledReport(
    name="session_end_report",
    report_type=ReportType.SESSION_SUMMARY,
    format=ReportFormat.HTML,
    frequency=ScheduleFrequency.SESSION_END
)

scheduler.add_schedule(session_end)

# Trigger manually when session ends
scheduler.trigger_report("session_end_report", session_summary)
```

### Custom Intervals

```python
# Report every 4 hours
custom_schedule = ScheduledReport(
    name="four_hourly",
    report_type=ReportType.SESSION_SUMMARY,
    format=ReportFormat.JSON,
    frequency=ScheduleFrequency.CUSTOM,
    custom_interval_seconds=4 * 3600  # 4 hours
)

scheduler.add_schedule(custom_schedule)
```

### Callbacks

```python
def on_report_success(report_path: Path):
    """Called when report generation succeeds"""
    print(f"Report generated: {report_path}")
    # Send email, upload to cloud, etc.

def on_report_error(error: Exception):
    """Called when report generation fails"""
    print(f"Report generation failed: {error}")
    # Send alert, log to monitoring system, etc.

# Add callbacks to schedule
schedule = ScheduledReport(
    name="monitored_report",
    report_type=ReportType.FULL_REPORT,
    format=ReportFormat.PDF,
    frequency=ScheduleFrequency.DAILY,
    hour=12,
    on_success=on_report_success,
    on_error=on_report_error
)

scheduler.add_schedule(schedule)
```

---

## Advanced Features

### Session Filtering

Only generate reports for sessions matching criteria:

```python
def filter_highway_tests(summary: SessionSummary) -> bool:
    """Only generate reports for highway test sessions"""
    return summary.test_type == "highway" and summary.total_events > 0

schedule = ScheduledReport(
    name="highway_reports",
    report_type=ReportType.SAFETY_ANALYSIS,
    format=ReportFormat.PDF,
    frequency=ScheduleFrequency.DAILY,
    hour=18,
    session_filter=filter_highway_tests
)
```

### Chart Generation

Standalone chart generation:

```python
from trinity.reporting import ChartGenerator

chart_gen = ChartGenerator()

# Pie chart
chart_gen.create_pie_chart(
    data=summary.detections_by_class,
    title="Detections by Class",
    output_path=Path("charts/detections.png")
)

# Bar chart with custom colors
severity_colors = {
    'low': '#27ae60',
    'medium': '#f39c12',
    'high': '#e74c3c'
}

chart_gen.create_bar_chart(
    data=summary.events_by_severity,
    title="Events by Severity",
    output_path=Path("charts/events.png"),
    color_map=severity_colors,
    horizontal=True
)

# Line chart
chart_gen.create_line_chart(
    data={
        'Detection FPS': [30, 28, 31, 29, 30],
        'Tracking FPS': [60, 58, 61, 59, 60]
    },
    title="Performance Over Time",
    output_path=Path("charts/performance.png"),
    xlabel="Sample",
    ylabel="FPS"
)

# Timeline chart
events = [
    (10.5, 'critical', 'Near collision detected'),
    (25.3, 'high', 'Hard braking event'),
    (42.1, 'medium', 'Lane departure'),
    (58.7, 'low', 'Close approach')
]

chart_gen.create_timeline_chart(
    data=events,
    title="Safety Events Timeline",
    output_path=Path("charts/timeline.png")
)
```

---

## Integration Example

### Complete Workflow

```python
from trinity.reporting import (
    ReportGenerator, ReportScheduler, ReportConfig,
    SessionSummary, ReportType, ReportFormat,
    ScheduledReport, ScheduleFrequency
)
from pathlib import Path
from datetime import datetime

# 1. Configure report generator
config = ReportConfig(
    title="Trinity AV Test Reports",
    company="Autonomous Vehicles Inc.",
    output_dir=Path("reports"),
    include_charts=True,
    chart_dpi=150
)

generator = ReportGenerator(config)

# 2. Set up scheduler
scheduler = ReportScheduler(report_generator=generator)

# 3. Add scheduled reports
schedules = [
    # Daily HTML summary
    ScheduledReport(
        name="daily_html",
        report_type=ReportType.SESSION_SUMMARY,
        format=ReportFormat.HTML,
        frequency=ScheduleFrequency.DAILY,
        hour=18
    ),

    # Weekly PDF full report
    ScheduledReport(
        name="weekly_pdf",
        report_type=ReportType.FULL_REPORT,
        format=ReportFormat.PDF,
        frequency=ScheduleFrequency.WEEKLY,
        day_of_week=0,  # Monday
        hour=9
    ),

    # Monthly Excel report
    ScheduledReport(
        name="monthly_excel",
        report_type=ReportType.FULL_REPORT,
        format=ReportFormat.EXCEL,
        frequency=ScheduleFrequency.MONTHLY,
        day_of_month=1,
        hour=8
    ),
]

for schedule in schedules:
    scheduler.add_schedule(schedule)

# 4. Start scheduler
scheduler.start()

# 5. Generate on-demand report
session_summary = SessionSummary(
    session_id=42,
    session_name="Downtown Navigation Test",
    test_type="urban",
    start_time=datetime.now(),
    end_time=None,
    duration_seconds=1800,
    total_frames=54000,
    total_detections=8500,
    total_tracks=125,
    total_events=3,
    avg_fps=30.0
)

report_path = generator.generate_session_report(
    session_summary,
    report_type=ReportType.FULL_REPORT,
    output_format=ReportFormat.PDF
)

print(f"Generated: {report_path}")
```

---

## API Reference

### ReportGenerator

Main class for generating reports.

**Methods:**
- `generate_session_report(summary, report_type, output_format)` - Generate report
- `_generate_pdf_report(summary, output_path, report_type)` - Generate PDF
- `_generate_html_report(summary, output_path, report_type)` - Generate HTML
- `_generate_excel_report(summary, output_path, report_type)` - Generate Excel
- `_generate_json_report(summary, output_path, report_type)` - Generate JSON

### ReportScheduler

Manages scheduled report generation.

**Methods:**
- `add_schedule(scheduled_report)` - Add schedule
- `remove_schedule(name)` - Remove schedule
- `start()` - Start scheduler
- `stop()` - Stop scheduler
- `trigger_report(name, session_summary)` - Manual trigger
- `get_status()` - Get scheduler status

### TemplateEngine

Manages report templates.

**Methods:**
- `get_template(name)` - Get template
- `list_templates()` - List all templates
- `add_template(template)` - Add template
- `create_custom_template(name, description, base_template, enabled_sections)` - Create custom
- `save_template(template)` - Save to file
- `load_template(filename)` - Load from file

### ChartGenerator

Generates charts and visualizations.

**Methods:**
- `create_pie_chart(data, title, output_path, ...)` - Pie chart
- `create_bar_chart(data, title, output_path, ...)` - Bar chart
- `create_line_chart(data, title, output_path, ...)` - Line chart
- `create_heatmap(data, title, output_path, ...)` - Heatmap
- `create_timeline_chart(data, title, output_path, ...)` - Timeline

---

## Dependencies

### Required
- `matplotlib` - Chart generation
- `numpy` - Numerical operations
- `loguru` - Logging

### Optional
- `reportlab` - PDF generation
- `openpyxl` - Excel generation
- `jinja2` - HTML templates

### Install All

```bash
pip install matplotlib numpy loguru reportlab openpyxl jinja2
```

---

## File Structure

```
trinity/reporting/
├── __init__.py              # Package exports
├── report_generator.py      # Main report generator (1,100 lines)
├── template_engine.py       # Template management (400 lines)
├── chart_generator.py       # Chart generation (600 lines)
├── scheduler.py             # Report scheduling (450 lines)
├── templates/               # HTML templates
│   └── report_template.html
└── README.md               # This file
```

**Total Code:** ~2,550 lines

---

## Performance

- **PDF Generation:** ~2-5 seconds for full report
- **HTML Generation:** ~1-3 seconds
- **Excel Generation:** ~3-7 seconds
- **Chart Generation:** ~0.5-1 second per chart

*Times vary based on data volume and chart complexity*

---

## Examples

See the `examples/` directory for complete working examples:

- `basic_report.py` - Simple report generation
- `custom_template.py` - Custom template creation
- `scheduled_reports.py` - Automated scheduling
- `chart_generation.py` - Standalone chart creation
- `integration.py` - Full Trinity integration

---

## Troubleshooting

### PDF Generation Fails

**Error:** `reportlab not found`

**Solution:**
```bash
pip install reportlab
```

### Charts Not Rendering

**Error:** `TclError: no display name`

**Solution:** Ensure matplotlib is using 'Agg' backend (already configured)

### Excel Charts Missing

**Error:** Charts not appearing in Excel

**Solution:** Ensure `openpyxl` version >= 3.0

---

## License

Copyright © 2025 Sherin-SEF-AI
Part of Trinity Phase 2 - Autonomous Vehicle Testing Platform

---

## Support

For issues or questions, please check:
- Project documentation
- Example code
- Issue tracker

**Phase 5.2 Complete** ✅
