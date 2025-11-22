"""
Trinity Chart Generator
Generates charts and visualizations for reports
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from loguru import logger

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure
from matplotlib.axes import Axes


@dataclass
class ChartConfig:
    """Configuration for chart generation"""
    dpi: int = 150
    style: str = "seaborn-v0_8-darkgrid"
    figsize: Tuple[int, int] = (10, 6)

    # Colors
    primary_color: str = "#2c3e50"
    secondary_color: str = "#3498db"
    success_color: str = "#27ae60"
    warning_color: str = "#f39c12"
    danger_color: str = "#e74c3c"

    # Font sizes
    title_fontsize: int = 14
    label_fontsize: int = 12
    tick_fontsize: int = 10


class ChartGenerator:
    """
    Generates charts and visualizations for reports

    Features:
    - Pie charts for distributions
    - Bar charts for comparisons
    - Line charts for time series
    - Heatmaps for correlations
    - Custom styling and branding
    """

    def __init__(self, config: Optional[ChartConfig] = None):
        """
        Initialize chart generator

        Args:
            config: Chart configuration
        """
        self.config = config or ChartConfig()

        # Set matplotlib style
        try:
            plt.style.use(self.config.style)
        except:
            logger.warning(f"Chart style '{self.config.style}' not available")

        logger.info("Chart generator initialized")

    # ========================================================================
    # Pie Charts
    # ========================================================================

    def create_pie_chart(
        self,
        data: Dict[str, float],
        title: str,
        output_path: Path,
        show_percentages: bool = True,
        explode_max: bool = False
    ) -> bool:
        """
        Create a pie chart

        Args:
            data: Dictionary of labels and values
            title: Chart title
            output_path: Output file path
            show_percentages: Show percentage labels
            explode_max: Explode the largest slice

        Returns:
            True if successful
        """
        try:
            fig, ax = plt.subplots(
                figsize=self.config.figsize,
                dpi=self.config.dpi
            )

            labels = list(data.keys())
            values = list(data.values())

            # Explode
            explode = None
            if explode_max and values:
                max_idx = values.index(max(values))
                explode = [0.1 if i == max_idx else 0 for i in range(len(values))]

            # Create pie chart
            autopct = '%1.1f%%' if show_percentages else None

            wedges, texts, autotexts = ax.pie(
                values,
                labels=[self._format_label(l) for l in labels],
                autopct=autopct,
                startangle=90,
                explode=explode
            )

            # Style text
            for text in texts:
                text.set_fontsize(self.config.tick_fontsize)

            if autotexts:
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontsize(self.config.tick_fontsize - 1)
                    autotext.set_weight('bold')

            ax.set_title(
                title,
                fontsize=self.config.title_fontsize,
                fontweight='bold',
                pad=20
            )

            plt.tight_layout()
            plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight')
            plt.close()

            logger.debug(f"Pie chart created: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error creating pie chart: {e}")
            return False

    # ========================================================================
    # Bar Charts
    # ========================================================================

    def create_bar_chart(
        self,
        data: Dict[str, float],
        title: str,
        output_path: Path,
        xlabel: str = "",
        ylabel: str = "Count",
        horizontal: bool = False,
        color_map: Optional[Dict[str, str]] = None,
        show_values: bool = True
    ) -> bool:
        """
        Create a bar chart

        Args:
            data: Dictionary of labels and values
            title: Chart title
            output_path: Output file path
            xlabel: X-axis label
            ylabel: Y-axis label
            horizontal: Create horizontal bar chart
            color_map: Custom color mapping for categories
            show_values: Show value labels on bars

        Returns:
            True if successful
        """
        try:
            fig, ax = plt.subplots(
                figsize=self.config.figsize,
                dpi=self.config.dpi
            )

            # Sort by value (descending)
            sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
            labels = [item[0] for item in sorted_items]
            values = [item[1] for item in sorted_items]

            # Get colors
            if color_map:
                colors = [color_map.get(label, self.config.secondary_color) for label in labels]
            else:
                colors = self.config.secondary_color

            # Create bar chart
            if horizontal:
                bars = ax.barh(
                    range(len(labels)),
                    values,
                    color=colors
                )
                ax.set_yticks(range(len(labels)))
                ax.set_yticklabels([self._format_label(l) for l in labels])
                ax.set_xlabel(ylabel, fontsize=self.config.label_fontsize)
                ax.set_ylabel(xlabel, fontsize=self.config.label_fontsize)

                # Add value labels
                if show_values:
                    for i, bar in enumerate(bars):
                        width = bar.get_width()
                        ax.text(
                            width,
                            bar.get_y() + bar.get_height() / 2,
                            f' {self._format_value(width)}',
                            ha='left',
                            va='center',
                            fontweight='bold',
                            fontsize=self.config.tick_fontsize - 1
                        )
            else:
                bars = ax.bar(
                    range(len(labels)),
                    values,
                    color=colors
                )
                ax.set_xticks(range(len(labels)))
                ax.set_xticklabels(
                    [self._format_label(l) for l in labels],
                    rotation=45,
                    ha='right'
                )
                ax.set_xlabel(xlabel, fontsize=self.config.label_fontsize)
                ax.set_ylabel(ylabel, fontsize=self.config.label_fontsize)

                # Add value labels
                if show_values:
                    for bar in bars:
                        height = bar.get_height()
                        ax.text(
                            bar.get_x() + bar.get_width() / 2,
                            height,
                            f'{self._format_value(height)}',
                            ha='center',
                            va='bottom',
                            fontweight='bold',
                            fontsize=self.config.tick_fontsize - 1
                        )

            ax.set_title(
                title,
                fontsize=self.config.title_fontsize,
                fontweight='bold',
                pad=20
            )

            ax.tick_params(labelsize=self.config.tick_fontsize)
            plt.tight_layout()
            plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight')
            plt.close()

            logger.debug(f"Bar chart created: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error creating bar chart: {e}")
            return False

    # ========================================================================
    # Line Charts
    # ========================================================================

    def create_line_chart(
        self,
        data: Dict[str, List[float]],
        title: str,
        output_path: Path,
        xlabel: str = "Time",
        ylabel: str = "Value",
        x_values: Optional[List] = None,
        show_grid: bool = True,
        show_legend: bool = True
    ) -> bool:
        """
        Create a line chart

        Args:
            data: Dictionary of series names and values
            title: Chart title
            output_path: Output file path
            xlabel: X-axis label
            ylabel: Y-axis label
            x_values: X-axis values (uses indices if None)
            show_grid: Show grid lines
            show_legend: Show legend

        Returns:
            True if successful
        """
        try:
            fig, ax = plt.subplots(
                figsize=self.config.figsize,
                dpi=self.config.dpi
            )

            # Plot each series
            for i, (name, values) in enumerate(data.items()):
                x = x_values if x_values else range(len(values))
                ax.plot(x, values, label=self._format_label(name), linewidth=2)

            ax.set_xlabel(xlabel, fontsize=self.config.label_fontsize)
            ax.set_ylabel(ylabel, fontsize=self.config.label_fontsize)
            ax.set_title(
                title,
                fontsize=self.config.title_fontsize,
                fontweight='bold',
                pad=20
            )

            if show_grid:
                ax.grid(True, alpha=0.3)

            if show_legend and len(data) > 1:
                ax.legend(fontsize=self.config.tick_fontsize)

            ax.tick_params(labelsize=self.config.tick_fontsize)
            plt.tight_layout()
            plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight')
            plt.close()

            logger.debug(f"Line chart created: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error creating line chart: {e}")
            return False

    # ========================================================================
    # Heatmaps
    # ========================================================================

    def create_heatmap(
        self,
        data: np.ndarray,
        title: str,
        output_path: Path,
        row_labels: Optional[List[str]] = None,
        col_labels: Optional[List[str]] = None,
        cmap: str = "YlOrRd",
        show_values: bool = True,
        value_format: str = ".2f"
    ) -> bool:
        """
        Create a heatmap

        Args:
            data: 2D array of values
            title: Chart title
            output_path: Output file path
            row_labels: Row labels
            col_labels: Column labels
            cmap: Colormap name
            show_values: Show values in cells
            value_format: Format string for values

        Returns:
            True if successful
        """
        try:
            fig, ax = plt.subplots(
                figsize=self.config.figsize,
                dpi=self.config.dpi
            )

            # Create heatmap
            im = ax.imshow(data, cmap=cmap, aspect='auto')

            # Set ticks and labels
            if row_labels:
                ax.set_yticks(range(len(row_labels)))
                ax.set_yticklabels(
                    [self._format_label(l) for l in row_labels],
                    fontsize=self.config.tick_fontsize
                )

            if col_labels:
                ax.set_xticks(range(len(col_labels)))
                ax.set_xticklabels(
                    [self._format_label(l) for l in col_labels],
                    rotation=45,
                    ha='right',
                    fontsize=self.config.tick_fontsize
                )

            # Add colorbar
            cbar = plt.colorbar(im, ax=ax)
            cbar.ax.tick_params(labelsize=self.config.tick_fontsize)

            # Show values in cells
            if show_values:
                for i in range(data.shape[0]):
                    for j in range(data.shape[1]):
                        text = ax.text(
                            j, i,
                            format(data[i, j], value_format),
                            ha="center",
                            va="center",
                            color="white" if data[i, j] > data.max() * 0.5 else "black",
                            fontsize=self.config.tick_fontsize - 2
                        )

            ax.set_title(
                title,
                fontsize=self.config.title_fontsize,
                fontweight='bold',
                pad=20
            )

            plt.tight_layout()
            plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight')
            plt.close()

            logger.debug(f"Heatmap created: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error creating heatmap: {e}")
            return False

    # ========================================================================
    # Stacked Bar Charts
    # ========================================================================

    def create_stacked_bar_chart(
        self,
        data: Dict[str, Dict[str, float]],
        title: str,
        output_path: Path,
        xlabel: str = "",
        ylabel: str = "Count",
        horizontal: bool = False
    ) -> bool:
        """
        Create a stacked bar chart

        Args:
            data: Nested dict {category: {subcategory: value}}
            title: Chart title
            output_path: Output file path
            xlabel: X-axis label
            ylabel: Y-axis label
            horizontal: Create horizontal bar chart

        Returns:
            True if successful
        """
        try:
            fig, ax = plt.subplots(
                figsize=self.config.figsize,
                dpi=self.config.dpi
            )

            # Prepare data
            categories = list(data.keys())
            subcategories = list(set(
                sub for cat_data in data.values()
                for sub in cat_data.keys()
            ))

            # Create matrix
            matrix = np.zeros((len(subcategories), len(categories)))
            for i, cat in enumerate(categories):
                for j, subcat in enumerate(subcategories):
                    matrix[j, i] = data[cat].get(subcat, 0)

            # Plot stacked bars
            bottom = np.zeros(len(categories))
            bars = []

            for i, subcat in enumerate(subcategories):
                if horizontal:
                    bar = ax.barh(
                        range(len(categories)),
                        matrix[i],
                        left=bottom,
                        label=self._format_label(subcat)
                    )
                else:
                    bar = ax.bar(
                        range(len(categories)),
                        matrix[i],
                        bottom=bottom,
                        label=self._format_label(subcat)
                    )
                bars.append(bar)
                bottom += matrix[i]

            # Set labels and title
            if horizontal:
                ax.set_yticks(range(len(categories)))
                ax.set_yticklabels([self._format_label(c) for c in categories])
                ax.set_xlabel(ylabel, fontsize=self.config.label_fontsize)
                ax.set_ylabel(xlabel, fontsize=self.config.label_fontsize)
            else:
                ax.set_xticks(range(len(categories)))
                ax.set_xticklabels(
                    [self._format_label(c) for c in categories],
                    rotation=45,
                    ha='right'
                )
                ax.set_xlabel(xlabel, fontsize=self.config.label_fontsize)
                ax.set_ylabel(ylabel, fontsize=self.config.label_fontsize)

            ax.set_title(
                title,
                fontsize=self.config.title_fontsize,
                fontweight='bold',
                pad=20
            )

            ax.legend(fontsize=self.config.tick_fontsize)
            ax.tick_params(labelsize=self.config.tick_fontsize)

            plt.tight_layout()
            plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight')
            plt.close()

            logger.debug(f"Stacked bar chart created: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error creating stacked bar chart: {e}")
            return False

    # ========================================================================
    # Time Series with Events
    # ========================================================================

    def create_timeline_chart(
        self,
        data: List[Tuple[float, str, str]],
        title: str,
        output_path: Path,
        xlabel: str = "Time (s)",
        ylabel: str = "Events"
    ) -> bool:
        """
        Create a timeline chart with events

        Args:
            data: List of (timestamp, event_type, description) tuples
            title: Chart title
            output_path: Output file path
            xlabel: X-axis label
            ylabel: Y-axis label

        Returns:
            True if successful
        """
        try:
            fig, ax = plt.subplots(
                figsize=(12, 6),
                dpi=self.config.dpi
            )

            # Group by event type
            events_by_type: Dict[str, List[float]] = {}
            for timestamp, event_type, desc in data:
                if event_type not in events_by_type:
                    events_by_type[event_type] = []
                events_by_type[event_type].append(timestamp)

            # Color map for event types
            color_map = {
                'critical': self.config.danger_color,
                'high': self.config.warning_color,
                'medium': self.config.secondary_color,
                'low': self.config.success_color,
            }

            # Plot events
            y_pos = 0
            y_labels = []
            y_ticks = []

            for event_type, timestamps in events_by_type.items():
                color = color_map.get(event_type.lower(), self.config.secondary_color)
                ax.scatter(
                    timestamps,
                    [y_pos] * len(timestamps),
                    s=100,
                    c=color,
                    alpha=0.7,
                    label=self._format_label(event_type)
                )
                y_labels.append(self._format_label(event_type))
                y_ticks.append(y_pos)
                y_pos += 1

            ax.set_xlabel(xlabel, fontsize=self.config.label_fontsize)
            ax.set_ylabel(ylabel, fontsize=self.config.label_fontsize)
            ax.set_title(
                title,
                fontsize=self.config.title_fontsize,
                fontweight='bold',
                pad=20
            )

            ax.set_yticks(y_ticks)
            ax.set_yticklabels(y_labels)

            ax.grid(True, alpha=0.3, axis='x')
            ax.legend(fontsize=self.config.tick_fontsize)
            ax.tick_params(labelsize=self.config.tick_fontsize)

            plt.tight_layout()
            plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight')
            plt.close()

            logger.debug(f"Timeline chart created: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error creating timeline chart: {e}")
            return False

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _format_label(self, label: str) -> str:
        """Format label for display"""
        if isinstance(label, str):
            # Replace underscores with spaces and capitalize
            return label.replace('_', ' ').title()
        return str(label)

    def _format_value(self, value: float) -> str:
        """Format value for display"""
        if value >= 1000:
            return f"{value:,.0f}"
        elif value >= 10:
            return f"{value:.0f}"
        else:
            return f"{value:.1f}"
