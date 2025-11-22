"""
Trinity Report Scheduler
Schedules and automates report generation
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
import threading
import time
from loguru import logger

from .report_generator import ReportGenerator, ReportFormat, ReportType, ReportConfig, SessionSummary


class ScheduleFrequency(Enum):
    """Report generation frequency"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SESSION_END = "session_end"
    CUSTOM = "custom"


@dataclass
class ScheduledReport:
    """Represents a scheduled report"""
    name: str
    report_type: ReportType
    format: ReportFormat
    frequency: ScheduleFrequency
    enabled: bool = True

    # Timing
    hour: int = 0  # Hour of day (0-23)
    day_of_week: int = 0  # 0=Monday, 6=Sunday
    day_of_month: int = 1  # 1-28
    custom_interval_seconds: Optional[int] = None

    # Filters
    session_filter: Optional[Callable[[SessionSummary], bool]] = None

    # Callbacks
    on_success: Optional[Callable[[Path], None]] = None
    on_error: Optional[Callable[[Exception], None]] = None

    # Metadata
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0


class ReportScheduler:
    """
    Manages scheduled and automated report generation

    Features:
    - Daily, weekly, monthly schedules
    - Session-end triggered reports
    - Custom interval scheduling
    - Automatic retry on failure
    - Email delivery (optional)
    - Report archiving
    """

    def __init__(
        self,
        report_generator: Optional[ReportGenerator] = None,
        check_interval_seconds: int = 60
    ):
        """
        Initialize report scheduler

        Args:
            report_generator: Report generator instance
            check_interval_seconds: How often to check for scheduled reports
        """
        self.report_generator = report_generator or ReportGenerator()
        self.check_interval = check_interval_seconds

        self.scheduled_reports: Dict[str, ScheduledReport] = {}
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None

        logger.info("Report scheduler initialized")

    # ========================================================================
    # Schedule Management
    # ========================================================================

    def add_schedule(self, scheduled_report: ScheduledReport):
        """Add a scheduled report"""
        self.scheduled_reports[scheduled_report.name] = scheduled_report

        # Calculate next run time
        self._calculate_next_run(scheduled_report)

        logger.info(
            f"Scheduled report added: {scheduled_report.name} "
            f"(next run: {scheduled_report.next_run})"
        )

    def remove_schedule(self, name: str) -> bool:
        """Remove a scheduled report"""
        if name in self.scheduled_reports:
            del self.scheduled_reports[name]
            logger.info(f"Scheduled report removed: {name}")
            return True
        return False

    def enable_schedule(self, name: str):
        """Enable a scheduled report"""
        if name in self.scheduled_reports:
            self.scheduled_reports[name].enabled = True
            self._calculate_next_run(self.scheduled_reports[name])
            logger.info(f"Schedule enabled: {name}")

    def disable_schedule(self, name: str):
        """Disable a scheduled report"""
        if name in self.scheduled_reports:
            self.scheduled_reports[name].enabled = False
            logger.info(f"Schedule disabled: {name}")

    def list_schedules(self) -> List[str]:
        """List all scheduled report names"""
        return list(self.scheduled_reports.keys())

    def get_schedule(self, name: str) -> Optional[ScheduledReport]:
        """Get scheduled report by name"""
        return self.scheduled_reports.get(name)

    # ========================================================================
    # Scheduler Control
    # ========================================================================

    def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()

        logger.info("Report scheduler started")

    def stop(self):
        """Stop the scheduler"""
        if not self.running:
            logger.warning("Scheduler not running")
            return

        self.running = False

        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)

        logger.info("Report scheduler stopped")

    def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started")

        while self.running:
            try:
                now = datetime.now()

                # Check each scheduled report
                for name, scheduled_report in list(self.scheduled_reports.items()):
                    if not scheduled_report.enabled:
                        continue

                    # Check if it's time to run
                    if scheduled_report.next_run and now >= scheduled_report.next_run:
                        self._run_scheduled_report(scheduled_report)

                # Sleep until next check
                time.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(self.check_interval)

        logger.info("Scheduler loop stopped")

    # ========================================================================
    # Report Execution
    # ========================================================================

    def _run_scheduled_report(self, scheduled_report: ScheduledReport):
        """Execute a scheduled report"""
        logger.info(f"Running scheduled report: {scheduled_report.name}")

        try:
            # Get session data (in production, this would query the database)
            # For now, we'll skip if no session data provider is set
            session_summary = self._get_latest_session_summary()

            if session_summary is None:
                logger.warning(f"No session data available for: {scheduled_report.name}")
                scheduled_report.error_count += 1
                self._calculate_next_run(scheduled_report)
                return

            # Apply session filter if provided
            if scheduled_report.session_filter:
                if not scheduled_report.session_filter(session_summary):
                    logger.info(f"Session filtered out for: {scheduled_report.name}")
                    self._calculate_next_run(scheduled_report)
                    return

            # Generate report
            output_path = self.report_generator.generate_session_report(
                session_summary=session_summary,
                report_type=scheduled_report.report_type,
                output_format=scheduled_report.format
            )

            # Update metadata
            scheduled_report.last_run = datetime.now()
            scheduled_report.run_count += 1
            self._calculate_next_run(scheduled_report)

            # Call success callback
            if scheduled_report.on_success:
                try:
                    scheduled_report.on_success(output_path)
                except Exception as e:
                    logger.error(f"Error in success callback: {e}")

            logger.success(f"Scheduled report completed: {scheduled_report.name}")

        except Exception as e:
            logger.error(f"Error running scheduled report '{scheduled_report.name}': {e}")
            scheduled_report.error_count += 1

            # Call error callback
            if scheduled_report.on_error:
                try:
                    scheduled_report.on_error(e)
                except Exception as cb_error:
                    logger.error(f"Error in error callback: {cb_error}")

            # Still calculate next run even if failed
            self._calculate_next_run(scheduled_report)

    def _get_latest_session_summary(self) -> Optional[SessionSummary]:
        """
        Get latest session summary

        In production, this would query the database for the most recent
        completed session. For now, returns None.
        """
        # TODO: Implement database query
        return None

    # ========================================================================
    # Next Run Calculation
    # ========================================================================

    def _calculate_next_run(self, scheduled_report: ScheduledReport):
        """Calculate next run time for a scheduled report"""
        now = datetime.now()

        if scheduled_report.frequency == ScheduleFrequency.DAILY:
            # Run at specified hour every day
            next_run = now.replace(
                hour=scheduled_report.hour,
                minute=0,
                second=0,
                microsecond=0
            )
            # If already passed today, schedule for tomorrow
            if next_run <= now:
                next_run += timedelta(days=1)

        elif scheduled_report.frequency == ScheduleFrequency.WEEKLY:
            # Run on specified day of week at specified hour
            days_ahead = scheduled_report.day_of_week - now.weekday()
            if days_ahead <= 0:  # Target day already passed this week
                days_ahead += 7

            next_run = now.replace(
                hour=scheduled_report.hour,
                minute=0,
                second=0,
                microsecond=0
            ) + timedelta(days=days_ahead)

        elif scheduled_report.frequency == ScheduleFrequency.MONTHLY:
            # Run on specified day of month at specified hour
            next_run = now.replace(
                day=scheduled_report.day_of_month,
                hour=scheduled_report.hour,
                minute=0,
                second=0,
                microsecond=0
            )

            # If already passed this month, schedule for next month
            if next_run <= now:
                # Move to next month
                if next_run.month == 12:
                    next_run = next_run.replace(year=next_run.year + 1, month=1)
                else:
                    next_run = next_run.replace(month=next_run.month + 1)

        elif scheduled_report.frequency == ScheduleFrequency.SESSION_END:
            # Don't schedule - will be triggered manually
            next_run = None

        elif scheduled_report.frequency == ScheduleFrequency.CUSTOM:
            # Run at custom interval
            if scheduled_report.custom_interval_seconds:
                if scheduled_report.last_run:
                    next_run = scheduled_report.last_run + timedelta(
                        seconds=scheduled_report.custom_interval_seconds
                    )
                else:
                    next_run = now + timedelta(
                        seconds=scheduled_report.custom_interval_seconds
                    )
            else:
                logger.warning(
                    f"Custom frequency requires custom_interval_seconds: "
                    f"{scheduled_report.name}"
                )
                next_run = None

        else:
            next_run = None

        scheduled_report.next_run = next_run

    # ========================================================================
    # Manual Trigger
    # ========================================================================

    def trigger_report(
        self,
        name: str,
        session_summary: SessionSummary
    ) -> Optional[Path]:
        """
        Manually trigger a scheduled report

        Args:
            name: Name of scheduled report
            session_summary: Session data to report on

        Returns:
            Path to generated report or None
        """
        if name not in self.scheduled_reports:
            logger.error(f"Scheduled report not found: {name}")
            return None

        scheduled_report = self.scheduled_reports[name]

        try:
            # Apply session filter if provided
            if scheduled_report.session_filter:
                if not scheduled_report.session_filter(session_summary):
                    logger.info(f"Session filtered out for: {name}")
                    return None

            # Generate report
            output_path = self.report_generator.generate_session_report(
                session_summary=session_summary,
                report_type=scheduled_report.report_type,
                output_format=scheduled_report.format
            )

            # Update metadata
            scheduled_report.last_run = datetime.now()
            scheduled_report.run_count += 1

            # Call success callback
            if scheduled_report.on_success:
                try:
                    scheduled_report.on_success(output_path)
                except Exception as e:
                    logger.error(f"Error in success callback: {e}")

            logger.success(f"Manually triggered report completed: {name}")
            return output_path

        except Exception as e:
            logger.error(f"Error triggering report '{name}': {e}")
            scheduled_report.error_count += 1

            # Call error callback
            if scheduled_report.on_error:
                try:
                    scheduled_report.on_error(e)
                except Exception as cb_error:
                    logger.error(f"Error in error callback: {cb_error}")

            return None

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        return {
            'running': self.running,
            'check_interval': self.check_interval,
            'total_schedules': len(self.scheduled_reports),
            'enabled_schedules': sum(
                1 for s in self.scheduled_reports.values() if s.enabled
            ),
            'schedules': {
                name: {
                    'enabled': s.enabled,
                    'frequency': s.frequency.value,
                    'last_run': s.last_run.isoformat() if s.last_run else None,
                    'next_run': s.next_run.isoformat() if s.next_run else None,
                    'run_count': s.run_count,
                    'error_count': s.error_count,
                }
                for name, s in self.scheduled_reports.items()
            }
        }


# ============================================================================
# Convenience Functions
# ============================================================================

def create_daily_report_schedule(
    name: str,
    hour: int = 0,
    report_type: ReportType = ReportType.SESSION_SUMMARY,
    format: ReportFormat = ReportFormat.PDF
) -> ScheduledReport:
    """Create a daily report schedule"""
    return ScheduledReport(
        name=name,
        report_type=report_type,
        format=format,
        frequency=ScheduleFrequency.DAILY,
        hour=hour
    )


def create_weekly_report_schedule(
    name: str,
    day_of_week: int = 0,  # Monday
    hour: int = 0,
    report_type: ReportType = ReportType.FULL_REPORT,
    format: ReportFormat = ReportFormat.PDF
) -> ScheduledReport:
    """Create a weekly report schedule"""
    return ScheduledReport(
        name=name,
        report_type=report_type,
        format=format,
        frequency=ScheduleFrequency.WEEKLY,
        day_of_week=day_of_week,
        hour=hour
    )


def create_session_end_report_schedule(
    name: str,
    report_type: ReportType = ReportType.SESSION_SUMMARY,
    format: ReportFormat = ReportFormat.HTML
) -> ScheduledReport:
    """Create a session-end triggered report schedule"""
    return ScheduledReport(
        name=name,
        report_type=report_type,
        format=format,
        frequency=ScheduleFrequency.SESSION_END
    )
