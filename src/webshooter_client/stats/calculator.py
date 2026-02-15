"""Statistics calculation functions for bests and stats commands."""

import statistics
from typing import Dict, List, Union

from webshooter_client.common.competition_filter import get_result_points
from webshooter_client.models.result import MilitaryResult, PrecisionResult, FieldResult
from webshooter_client.stats.models import BasicStats, SeriesStats, YearlyStats


def get_weapon_group(weapon_class: str) -> str:
    """Extract weapon group from weapon class.

    Args:
        weapon_class: Weapon class string (e.g., "C3", "A1", "R2")

    Returns:
        First character of weapon_class, or "?" if empty/None

    """
    return weapon_class[0] if weapon_class else "?"


ResultType = Union[PrecisionResult, MilitaryResult, FieldResult]


def calculate_basic_stats(results: List[ResultType]) -> BasicStats:
    """Calculate basic statistics for a set of results.

    For Precision: Uses sum of series (excludes finals).
    For Military: Uses result.points directly.

    Args:
        results: List of result objects

    Returns:
        BasicStats object with calculated values

    """
    if not results:
        return BasicStats(count=0, mean=0.0, median=0.0, stdev=0.0, min_score=0, max_score=0, avg_xs=0.0)

    points = [get_result_points(r) for r in results]
    points = [p for p in points if p is not None]  # Filter out None values

    xs = [sum(s.inner_tens for s in r.series) for r in results if hasattr(r, "series")]

    count = len(points)
    mean = statistics.mean(points) if points else 0.0
    median = statistics.median(points) if points else 0.0
    stdev = statistics.stdev(points) if len(points) > 1 else 0.0
    min_score = min(points) if points else 0
    max_score = max(points) if points else 0
    avg_xs = statistics.mean(xs) if xs else 0.0

    return BasicStats(
        count=count, mean=mean, median=median, stdev=stdev, min_score=min_score, max_score=max_score, avg_xs=avg_xs
    )


def calculate_series_stats(results: List[ResultType], num_series: int) -> SeriesStats:
    """Calculate series-level statistics for results.

    Args:
        results: List of result objects (must have series attribute)
        num_series: Number of series (7 for Precision, 12 for Military)

    Returns:
        SeriesStats object with series averages and strongest/weakest

    """
    series_averages: Dict[int, float] = {}

    # Calculate average for each series position
    for series_pos in range(1, num_series + 1):
        series_points = []
        for result in results:
            if hasattr(result, "series") and len(result.series) >= series_pos:
                series_points.append(result.series[series_pos - 1].points)

        if series_points:
            series_averages[series_pos] = statistics.mean(series_points)
        else:
            series_averages[series_pos] = 0.0

    # Find strongest and weakest
    if series_averages:
        strongest_series = max(series_averages, key=series_averages.get)
        weakest_series = min(series_averages, key=series_averages.get)
    else:
        strongest_series = 1
        weakest_series = 1

    strongest_avg = series_averages.get(strongest_series, 0.0)
    weakest_avg = series_averages.get(weakest_series, 0.0)

    return SeriesStats(
        series_averages=series_averages,
        strongest_series=strongest_series,
        weakest_series=weakest_series,
        strongest_avg=strongest_avg,
        weakest_avg=weakest_avg,
    )


def get_num_series(result: ResultType) -> int:
    """Determine number of series for a result type.

    Args:
        result: Result object (Precision/Military/Field)

    Returns:
        Number of series (7 for Precision, 12 for Military, 0 for Field/unknown)

    """
    if isinstance(result, PrecisionResult):
        return 7
    elif isinstance(result, MilitaryResult):
        return 12
    else:
        return 0  # Field results don't use series


def calculate_yearly_stats(
    results: List[ResultType], year: int, num_series: int, compute_series_stats: bool = False
) -> YearlyStats:
    """Calculate statistics for results in a single year.

    Args:
        results: Results for the year
        year: Year value
        num_series: Number of series (7 or 12)
        compute_series_stats: If False (default), series_stats will be empty to save computation

    Returns:
        YearlyStats object

    """
    # Get weapon class (same for all results in same year/group)
    weapon_class = ""
    if results and hasattr(results[0], "signup"):
        weapon_class = results[0].signup.weapon_class

    weapon_group = get_weapon_group(weapon_class)

    basic_stats = calculate_basic_stats(results)
    series_stats = (
        calculate_series_stats(results, num_series)
        if compute_series_stats and num_series > 0
        else SeriesStats(series_averages={}, strongest_series=0, weakest_series=0, strongest_avg=0.0, weakest_avg=0.0)
    )

    return YearlyStats(
        year=year,
        weapon_class=weapon_class,
        weapon_group=weapon_group,
        basic_stats=basic_stats,
        series_stats=series_stats,
    )


def calculate_trend(yearly_stats: Dict[int, YearlyStats]) -> float:
    """Calculate overall trend (points per year) across multiple years.

    Args:
        yearly_stats: Dictionary mapping year to YearlyStats

    Returns:
        Points per year (slope of linear trend)

    """
    if len(yearly_stats) < 2:
        return 0.0

    sorted_years = sorted(yearly_stats.keys())
    first_year = sorted_years[0]
    last_year = sorted_years[-1]
    year_range = last_year - first_year

    if year_range == 0:
        return 0.0

    first_mean = yearly_stats[first_year].basic_stats.mean
    last_mean = yearly_stats[last_year].basic_stats.mean
    absolute_change = last_mean - first_mean

    return absolute_change / year_range
