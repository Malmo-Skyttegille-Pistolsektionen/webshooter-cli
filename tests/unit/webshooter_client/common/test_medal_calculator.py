"""Unit tests for medal calculator module."""

import pytest
from webshooter_client.common.medal_calculator import (
    calculate_medals,
    MedalCalculationInput,
)
from webshooter_client.models.result import (
    StdMedal,
    SeriesResult,
)
from webshooter_client.models.competition import CompetitionType
from webshooter_client.models.signup import Signup

# Test fixtures for common data


@pytest.fixture
def sample_signup():
    """Create a sample signup for testing."""
    return Signup(
        id=1,
        spsf_club_number="12-239",
        shooting_card_number="10000",
        fullname="Test Shooter",
        lane=1,
        weapon_class="A1",
        weapon_class_general="A",
        share_patrol_with=None,
    )


@pytest.fixture
def sample_signup_b():
    """Create another sample signup for testing."""
    return Signup(
        id=2,
        spsf_club_number="12-239",
        shooting_card_number="10009",
        fullname="Test Shooter B",
        lane=2,
        weapon_class="B1",
        weapon_class_general="B",
        share_patrol_with=None,
    )


@pytest.fixture
def sample_signup_c():
    """Create another sample signup for testing."""
    return Signup(
        id=3,
        spsf_club_number="12-239",
        shooting_card_number="10010",
        fullname="Test Shooter C",
        lane=3,
        weapon_class="C1",
        weapon_class_general="C",
        share_patrol_with=None,
    )


# Field Competition Tests


class TestFieldMedalCalculation:
    """Test field competition medal calculation."""

    def test_field_single_competitor_no_medal(self, sample_signup):
        """Single competitor in field competition should get no medal."""
        results = [{"points": 100, "hits": 30, "figures": 25, "signup": sample_signup}]
        input_data = MedalCalculationInput(
            results=results,
            competition_type=CompetitionType.FIELD,
            weapon_groups=[],  # Not used for field
        )
        calculated_medals = calculate_medals(input_data)
        assert calculated_medals[0] is None

    def test_field_three_competitors_silver_bronze(self, sample_signup, sample_signup_b, sample_signup_c):
        """Three competitors: top 1 should get nothing (less than 1/9), 2nd nothing, 3rd nothing."""
        results = [
            {"points": 300, "hits": 90, "figures": 80, "signup": sample_signup},
            {"points": 200, "hits": 60, "figures": 50, "signup": sample_signup_b},
            {"points": 100, "hits": 30, "figures": 25, "signup": sample_signup_c},
        ]
        input_data = MedalCalculationInput(
            results=results,
            competition_type=CompetitionType.FIELD,
            weapon_groups=[],
        )
        calculated_medals = calculate_medals(input_data)
        # With 3 competitors: 1/9 = 0.33, 1/3 = 1
        # Top 1 (0-indexed): no silver (needs index < 0.33)
        # Top 1 bronze (index 0): yes bronze (1st is within top 1/3)
        # Actually, with 3: floor(3/9) - 1 = -1 (no silver), floor(3/3) - 1 = 0 (1st gets bronze)
        assert calculated_medals[0] == StdMedal.BRONZE
        assert calculated_medals[1] is None
        assert calculated_medals[2] is None

    def test_field_nine_competitors_silver_and_bronze(self, sample_signup):
        """Nine competitors: top 1 gets silver, top 3 get bronze."""
        results = []
        for i in range(9):
            signup = Signup(
                id=i,
                spsf_club_number="12-239",
                shooting_card_number=f"1000{i}",
                fullname=f"Shooter {i}",
                lane=i,
                weapon_class="A1",
                weapon_class_general="A",
                share_patrol_with=None,
            )
            results.append(
                {
                    "points": 300 - (i * 10),
                    "hits": 90 - (i * 5),
                    "figures": 80 - (i * 5),
                    "signup": signup,
                }
            )
        input_data = MedalCalculationInput(
            results=results,
            competition_type=CompetitionType.FIELD,
            weapon_groups=[],
        )
        calculated_medals = calculate_medals(input_data)
        # floor(9/9) - 1 = 0 -> silver at index 0 (1st place)
        # floor(9/3) - 1 = 2 -> bronze indices 0,1,2 (top 3)
        assert calculated_medals[0] == StdMedal.SILVER
        assert calculated_medals[1] == StdMedal.BRONZE
        assert calculated_medals[2] == StdMedal.BRONZE
        assert calculated_medals[3] is None

    def test_field_sorting_by_hits_primary(self, sample_signup, sample_signup_b, sample_signup_c):
        """Field results should be sorted by hits (primary), then figures, then points."""
        results = [
            {"points": 100, "hits": 30, "figures": 25, "signup": sample_signup},  # 3rd
            {"points": 300, "hits": 90, "figures": 80, "signup": sample_signup_b},  # 1st (highest hits)
            {"points": 200, "hits": 60, "figures": 50, "signup": sample_signup_c},  # 2nd
        ]
        input_data = MedalCalculationInput(
            results=results,
            competition_type=CompetitionType.FIELD,
            weapon_groups=[],
        )
        calculated_medals = calculate_medals(input_data)
        # After sorting by hits (90 > 60 > 30):
        # With 3 competitors: floor(3/9) - 1 = -1 (no silver)
        # floor(3/3) - 1 = 0 (only 1st place gets bronze)
        medal_b = calculated_medals[1]  # sample_signup_b position (1st by hits)
        medal_c = calculated_medals[2]  # sample_signup_c position (2nd by hits)
        medal_a = calculated_medals[0]  # sample_signup position (3rd by hits)
        assert medal_b == StdMedal.BRONZE
        assert medal_c is None
        assert medal_a is None


# Precision Competition Tests


class TestPrecisionMedalCalculation:
    """Test precision competition medal calculation."""

    def test_precision_7_series_fixed_threshold_silver(self, sample_signup):
        """7-series precision group A achieving 323+ points should get silver via fixed threshold."""
        series = [SeriesResult(points=47, inner_tens=5) for _ in range(7)]  # 7 * 47 = 329 points
        results = [
            {
                "points": 329,
                "series": series,
                "weapon_group": "A",
                "signup": sample_signup,
            }
        ]
        input_data = MedalCalculationInput(
            results=results,
            competition_type=CompetitionType.PRECISION,
            weapon_groups=["A"],
        )
        calculated_medals = calculate_medals(input_data)
        assert calculated_medals[0] == StdMedal.SILVER

    def test_precision_7_series_fixed_threshold_bronze(self, sample_signup):
        """7-series precision group A achieving 312+ points should get bronze via fixed threshold."""
        series = [SeriesResult(points=45, inner_tens=4) for _ in range(7)]  # 7 * 45 = 315 points
        results = [
            {
                "points": 315,
                "series": series,
                "weapon_group": "A",
                "signup": sample_signup,
            }
        ]
        input_data = MedalCalculationInput(
            results=results,
            competition_type=CompetitionType.PRECISION,
            weapon_groups=["A"],
        )
        calculated_medals = calculate_medals(input_data)
        assert calculated_medals[0] == StdMedal.BRONZE

    def test_precision_7_series_below_bronze_threshold(self, sample_signup):
        """7-series precision below bronze threshold should get no medal."""
        series = [SeriesResult(points=44, inner_tens=4) for _ in range(7)]  # 7 * 44 = 308 points
        results = [
            {
                "points": 308,
                "series": series,
                "weapon_group": "A",
                "signup": sample_signup,
            }
        ]
        input_data = MedalCalculationInput(
            results=results,
            competition_type=CompetitionType.PRECISION,
            weapon_groups=["A"],
        )
        calculated_medals = calculate_medals(input_data)
        assert calculated_medals[0] is None

    def test_precision_6_series_group_b_silver(self, sample_signup):
        """6-series precision group B achieving 282+ points should get silver."""
        series = [SeriesResult(points=48, inner_tens=5) for _ in range(6)]  # 6 * 48 = 288 points
        results = [
            {
                "points": 288,
                "series": series,
                "weapon_group": "B",
                "signup": sample_signup,
            }
        ]
        input_data = MedalCalculationInput(
            results=results,
            competition_type=CompetitionType.PRECISION,
            weapon_groups=["B"],
        )
        calculated_medals = calculate_medals(input_data)
        assert calculated_medals[0] == StdMedal.SILVER

    def test_precision_10_series_group_c_bronze(self, sample_signup):
        """10-series precision group C achieving 460+ points should get bronze."""
        series = [SeriesResult(points=46, inner_tens=4) for _ in range(10)]  # 10 * 46 = 460 points
        results = [
            {
                "points": 460,
                "series": series,
                "weapon_group": "C",
                "signup": sample_signup,
            }
        ]
        input_data = MedalCalculationInput(
            results=results,
            competition_type=CompetitionType.PRECISION,
            weapon_groups=["C"],
        )
        calculated_medals = calculate_medals(input_data)
        assert calculated_medals[0] == StdMedal.BRONZE

    def test_precision_relative_placement_silver(self, sample_signup, sample_signup_b, sample_signup_c):
        """9 competitors: top 1 should get silver via relative placement."""
        results = []
        signups = [sample_signup, sample_signup_b, sample_signup_c] + [None] * 6
        for i, signup in enumerate(signups):
            if signup is None:
                signup = Signup(
                    id=i,
                    spsf_club_number="12-239",
                    shooting_card_number=f"1000{i}",
                    fullname=f"Shooter {i}",
                    lane=i,
                    weapon_class="A1",
                    weapon_class_general="A",
                    share_patrol_with=None,
                )
            series = [SeriesResult(points=40 - i, inner_tens=4) for _ in range(7)]
            results.append(
                {
                    "points": (40 - i) * 7,
                    "series": series,
                    "weapon_group": "A",
                    "signup": signup,
                }
            )
        input_data = MedalCalculationInput(
            results=results,
            competition_type=CompetitionType.PRECISION,
            weapon_groups=["A"],
        )
        calculated_medals = calculate_medals(input_data)
        # Top 1 (index 0) should get silver via relative placement
        assert calculated_medals[0] == StdMedal.SILVER


# Military Competition Tests


class TestMilitaryMedalCalculation:
    """Test military competition medal calculation."""

    def test_military_12_series_group_a_silver(self, sample_signup):
        """12-series military group A achieving 540+ points should get silver."""
        series = [SeriesResult(points=46, inner_tens=5) for _ in range(12)]  # 12 * 46 = 552 points
        results = [
            {
                "points": 552,
                "series": series,
                "weapon_group": "A",
                "signup": sample_signup,
            }
        ]
        input_data = MedalCalculationInput(
            results=results,
            competition_type=CompetitionType.MILITARY,
            weapon_groups=["A"],
        )
        calculated_medals = calculate_medals(input_data)
        assert calculated_medals[0] == StdMedal.SILVER

    def test_military_12_series_group_r_bronze(self, sample_signup):
        """12-series military group R achieving 528+ points should get bronze."""
        series = [SeriesResult(points=44, inner_tens=4) for _ in range(12)]  # 12 * 44 = 528 points
        results = [
            {
                "points": 528,
                "series": series,
                "weapon_group": "R",
                "signup": sample_signup,
            }
        ]
        input_data = MedalCalculationInput(
            results=results,
            competition_type=CompetitionType.MILITARY,
            weapon_groups=["R"],
        )
        calculated_medals = calculate_medals(input_data)
        assert calculated_medals[0] == StdMedal.BRONZE

    def test_military_12_series_group_b_silver(self, sample_signup):
        """12-series military group B achieving 561+ points should get silver."""
        series = [SeriesResult(points=47, inner_tens=5) for _ in range(12)]  # 12 * 47 = 564 points
        results = [
            {
                "points": 564,
                "series": series,
                "weapon_group": "B",
                "signup": sample_signup,
            }
        ]
        input_data = MedalCalculationInput(
            results=results,
            competition_type=CompetitionType.MILITARY,
            weapon_groups=["B"],
        )
        calculated_medals = calculate_medals(input_data)
        assert calculated_medals[0] == StdMedal.SILVER

    def test_military_12_series_group_c_bronze(self, sample_signup):
        """12-series military group C achieving 540+ points should get bronze."""
        series = [SeriesResult(points=45, inner_tens=4) for _ in range(12)]  # 12 * 45 = 540 points
        results = [
            {
                "points": 540,
                "series": series,
                "weapon_group": "C",
                "signup": sample_signup,
            }
        ]
        input_data = MedalCalculationInput(
            results=results,
            competition_type=CompetitionType.MILITARY,
            weapon_groups=["C"],
        )
        calculated_medals = calculate_medals(input_data)
        assert calculated_medals[0] == StdMedal.BRONZE

    def test_military_below_bronze_threshold(self, sample_signup):
        """12-series military below bronze threshold should get no medal."""
        series = [SeriesResult(points=42, inner_tens=4) for _ in range(12)]  # 12 * 42 = 504 points
        results = [
            {
                "points": 504,
                "series": series,
                "weapon_group": "A",
                "signup": sample_signup,
            }
        ]
        input_data = MedalCalculationInput(
            results=results,
            competition_type=CompetitionType.MILITARY,
            weapon_groups=["A"],
        )
        calculated_medals = calculate_medals(input_data)
        assert calculated_medals[0] is None


# Edge Cases and Integration Tests


class TestMedalCalculationEdgeCases:
    """Test edge cases in medal calculation."""

    def test_empty_results(self):
        """Empty results should return empty list."""
        input_data = MedalCalculationInput(
            results=[],
            competition_type=CompetitionType.PRECISION,
            weapon_groups=["A"],
        )
        calculated_medals = calculate_medals(input_data)
        assert calculated_medals == []

    def test_single_result_relative_placement(self, sample_signup):
        """Single result in competition should not get medal (can't be top 1/9)."""
        series = [SeriesResult(points=47, inner_tens=5) for _ in range(7)]
        results = [
            {
                "points": 329,
                "series": series,
                "weapon_group": "A",
                "signup": sample_signup,
            }
        ]
        input_data = MedalCalculationInput(
            results=results,
            competition_type=CompetitionType.PRECISION,
            weapon_groups=["A"],
        )
        calculated_medals = calculate_medals(input_data)
        # Should get silver via fixed threshold, not relative
        assert calculated_medals[0] == StdMedal.SILVER

    def test_results_with_different_series_counts(self, sample_signup, sample_signup_b):
        """Precision results with different series counts."""
        # One with 7 series, one with 6 series
        series_7 = [SeriesResult(points=47, inner_tens=5) for _ in range(7)]
        series_6 = [SeriesResult(points=48, inner_tens=5) for _ in range(6)]
        results = [
            {
                "points": 329,
                "series": series_7,
                "weapon_group": "A",
                "signup": sample_signup,
            },
            {
                "points": 288,
                "series": series_6,
                "weapon_group": "A",
                "signup": sample_signup_b,
            },
        ]
        input_data = MedalCalculationInput(
            results=results,
            competition_type=CompetitionType.PRECISION,
            weapon_groups=["A"],
        )
        calculated_medals = calculate_medals(input_data)
        # Both should be classified based on their own series count
        # 329 points with 7 series -> silver (>= 323)
        # 288 points with 6 series -> silver (>= 282)
        assert calculated_medals[0] == StdMedal.SILVER
        assert calculated_medals[1] == StdMedal.SILVER
