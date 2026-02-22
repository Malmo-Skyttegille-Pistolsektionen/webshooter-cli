"""Tests for competition filtering utilities."""

from unittest.mock import Mock

from webshooter_client.common.competition_filter import (
    is_valid_precision_result,
    is_valid_military_result,
    get_result_points,
)
from webshooter_client.models.result import PrecisionResult, MilitaryResult, SeriesResult


def create_precision_result(num_series: int = 7, total_points: int = 315) -> PrecisionResult:
    """Create a precision result with specified number of series."""
    signup = Mock()
    signup.weapon_class = "C3"

    if num_series == 0:
        series = []
    else:
        points_per_series = total_points // num_series
        remainder = total_points % num_series

        series = [
            SeriesResult(points=points_per_series + (1 if i < remainder else 0), inner_tens=1)
            for i in range(num_series)
        ]

    return PrecisionResult(
        signup=signup,
        placement=1,
        std_medal=None,
        points=total_points,
        series=series,
    )


def create_military_result(num_series: int = 12, total_points: int = 480) -> MilitaryResult:
    """Create a military result with specified number of series."""
    signup = Mock()
    signup.weapon_class = "C3"

    if num_series == 0:
        series = []
    else:
        points_per_series = total_points // num_series
        remainder = total_points % num_series

        series = [
            SeriesResult(points=points_per_series + (1 if i < remainder else 0), inner_tens=1)
            for i in range(num_series)
        ]

    return MilitaryResult(
        signup=signup,
        placement=1,
        std_medal=None,
        points=total_points,
        series=series,
    )


class TestIsValidPrecisionResult:
    """Tests for is_valid_precision_result function."""

    def test_valid_precision_exactly_7_series(self):
        """Precision result with exactly 7 series is valid."""
        result = create_precision_result(num_series=7)
        assert is_valid_precision_result(result) is True

    def test_invalid_precision_6_series(self):
        """Precision result with 6 series is invalid."""
        result = create_precision_result(num_series=6)
        assert is_valid_precision_result(result) is False

    def test_invalid_precision_8_series(self):
        """Precision result with 8 series is invalid."""
        result = create_precision_result(num_series=8)
        assert is_valid_precision_result(result) is False

    def test_invalid_precision_10_series(self):
        """Precision result with 10 series (non-standard) is invalid."""
        result = create_precision_result(num_series=10)
        assert is_valid_precision_result(result) is False

    def test_invalid_precision_empty_series(self):
        """Precision result with no series is invalid."""
        result = create_precision_result(num_series=0)
        assert is_valid_precision_result(result) is False


class TestIsValidMilitaryResult:
    """Tests for is_valid_military_result function."""

    def test_valid_military_standard_12_series(self):
        """Military result with 12 series is valid."""
        result = create_military_result(num_series=12)
        assert is_valid_military_result(result) is True

    def test_valid_military_any_series_count(self):
        """Military result with any number of series is valid."""
        for num_series in [6, 8, 10, 12, 15]:
            result = create_military_result(num_series=num_series)
            assert is_valid_military_result(result) is True

    def test_invalid_military_no_series(self):
        """Military result with no series is invalid."""
        result = create_military_result(num_series=0)
        assert is_valid_military_result(result) is False

    def test_invalid_military_none_series(self):
        """Military result with None series is invalid."""
        signup = Mock()
        signup.weapon_class = "C3"
        result = MilitaryResult(
            signup=signup,
            placement=1,
            std_medal=None,
            points=480,
            series=None,
        )
        assert is_valid_military_result(result) is False


class TestGetResultPoints:
    """Tests for get_result_points function."""

    def test_precision_returns_series_sum_not_total(self):
        """Precision results use sum of series, not result.points."""
        # Create result with series sum = 315 but points = 350 (simulating finals)
        result = create_precision_result(num_series=7, total_points=315)
        # Override points to simulate finals included
        result.points = 350

        # Should return series sum (315) not result.points (350)
        assert get_result_points(result) == 315

    def test_precision_7_series_valid(self):
        """Valid precision (7 series) returns series sum."""
        result = create_precision_result(num_series=7, total_points=320)
        assert get_result_points(result) == 320

    def test_precision_non_7_series_returns_none(self):
        """Invalid precision (not 7 series) returns None."""
        result = create_precision_result(num_series=10)
        assert get_result_points(result) is None

    def test_military_returns_total_points(self):
        """Military results return result.points directly."""
        result = create_military_result(num_series=12, total_points=480)
        assert get_result_points(result) == 480

    def test_military_any_series_count_valid(self):
        """Military with any series count returns points."""
        for num_series in [6, 8, 12]:
            result = create_military_result(num_series=num_series, total_points=480)
            assert get_result_points(result) == 480

    def test_military_no_series_returns_none(self):
        """Military with no series returns None."""
        result = create_military_result(num_series=0)
        assert get_result_points(result) is None

    def test_military_none_series_returns_none(self):
        """Military with None series returns None."""
        signup = Mock()
        signup.weapon_class = "C3"
        result = MilitaryResult(
            signup=signup,
            placement=1,
            std_medal=None,
            points=480,
            series=None,
        )
        assert get_result_points(result) is None


class TestCompetitionFilterIntegration:
    """Integration tests for filtering utilities."""

    def test_precision_with_finals_excluded(self):
        """Precision with finals shows only base series points."""
        # Competition 259 example: 7-series base + 3-series finals
        # Base: 350 points (7 × 50)
        # Finals: 102 points
        # result.points = 452
        result = create_precision_result(num_series=7, total_points=350)
        result.points = 452  # Simulate finals added to total

        assert is_valid_precision_result(result) is True
        assert get_result_points(result) == 350  # Not 452

    def test_precision_filtering_across_sizes(self):
        """Test filtering works correctly for various precision formats."""
        test_cases = [
            (6, False),  # 6-series: invalid
            (7, True),  # 7-series: valid
            (8, False),  # 8-series: invalid
            (10, False),  # 10-series: invalid
        ]

        for num_series, should_be_valid in test_cases:
            result = create_precision_result(num_series=num_series)
            is_valid = is_valid_precision_result(result)
            assert is_valid == should_be_valid, f"Expected {num_series}-series to be valid={should_be_valid}"

            if should_be_valid:
                points = get_result_points(result)
                assert points is not None
            else:
                points = get_result_points(result)
                assert points is None


def create_field_result_filter(num_stations: int = 8, hits_per_station: int = 5):
    """Create a FieldResult for competition_filter tests."""
    from webshooter_client.models.result import FieldResult, StationResult

    signup = Mock()
    signup.weapon_class = "C3"

    stations = [
        StationResult(hits=hits_per_station, figure_hits=hits_per_station - 1, points=hits_per_station * 2)
        for _ in range(num_stations)
    ]

    return FieldResult(
        signup=signup,
        placement=1,
        std_medal=None,
        points=hits_per_station * num_stations,
        stations=stations,
    )


class TestIsValidFieldResult:
    """Tests for is_valid_field_result function."""

    def test_valid_field_8_stations(self):
        from webshooter_client.common.competition_filter import is_valid_field_result

        assert is_valid_field_result(create_field_result_filter(num_stations=8)) is True

    def test_valid_field_9_stations(self):
        from webshooter_client.common.competition_filter import is_valid_field_result

        assert is_valid_field_result(create_field_result_filter(num_stations=9)) is True

    def test_valid_field_10_stations(self):
        from webshooter_client.common.competition_filter import is_valid_field_result

        assert is_valid_field_result(create_field_result_filter(num_stations=10)) is True

    def test_invalid_field_empty_stations(self):
        from webshooter_client.common.competition_filter import is_valid_field_result
        from webshooter_client.models.result import FieldResult

        signup = Mock()
        signup.weapon_class = "C3"
        result = FieldResult(signup=signup, placement=1, std_medal=None, points=0, stations=[])
        assert is_valid_field_result(result) is False

    def test_invalid_field_none_stations(self):
        from webshooter_client.common.competition_filter import is_valid_field_result
        from webshooter_client.models.result import FieldResult

        signup = Mock()
        signup.weapon_class = "C3"
        result = FieldResult(signup=signup, placement=1, std_medal=None, points=0, stations=None)
        assert is_valid_field_result(result) is False


class TestGetFieldResultHelpers:
    """Tests for get_field_result_hits, figures, and points helpers."""

    def test_get_field_result_hits_sums_stations(self):
        from webshooter_client.common.competition_filter import get_field_result_hits
        from webshooter_client.models.result import FieldResult, StationResult

        signup = Mock()
        signup.weapon_class = "C3"
        stations = [
            StationResult(hits=5, figure_hits=3, points=10),
            StationResult(hits=6, figure_hits=4, points=15),
            StationResult(hits=4, figure_hits=2, points=8),
        ]
        result = FieldResult(signup=signup, placement=1, std_medal=None, points=33, stations=stations)
        assert get_field_result_hits(result) == 15  # 5 + 6 + 4

    def test_get_field_result_hits_invalid_returns_none(self):
        from webshooter_client.common.competition_filter import get_field_result_hits
        from webshooter_client.models.result import FieldResult

        signup = Mock()
        signup.weapon_class = "C3"
        result = FieldResult(signup=signup, placement=1, std_medal=None, points=0, stations=[])
        assert get_field_result_hits(result) is None

    def test_get_field_result_figures(self):
        from webshooter_client.common.competition_filter import get_field_result_figures
        from webshooter_client.models.result import FieldResult, StationResult

        signup = Mock()
        signup.weapon_class = "C3"
        stations = [
            StationResult(hits=5, figure_hits=3, points=0),
            StationResult(hits=5, figure_hits=4, points=0),
        ]
        result = FieldResult(signup=signup, placement=1, std_medal=None, points=0, stations=stations)
        assert get_field_result_figures(result) == 7  # 3 + 4

    def test_get_field_result_figures_handles_none(self):
        from webshooter_client.common.competition_filter import get_field_result_figures
        from webshooter_client.models.result import FieldResult, StationResult

        signup = Mock()
        signup.weapon_class = "C3"
        stations = [
            StationResult(hits=5, figure_hits=None, points=0),
            StationResult(hits=5, figure_hits=3, points=0),
        ]
        result = FieldResult(signup=signup, placement=1, std_medal=None, points=0, stations=stations)
        assert get_field_result_figures(result) == 3

    def test_get_field_result_points_sums_stations(self):
        from webshooter_client.common.competition_filter import get_field_result_points
        from webshooter_client.models.result import FieldResult, StationResult

        signup = Mock()
        signup.weapon_class = "C3"
        stations = [
            StationResult(hits=5, figure_hits=3, points=10),
            StationResult(hits=6, figure_hits=4, points=15),
        ]
        result = FieldResult(signup=signup, placement=1, std_medal=None, points=25, stations=stations)
        assert get_field_result_points(result) == 25  # 10 + 15

    def test_get_result_points_field_returns_total_hits(self):
        """get_result_points for FieldResult returns total hits."""
        result = create_field_result_filter(num_stations=8, hits_per_station=5)
        assert get_result_points(result) == 40  # 8 × 5

    def test_get_result_points_field_invalid_returns_none(self):
        from webshooter_client.models.result import FieldResult

        signup = Mock()
        signup.weapon_class = "C3"
        result = FieldResult(signup=signup, placement=1, std_medal=None, points=0, stations=[])
        assert get_result_points(result) is None
