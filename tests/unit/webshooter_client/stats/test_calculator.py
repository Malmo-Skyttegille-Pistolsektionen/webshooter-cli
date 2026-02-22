"""Tests for stats calculator functions."""

import pytest
from unittest.mock import Mock

from webshooter_client.models.result import PrecisionResult, MilitaryResult, FieldResult, SeriesResult, StationResult
from webshooter_client.stats.calculator import (
    calculate_basic_stats,
    calculate_series_stats,
    get_num_series,
    calculate_yearly_stats,
    calculate_trend,
    calculate_field_station_deviations,
    calculate_field_yearly_stats,
    calculate_field_trend,
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
    yearly_stats = calculate_yearly_stats(results, year=2024, num_series=7, compute_series_stats=True)

    assert yearly_stats.year == 2024
    assert yearly_stats.weapon_class == "C3"
    assert yearly_stats.weapon_group == "C"
    assert yearly_stats.basic_stats.count == 10
    assert len(yearly_stats.series_stats.series_averages) == 7


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
        2022: calculate_yearly_stats([result], 2022, 7, compute_series_stats=True),
        2024: calculate_yearly_stats([result], 2024, 7, compute_series_stats=True),
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
        2022: calculate_yearly_stats([result_2022], 2022, 7, compute_series_stats=True),
        2024: calculate_yearly_stats([result_2024], 2024, 7, compute_series_stats=True),
    }

    trend = calculate_trend(yearly_stats)
    # (315 - 294) / (2024 - 2022) = 21 / 2 = 10.5 points/year
    assert trend == pytest.approx(10.5, abs=0.1)


def make_field_result_calc(hits_per_station: list, card: str = "10008", std_medal=None):
    """Create FieldResult for calculator tests."""
    signup = Mock()
    signup.weapon_class = "C3"
    signup.shooting_card_number = card
    stations = [StationResult(hits=h, figure_hits=max(0, h - 1), points=h * 2) for h in hits_per_station]
    return FieldResult(signup=signup, placement=1, std_medal=std_medal, points=sum(hits_per_station), stations=stations)


def test_calculate_field_station_deviations_basic():
    """Test station deviation calculation against std medal winners."""
    my_result = make_field_result_calc([4, 5, 6, 4, 5, 6, 4, 5])
    medal1 = make_field_result_calc([5, 6, 6, 5, 6, 6, 5, 6])
    medal2 = make_field_result_calc([6, 5, 6, 6, 5, 6, 6, 5])

    deviations, total_dev, total_figs_dev = calculate_field_station_deviations(my_result, [medal1, medal2])

    # My station 1 hits = 4, medal avg = (5+6)/2 = 5.5, deviation = 4 - 5.5 = -1.5
    assert deviations[1] == pytest.approx(-1.5, abs=0.01)
    assert len(deviations) == 8  # 8 stations
    assert total_dev < 0  # I'm below medal average overall
    assert isinstance(total_figs_dev, float)  # Figures deviation returned


def test_calculate_field_station_deviations_no_medals():
    """Test deviation with no std medal winners returns empty dict."""
    my_result = make_field_result_calc([5, 6, 4, 6, 5])

    deviations, total_dev, total_figs_dev = calculate_field_station_deviations(my_result, [])

    assert deviations == {}
    assert total_dev == 0.0
    assert total_figs_dev == 0.0


def test_calculate_field_station_deviations_above_medal():
    """Test positive deviation when shooter beats medal average."""
    my_result = make_field_result_calc([6, 6, 6, 6])
    medal = make_field_result_calc([4, 4, 4, 4])

    deviations, total_dev, total_figs_dev = calculate_field_station_deviations(my_result, [medal])

    assert all(d > 0 for d in deviations.values())
    assert total_dev > 0
    assert isinstance(total_figs_dev, float)


def test_calculate_field_yearly_stats_basic():
    """Test FieldYearlyStats calculation."""
    my1 = make_field_result_calc([5, 6, 4, 6, 5, 6, 4, 6])  # 42 hits
    my2 = make_field_result_calc([6, 5, 6, 4, 6, 5, 6, 4])  # 42 hits
    medal1 = make_field_result_calc([6, 6, 6, 6, 6, 6, 6, 6])  # 48 hits
    medal2 = make_field_result_calc([5, 5, 5, 5, 5, 5, 5, 5])  # 40 hits

    comp_data = [(my1, [medal1, medal2]), (my2, [medal1, medal2])]
    stats = calculate_field_yearly_stats(comp_data, year=2024)

    assert stats is not None
    assert stats.year == 2024
    assert stats.num_competitions == 2
    assert stats.weapon_class == "C3"
    assert stats.avg_hits == pytest.approx(42.0, abs=0.1)
    assert stats.num_with_medal_data == 2
    # Medal avg = (48 + 40) / 2 = 44 hits, my avg = 42, total_dev = -2
    assert stats.total_deviation == pytest.approx(-2.0, abs=0.1)


def test_calculate_field_yearly_stats_no_medals():
    """Test FieldYearlyStats with no medal data."""
    my1 = make_field_result_calc([5, 5, 5, 5, 5])
    comp_data = [(my1, [])]
    stats = calculate_field_yearly_stats(comp_data, year=2024)

    assert stats is not None
    assert stats.num_with_medal_data == 0
    assert stats.total_deviation == 0.0
    assert stats.station_deviations == {}


def test_calculate_field_yearly_stats_empty():
    """Test FieldYearlyStats with no data returns None."""
    stats = calculate_field_yearly_stats([], year=2024)
    assert stats is None


def test_calculate_field_trend():
    """Test field trend calculation."""
    my_2022 = make_field_result_calc([4, 4, 4, 4, 4, 4, 4, 4])  # 32 hits
    my_2024 = make_field_result_calc([5, 5, 5, 5, 5, 5, 5, 5])  # 40 hits

    stats_2022 = calculate_field_yearly_stats([(my_2022, [])], year=2022)
    stats_2024 = calculate_field_yearly_stats([(my_2024, [])], year=2024)

    trend = calculate_field_trend({2022: stats_2022, 2024: stats_2024})
    # (40 - 32) / (2024 - 2022) = 8 / 2 = 4.0 hits/year
    assert trend == pytest.approx(4.0, abs=0.1)


def test_calculate_field_trend_single_year():
    """Test field trend with single year returns 0."""
    my1 = make_field_result_calc([5, 5, 5])
    stats = calculate_field_yearly_stats([(my1, [])], year=2024)
    trend = calculate_field_trend({2024: stats})
    assert trend == 0.0
