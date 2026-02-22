"""Statistics calculation functions for bests and stats commands."""

import statistics
from typing import Dict, List, Optional, Tuple, Union

from webshooter_client.common.competition_filter import get_result_points, get_field_result_hits
from webshooter_client.models.result import MilitaryResult, PrecisionResult, FieldResult
from webshooter_client.stats.models import BasicStats, FieldYearlyStats, SeriesStats, YearlyStats


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


def calculate_field_station_deviations(
    my_result: FieldResult,
    medal_results: List[FieldResult],
) -> Tuple[Dict[int, float], float, float]:
    """Calculate per-station hit deviations from std medal winners.

    Computes (my_hits_at_station - std_medal_avg_hits_at_station) for each station.
    Positive = above std medal average, Negative = below.

    Args:
        my_result: The shooter's FieldResult for this competition
        medal_results: All results from std medal winners (std_medal is not None) in this competition

    Returns:
        Tuple of:
          - Dict mapping station index (1-based) to deviation
          - Total hits deviation (my total hits - std medal avg total hits)
          - Total figures deviation (my total figures - std medal avg total figures)
    """
    if not medal_results:
        return {}, 0.0, 0.0

    num_stations = len(my_result.stations)
    station_deviations: Dict[int, float] = {}

    for station_idx in range(num_stations):
        my_hits = my_result.stations[station_idx].hits

        # Average std medal winner hits at this station
        medal_station_hits = [r.stations[station_idx].hits for r in medal_results if len(r.stations) > station_idx]
        if not medal_station_hits:
            continue

        medal_avg = statistics.mean(medal_station_hits)
        station_deviations[station_idx + 1] = my_hits - medal_avg

    # Total hits deviation
    my_total = get_field_result_hits(my_result) or 0
    medal_totals = [get_field_result_hits(r) for r in medal_results if get_field_result_hits(r) is not None]
    total_deviation = (my_total - statistics.mean(medal_totals)) if medal_totals else 0.0

    # Total figures deviation
    from webshooter_client.common.competition_filter import get_field_result_figures

    my_figs = get_field_result_figures(my_result) or 0
    medal_figs = [get_field_result_figures(r) for r in medal_results if get_field_result_figures(r) is not None]
    total_figures_deviation = float(my_figs - statistics.mean(medal_figs)) if medal_figs else 0.0

    return station_deviations, total_deviation, total_figures_deviation


def calculate_field_yearly_stats(
    competition_data: List[Tuple[FieldResult, List[FieldResult]]],
    year: int,
) -> Optional[FieldYearlyStats]:
    """Calculate FieldYearlyStats for a set of (my_result, medal_results) pairs.

    Args:
        competition_data: List of (my_result, medal_winners_for_that_competition) pairs
        year: Year value

    Returns:
        FieldYearlyStats or None if no data
    """
    if not competition_data:
        return None

    weapon_class = ""
    if competition_data[0][0].signup:
        weapon_class = competition_data[0][0].signup.weapon_class

    num_competitions = len(competition_data)

    # Aggregate per-competition stats
    all_hits: List[int] = []
    all_figures: List[int] = []
    all_points: List[int] = []
    station_deviations_accum: Dict[int, List[float]] = {}
    total_deviations: List[float] = []
    total_figures_deviations: List[float] = []
    misses_per_station_list: List[float] = []
    num_with_medal_data = 0

    for my_result, medal_results in competition_data:
        my_total_hits = get_field_result_hits(my_result) or 0
        my_figures = sum(s.figure_hits or 0 for s in my_result.stations)
        my_points = sum(s.points or 0 for s in my_result.stations)

        all_hits.append(my_total_hits)
        all_figures.append(my_figures)
        all_points.append(my_points)

        # Misses per station: (6 - avg_hits_per_station)
        n_stations = len(my_result.stations)
        if n_stations > 0:
            avg_hits_per_station = my_total_hits / n_stations
            misses_per_station_list.append(6.0 - avg_hits_per_station)

        if medal_results:
            num_with_medal_data += 1
            station_devs, total_dev, total_figs_dev = calculate_field_station_deviations(my_result, medal_results)
            total_deviations.append(total_dev)
            total_figures_deviations.append(total_figs_dev)
            for station_pos, dev in station_devs.items():
                if station_pos not in station_deviations_accum:
                    station_deviations_accum[station_pos] = []
                station_deviations_accum[station_pos].append(dev)

    # Compute averages
    avg_hits = statistics.mean(all_hits) if all_hits else 0.0
    avg_points = statistics.mean(all_points) if all_points else 0.0
    avg_misses_per_station = statistics.mean(misses_per_station_list) if misses_per_station_list else 0.0
    total_deviation = statistics.mean(total_deviations) if total_deviations else 0.0
    total_figures_deviation = statistics.mean(total_figures_deviations) if total_figures_deviations else 0.0

    station_deviations_avg = {pos: statistics.mean(devs) for pos, devs in station_deviations_accum.items()}

    return FieldYearlyStats(
        year=year,
        weapon_class=weapon_class,
        num_competitions=num_competitions,
        avg_hits=avg_hits,
        avg_points=avg_points,
        station_deviations=station_deviations_avg,
        total_deviation=total_deviation,
        total_figures_deviation=total_figures_deviation,
        avg_misses_per_station=avg_misses_per_station,
        num_with_medal_data=num_with_medal_data,
    )


def calculate_field_trend(yearly_stats: Dict[int, FieldYearlyStats]) -> float:
    """Calculate trend (avg hits per year) across multiple Field years.

    Args:
        yearly_stats: Dictionary mapping year to FieldYearlyStats

    Returns:
        Average hits change per year (slope of linear trend)
    """
    if len(yearly_stats) < 2:
        return 0.0

    sorted_years = sorted(yearly_stats.keys())
    first_year = sorted_years[0]
    last_year = sorted_years[-1]
    year_range = last_year - first_year

    if year_range == 0:
        return 0.0

    return (yearly_stats[last_year].avg_hits - yearly_stats[first_year].avg_hits) / year_range
