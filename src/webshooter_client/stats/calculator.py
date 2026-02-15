"""Statistics calculation functions for bests and stats commands."""

import statistics
from typing import Dict, List, Union

from webshooter_client.common.competition_filter import get_result_points
from webshooter_client.models.result import MilitaryResult, PrecisionResult, FieldResult
from webshooter_client.stats.models import BasicStats, SeriesStats, YearlyStats, YoYComparison


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

    count = len(results)
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


def group_results_by_weapon_group(results: List[ResultType]) -> Dict[str, List[ResultType]]:
    """Group results by weapon group (extracted from weapon_class).

    Args:
        results: List of result objects

    Returns:
        Dictionary mapping weapon group (e.g., "C", "A") to results

    """
    grouped: Dict[str, List[ResultType]] = {}

    for result in results:
        if hasattr(result, "signup"):
            weapon_class = result.signup.weapon_class
            # Extract group: "C3" -> "C", "A1" -> "A", "R2" -> "R"
            weapon_group = weapon_class[0] if weapon_class else "?"
        else:
            weapon_group = "?"

        if weapon_group not in grouped:
            grouped[weapon_group] = []
        grouped[weapon_group].append(result)

    return grouped


def group_results_by_year(results: List[ResultType]) -> Dict[int, List[ResultType]]:
    """Group results by year (extracted from competition date).

    Args:
        results: List of result objects (must have signup with competition)

    Returns:
        Dictionary mapping year to results

    """
    grouped: Dict[int, List[ResultType]] = {}

    for result in results:
        if hasattr(result, "signup") and hasattr(result.signup, "competition"):
            year = result.signup.competition.competition_date.year
        else:
            year = 0

        if year > 0:
            if year not in grouped:
                grouped[year] = []
            grouped[year].append(result)

    return grouped


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


def calculate_yearly_stats(results: List[ResultType], year: int, num_series: int) -> YearlyStats:
    """Calculate statistics for results in a single year.

    Args:
        results: Results for the year
        year: Year value
        num_series: Number of series (7 or 12)

    Returns:
        YearlyStats object

    """
    # Get weapon class (same for all results in same year/group)
    weapon_class = ""
    if results and hasattr(results[0], "signup"):
        weapon_class = results[0].signup.weapon_class

    weapon_group = weapon_class[0] if weapon_class else "?"

    basic_stats = calculate_basic_stats(results)
    series_stats = (
        calculate_series_stats(results, num_series)
        if num_series > 0
        else (SeriesStats(series_averages={}, strongest_series=0, weakest_series=0, strongest_avg=0.0, weakest_avg=0.0))
    )

    return YearlyStats(
        year=year,
        weapon_class=weapon_class,
        weapon_group=weapon_group,
        basic_stats=basic_stats,
        series_stats=series_stats,
    )


def calculate_year_over_year(yearly_stats: Dict[int, YearlyStats]) -> List[YoYComparison]:
    """Calculate year-over-year comparisons between consecutive years.

    Args:
        yearly_stats: Dictionary mapping year to YearlyStats

    Returns:
        List of YoYComparison objects for consecutive years

    """
    comparisons = []
    sorted_years = sorted(yearly_stats.keys())

    for i in range(len(sorted_years) - 1):
        from_year = sorted_years[i]
        to_year = sorted_years[i + 1]
        from_stats = yearly_stats[from_year]
        to_stats = yearly_stats[to_year]

        from_mean = from_stats.basic_stats.mean
        to_mean = to_stats.basic_stats.mean

        absolute_change = to_mean - from_mean
        percent_change = (absolute_change / from_mean * 100) if from_mean != 0 else 0.0

        # Track class progression
        class_progression = ""
        if from_stats.weapon_class != to_stats.weapon_class:
            class_progression = f"{from_stats.weapon_class}→{to_stats.weapon_class}"

        comparisons.append(
            YoYComparison(
                from_year=from_year,
                to_year=to_year,
                from_stats=from_stats,
                to_stats=to_stats,
                absolute_change=absolute_change,
                percent_change=percent_change,
                class_progression=class_progression,
            )
        )

    return comparisons


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
