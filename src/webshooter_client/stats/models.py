"""Data classes for statistics calculations."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class BasicStats:
    """Basic statistics for a set of results."""

    count: int
    mean: float
    median: float
    stdev: float
    min_score: int
    max_score: int
    avg_xs: float

    def __str__(self) -> str:
        """Format as readable string."""
        return (
            f"Total Competitions: {self.count}\n"
            f"Average Score:      {self.mean:.1f} ± {self.stdev:.1f}\n"
            f"Median Score:       {self.median:.0f}\n"
            f"Best/Worst:         {self.max_score} / {self.min_score}\n"
            f"Average Xs:         {self.avg_xs:.1f}"
        )


@dataclass
class SeriesStats:
    """Statistics for each series position."""

    series_averages: Dict[int, float]  # {1: 45.2, 2: 44.8, ...}
    strongest_series: int
    weakest_series: int
    strongest_avg: float
    weakest_avg: float

    def format_series_analysis(self, num_series: int) -> str:
        """Format series-level analysis as readable string."""
        lines = [f"Series Analysis ({num_series} series):"]
        for series_pos in range(1, num_series + 1):
            avg = self.series_averages.get(series_pos, 0.0)
            if series_pos == self.strongest_series:
                lines.append(f"  Series {series_pos}: {avg:.1f} ✓ (strongest)")
            elif series_pos == self.weakest_series:
                lines.append(f"  Series {series_pos}: {avg:.1f} ⚠️ (weakest)")
            else:
                lines.append(f"  Series {series_pos}: {avg:.1f}")
        return "\n".join(lines)


@dataclass
class YearlyStats:
    """Statistics for a single year."""

    year: int
    weapon_class: str  # e.g., "C3", "A1", "R2"
    weapon_group: str  # e.g., "C", "A", "R"
    basic_stats: BasicStats
    series_stats: SeriesStats


@dataclass
class YoYComparison:
    """Year-over-year comparison between two years."""

    from_year: int
    to_year: int
    from_stats: YearlyStats
    to_stats: YearlyStats
    absolute_change: float  # points
    percent_change: float  # %
    class_progression: str  # e.g., "C1→C2", empty if same class

    def format_change(self) -> str:
        """Format year-over-year change as readable string."""
        if self.percent_change >= 0:
            return f"+{self.absolute_change:.1f} points (+{self.percent_change:.1f}%) ⬆️"
        else:
            return f"{self.absolute_change:.1f} points ({self.percent_change:.1f}%) ⬇️"
