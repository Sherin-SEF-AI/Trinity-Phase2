"""
Trinity Template Engine
Manages customizable report templates
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
from loguru import logger


@dataclass
class TemplateSection:
    """Represents a section in a report template"""
    name: str
    title: str
    enabled: bool = True
    order: int = 0
    subsections: List[str] = None

    def __post_init__(self):
        if self.subsections is None:
            self.subsections = []


@dataclass
class ReportTemplate:
    """Report template configuration"""
    name: str
    description: str
    format: str  # pdf, html, excel
    sections: List[TemplateSection]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TemplateEngine:
    """
    Manages report templates

    Features:
    - Load/save custom templates
    - Template validation
    - Section ordering and filtering
    - Template inheritance
    """

    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize template engine

        Args:
            template_dir: Directory for template storage
        """
        self.template_dir = template_dir or Path(__file__).parent / "templates"
        self.template_dir.mkdir(parents=True, exist_ok=True)

        self.templates: Dict[str, ReportTemplate] = {}

        # Load default templates
        self._load_default_templates()

        logger.info(f"Template engine initialized with {len(self.templates)} templates")

    def _load_default_templates(self):
        """Load default report templates"""

        # Full report template
        full_template = ReportTemplate(
            name="full_report",
            description="Complete test report with all sections",
            format="pdf",
            sections=[
                TemplateSection("title_page", "Title Page", order=1),
                TemplateSection("executive_summary", "Executive Summary", order=2),
                TemplateSection("session_details", "Session Details", order=3),
                TemplateSection("statistics", "Statistics", order=4, subsections=[
                    "detection_stats",
                    "tracking_stats",
                    "performance_stats"
                ]),
                TemplateSection("charts", "Visual Analysis", order=5),
                TemplateSection("safety_analysis", "Safety Analysis", order=6, subsections=[
                    "ttc_analysis",
                    "near_miss_events",
                    "hard_braking"
                ]),
                TemplateSection("edge_cases", "Edge Case Analysis", order=7),
                TemplateSection("recommendations", "Recommendations", order=8, enabled=False),
            ]
        )
        self.templates["full_report"] = full_template

        # Safety-focused template
        safety_template = ReportTemplate(
            name="safety_report",
            description="Safety-focused report",
            format="pdf",
            sections=[
                TemplateSection("title_page", "Title Page", order=1),
                TemplateSection("executive_summary", "Executive Summary", order=2),
                TemplateSection("safety_analysis", "Safety Analysis", order=3, subsections=[
                    "ttc_analysis",
                    "near_miss_events",
                    "hard_braking",
                    "safe_distance_violations"
                ]),
                TemplateSection("events_timeline", "Events Timeline", order=4),
                TemplateSection("charts", "Safety Charts", order=5),
            ]
        )
        self.templates["safety_report"] = safety_template

        # Edge case template
        edge_case_template = ReportTemplate(
            name="edge_case_report",
            description="Edge case analysis report",
            format="pdf",
            sections=[
                TemplateSection("title_page", "Title Page", order=1),
                TemplateSection("edge_cases", "Edge Case Analysis", order=2, subsections=[
                    "by_category",
                    "by_severity",
                    "detailed_list"
                ]),
                TemplateSection("charts", "Edge Case Charts", order=3),
                TemplateSection("recommendations", "Dataset Curation Recommendations", order=4),
            ]
        )
        self.templates["edge_case_report"] = edge_case_template

        # Quick summary template
        quick_template = ReportTemplate(
            name="quick_summary",
            description="Quick summary report",
            format="html",
            sections=[
                TemplateSection("executive_summary", "Summary", order=1),
                TemplateSection("statistics", "Key Statistics", order=2),
                TemplateSection("charts", "Charts", order=3),
            ]
        )
        self.templates["quick_summary"] = quick_template

    def get_template(self, name: str) -> Optional[ReportTemplate]:
        """Get template by name"""
        return self.templates.get(name)

    def list_templates(self) -> List[str]:
        """List available template names"""
        return list(self.templates.keys())

    def add_template(self, template: ReportTemplate):
        """Add or update a template"""
        self.templates[template.name] = template
        logger.info(f"Template added: {template.name}")

    def remove_template(self, name: str) -> bool:
        """Remove a template"""
        if name in self.templates:
            del self.templates[name]
            logger.info(f"Template removed: {name}")
            return True
        return False

    def save_template(self, template: ReportTemplate, filename: Optional[str] = None):
        """Save template to file"""
        if filename is None:
            filename = f"{template.name}.json"

        filepath = self.template_dir / filename

        template_dict = {
            'name': template.name,
            'description': template.description,
            'format': template.format,
            'metadata': template.metadata,
            'sections': [
                {
                    'name': s.name,
                    'title': s.title,
                    'enabled': s.enabled,
                    'order': s.order,
                    'subsections': s.subsections
                }
                for s in template.sections
            ]
        }

        with filepath.open('w') as f:
            json.dump(template_dict, f, indent=2)

        logger.info(f"Template saved: {filepath}")

    def load_template(self, filename: str) -> Optional[ReportTemplate]:
        """Load template from file"""
        filepath = self.template_dir / filename

        if not filepath.exists():
            logger.error(f"Template file not found: {filepath}")
            return None

        try:
            with filepath.open('r') as f:
                data = json.load(f)

            sections = [
                TemplateSection(
                    name=s['name'],
                    title=s['title'],
                    enabled=s.get('enabled', True),
                    order=s.get('order', 0),
                    subsections=s.get('subsections', [])
                )
                for s in data['sections']
            ]

            template = ReportTemplate(
                name=data['name'],
                description=data['description'],
                format=data['format'],
                sections=sections,
                metadata=data.get('metadata', {})
            )

            self.templates[template.name] = template
            logger.info(f"Template loaded: {template.name}")

            return template

        except Exception as e:
            logger.error(f"Error loading template: {e}")
            return None

    def get_enabled_sections(self, template_name: str) -> List[TemplateSection]:
        """Get enabled sections for a template, sorted by order"""
        template = self.get_template(template_name)
        if not template:
            return []

        enabled = [s for s in template.sections if s.enabled]
        return sorted(enabled, key=lambda s: s.order)

    def validate_template(self, template: ReportTemplate) -> Tuple[bool, List[str]]:
        """
        Validate template configuration

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check required fields
        if not template.name:
            errors.append("Template name is required")

        if not template.format:
            errors.append("Template format is required")

        if template.format not in ['pdf', 'html', 'excel', 'json']:
            errors.append(f"Invalid format: {template.format}")

        # Check sections
        if not template.sections:
            errors.append("Template must have at least one section")

        # Check for duplicate section names
        section_names = [s.name for s in template.sections]
        if len(section_names) != len(set(section_names)):
            errors.append("Duplicate section names found")

        # Check order values
        orders = [s.order for s in template.sections if s.enabled]
        if orders and (min(orders) < 0 or len(set(orders)) != len(orders)):
            errors.append("Section orders must be unique and non-negative")

        return len(errors) == 0, errors

    def create_custom_template(
        self,
        name: str,
        description: str,
        base_template: str = "full_report",
        enabled_sections: Optional[List[str]] = None
    ) -> Optional[ReportTemplate]:
        """
        Create a custom template based on an existing template

        Args:
            name: New template name
            description: Template description
            base_template: Name of template to use as base
            enabled_sections: List of section names to enable (None = all)

        Returns:
            New template or None if base template not found
        """
        base = self.get_template(base_template)
        if not base:
            logger.error(f"Base template not found: {base_template}")
            return None

        # Create new sections based on base
        new_sections = []
        for section in base.sections:
            enabled = True
            if enabled_sections is not None:
                enabled = section.name in enabled_sections

            new_section = TemplateSection(
                name=section.name,
                title=section.title,
                enabled=enabled,
                order=section.order,
                subsections=section.subsections.copy()
            )
            new_sections.append(new_section)

        # Create new template
        new_template = ReportTemplate(
            name=name,
            description=description,
            format=base.format,
            sections=new_sections,
            metadata={'base_template': base_template}
        )

        # Validate
        is_valid, errors = self.validate_template(new_template)
        if not is_valid:
            logger.error(f"Template validation failed: {errors}")
            return None

        self.add_template(new_template)
        return new_template
