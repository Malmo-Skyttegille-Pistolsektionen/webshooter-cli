"""Data classes for statistics calculations."""

from dataclasses import dataclass, field
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


@dataclass
class SeriesStats:
    """Statistics for each series position."""

    series_averages: Dict[int, float]  # {1: 45.2, 2: 44.8, ...}
    strongest_series: int
    weakest_series: int
    strongest_avg: float
    weakest_avg: float


@dataclass
class YearlyStats:
    """Statistics for a single year."""

    year: int
    weapon_class: str  # e.g., "C3", "A1", "R2"
    weapon_group: str  # e.g., "C", "A", "R"
    basic_stats: BasicStats
    series_stats: SeriesStats


@dataclass
class FieldYearlyStats:
    """Statistics for a single year of Field competitions."""

    year: int
    weapon_class: str
    num_competitions: int
    avg_hits: float
    avg_points: float
    # Per-station deviation from std medal winners (station index 1-based -> avg deviation)
    # Positive = above medal average, Negative = below medal average
    station_deviations: Dict[int, float] = field(default_factory=dict)
    # Average total hits deviation from std medal winners across all competitions
    total_deviation: float = 0.0
    # Average total figures deviation from std medal winners across all competitions
    total_figures_deviation: float = 0.0
    # Average misses per station (6 - avg_hits_per_station)
    avg_misses_per_station: float = 0.0
    # Number of competitions where std medal winner data was available
    num_with_medal_data: int = 0
