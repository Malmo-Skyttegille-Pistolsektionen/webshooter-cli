"""Tests for stats calculator functions."""

import pytest
from unittest.mock import Mock

from webshooter_client.models.result import PrecisionResult, MilitaryResult, FieldResult, SeriesResult
from webshooter_client.stats.calculator import (
    calculate_basic_stats,
    calculate_series_stats,
    group_results_by_weapon_group,
    group_results_by_year,
    get_num_series,
    calculate_yearly_stats,
    calculate_year_over_year,
    calculate_trend,
)


def create_precision_result(points: int, xs_count: int = 0) -> PrecisionResult:
    """Create a test precision result with the given points.

    Creates 7 series that sum to the requested points value.
    Note: After refactor, calculate_basic_stats uses sum(series) not result.points.
    """
    signup = Mock()
    signup.weapon_class = "C3"

    # Distribute points evenly across 7 series
    points_per_series = points // 7
    remainder = points % 7

    series = []
    for i in range(7):
        # Add remainder to first series to ensure exact total
        series_points = points_per_series + (1 if i < remainder else 0)
        series.append(SeriesResult(points=series_points, inner_tens=1 if i < xs_count else 0))

    return PrecisionResult(
        signup=signup,
        placement=1,
        std_medal=None,
        points=points,  # Keep for consistency but sum(series) is used in calculations
        series=series,
    )


def create_military_result(points: int, xs_count: int = 0) -> MilitaryResult:
    """Create a test military result with the given points."""
    signup = Mock()
    signup.weapon_class = "C3"

    series = [SeriesResult(points=43 + i % 2, inner_tens=1 if i < xs_count else 0) for i in range(12)]

    return MilitaryResult(
        signup=signup,
        placement=1,
        std_medal=None,
        points=points,
        series=series,
    )


def test_calculate_basic_stats_empty():
    """Test basic stats with empty results list."""
    stats = calculate_basic_stats([])
    assert stats.count == 0
    assert stats.mean == 0.0
    assert stats.stdev == 0.0


def test_calculate_basic_stats_single_result():
    """Test basic stats with single result."""
    result = create_precision_result(325, xs_count=8)
    stats = calculate_basic_stats([result])

    assert stats.count == 1
    assert stats.mean == 325.0
    assert stats.median == 325.0
    assert stats.stdev == 0.0  # No stdev with single result
    assert stats.min_score == 325
    assert stats.max_score == 325


def test_calculate_basic_stats_multiple_results():
    """Test basic stats with multiple precision results."""
    results = [create_precision_result(points) for points in [325, 318, 312, 308, 305, 302, 300, 295, 290, 285]]
    stats = calculate_basic_stats(results)

    assert stats.count == 10
    assert stats.mean == pytest.approx(304.0, abs=1.0)
    assert stats.median == pytest.approx(304.0, abs=1.0)
    assert stats.stdev > 0  # Should have stdev with >1 results
    assert stats.min_score == 285
    assert stats.max_score == 325


def test_calculate_series_stats_precision():
    """Test series stats calculation for precision results."""
    results = [create_precision_result(points) for points in range(300, 320)]
    series_stats = calculate_series_stats(results, num_series=7)

    # Should have averages for all 7 series
    assert len(series_stats.series_averages) == 7
    for series_pos in range(1, 8):
        assert series_pos in series_stats.series_averages
        assert 40 < series_stats.series_averages[series_pos] < 50  # Realistic range

    # Should identify strongest and weakest
    assert series_stats.strongest_series in range(1, 8)
    assert series_stats.weakest_series in range(1, 8)
    assert series_stats.strongest_avg >= series_stats.weakest_avg


def test_calculate_series_stats_military():
    """Test series stats calculation for military results."""
    results = [create_military_result(points) for points in range(500, 520)]
    series_stats = calculate_series_stats(results, num_series=12)

    assert len(series_stats.series_averages) == 12
    assert series_stats.strongest_series in range(1, 13)
    assert series_stats.weakest_series in range(1, 13)


def test_calculate_series_stats_empty():
    """Test series stats with empty results."""
    series_stats = calculate_series_stats([], num_series=7)
    assert len(series_stats.series_averages) == 7
    # All should be 0 since no results


def test_group_results_by_weapon_group():
    """Test grouping results by weapon group."""
    signup_c = Mock()
    signup_c.weapon_class = "C3"

    signup_a = Mock()
    signup_a.weapon_class = "A2"

    result_c = PrecisionResult(signup=signup_c, placement=1, std_medal=None, points=325, series=[])
    result_a = PrecisionResult(signup=signup_a, placement=2, std_medal=None, points=320, series=[])

    grouped = group_results_by_weapon_group([result_c, result_a])

    assert "C" in grouped
    assert "A" in grouped
    assert len(grouped["C"]) == 1
    assert len(grouped["A"]) == 1


def test_group_results_by_year():
    """Test grouping results by year."""
    from datetime import date

    signup_2023 = Mock()
    signup_2023.weapon_class = "C3"
    signup_2023.competition = Mock()
    signup_2023.competition.competition_date = date(2023, 7, 10)

    signup_2024 = Mock()
    signup_2024.weapon_class = "C3"
    signup_2024.competition = Mock()
    signup_2024.competition.competition_date = date(2024, 7, 10)

    result_2023 = PrecisionResult(signup=signup_2023, placement=1, std_medal=None, points=300, series=[])
    result_2024 = PrecisionResult(signup=signup_2024, placement=1, std_medal=None, points=310, series=[])

    grouped = group_results_by_year([result_2023, result_2024])

    assert 2023 in grouped
    assert 2024 in grouped
    assert len(grouped[2023]) == 1
    assert len(grouped[2024]) == 1


def test_get_num_series():
    """Test num_series detection for different result types."""
    precision = PrecisionResult(signup=None, placement=0, std_medal=None, points=0, series=[])
    military = MilitaryResult(signup=None, placement=0, std_medal=None, points=0, series=[])
    field = FieldResult(signup=None, placement=0, std_medal=None, points=0, stations=[])

    assert get_num_series(precision) == 7
    assert get_num_series(military) == 12
    assert get_num_series(field) == 0


def test_calculate_yearly_stats():
    """Test yearly stats calculation."""
    results = [create_precision_result(points) for points in range(300, 310)]
    yearly_stats = calculate_yearly_stats(results, year=2024, num_series=7)

    assert yearly_stats.year == 2024
    assert yearly_stats.weapon_class == "C3"
    assert yearly_stats.weapon_group == "C"
    assert yearly_stats.basic_stats.count == 10
    assert len(yearly_stats.series_stats.series_averages) == 7


def test_calculate_year_over_year():
    """Test year-over-year comparison calculation."""
    from datetime import date

    signup_2023 = Mock()
    signup_2023.weapon_class = "C2"
    signup_2023.competition = Mock()
    signup_2023.competition.competition_date = date(2023, 7, 10)

    # 7 series × 43 points = 301 (sum of series)
    result_2023 = PrecisionResult(
        signup=signup_2023,
        placement=1,
        std_medal=None,
        points=301,
        series=[SeriesResult(points=43, inner_tens=1) for _ in range(7)],
    )

    signup_2024 = Mock()
    signup_2024.weapon_class = "C3"
    signup_2024.competition = Mock()
    signup_2024.competition.competition_date = date(2024, 7, 10)

    # 7 series × 45 points = 315 (sum of series)
    result_2024 = PrecisionResult(
        signup=signup_2024,
        placement=1,
        std_medal=None,
        points=315,
        series=[SeriesResult(points=45, inner_tens=1) for _ in range(7)],
    )

    yearly_stats = {
        2023: calculate_yearly_stats([result_2023], 2023, 7),
        2024: calculate_yearly_stats([result_2024], 2024, 7),
    }

    comparisons = calculate_year_over_year(yearly_stats)

    assert len(comparisons) == 1
    comparison = comparisons[0]
    assert comparison.from_year == 2023
    assert comparison.to_year == 2024
    assert comparison.absolute_change == pytest.approx(14.0)  # 315 - 301
    assert comparison.percent_change == pytest.approx(4.65, abs=0.1)  # (14 / 301) * 100
    assert comparison.class_progression == "C2→C3"


def test_calculate_trend_single_year():
    """Test trend calculation with single year."""
    yearly_stats = {2024: Mock()}
    trend = calculate_trend(yearly_stats)
    assert trend == 0.0


def test_calculate_trend_no_change():
    """Test trend calculation with no change."""
    signup = Mock()
    signup.weapon_class = "C3"
    signup.competition = Mock()
    signup.competition.competition_date = __import__("datetime").date(2024, 1, 1)

    result = PrecisionResult(
        signup=signup,
        placement=1,
        std_medal=None,
        points=300,
        series=[SeriesResult(points=45, inner_tens=1) for _ in range(7)],
    )

    yearly_stats = {
        2022: calculate_yearly_stats([result], 2022, 7),
        2024: calculate_yearly_stats([result], 2024, 7),
    }

    trend = calculate_trend(yearly_stats)
    assert trend == pytest.approx(0.0, abs=0.1)


def test_calculate_trend_positive_change():
    """Test trend calculation with positive change."""
    signup_2022 = Mock()
    signup_2022.weapon_class = "C3"
    signup_2022.competition = Mock()
    signup_2022.competition.competition_date = __import__("datetime").date(2022, 1, 1)

    # 7 series × 42 points = 294 (sum of series)
    result_2022 = PrecisionResult(
        signup=signup_2022,
        placement=1,
        std_medal=None,
        points=294,
        series=[SeriesResult(points=42, inner_tens=1) for _ in range(7)],
    )

    signup_2024 = Mock()
    signup_2024.weapon_class = "C3"
    signup_2024.competition = Mock()
    signup_2024.competition.competition_date = __import__("datetime").date(2024, 1, 1)

    # 7 series × 45 points = 315 (sum of series)
    result_2024 = PrecisionResult(
        signup=signup_2024,
        placement=1,
        std_medal=None,
        points=315,
        series=[SeriesResult(points=45, inner_tens=1) for _ in range(7)],
    )

    yearly_stats = {
        2022: calculate_yearly_stats([result_2022], 2022, 7),
        2024: calculate_yearly_stats([result_2024], 2024, 7),
    }

    trend = calculate_trend(yearly_stats)
    # (315 - 294) / (2024 - 2022) = 21 / 2 = 10.5 points/year
    assert trend == pytest.approx(10.5, abs=0.1)
