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
