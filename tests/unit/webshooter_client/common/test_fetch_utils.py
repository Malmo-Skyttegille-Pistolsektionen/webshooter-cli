"""Unit tests for fetch_utils module."""

from unittest.mock import patch
from webshooter_client.common.fetch_utils import fetch_field_competition_results
from webshooter_client.models.result import FieldResult, StationResult
from webshooter_client.models.signup import Signup
from webshooter_client.models.result import StdMedal
from webshooter_client.models.competition import Competition, CompetitionType
from datetime import date


class TestFetchFieldCompetitionResultsMultipleWeaponClasses:
    """Test that fetch_field_competition_results handles multiple weapon classes."""

    def test_collects_all_weapon_classes_for_same_card_in_competition(self):
        """Test that all weapon classes for a card in one competition are collected."""
        # Setup: Create two FieldResults for same card but different weapon classes
        signup_c3 = Signup(
            id=1,
            spsf_club_number="12-239",
            shooting_card_number="53780",
            fullname="Test Shooter",
            lane=1,
            weapon_class="C3",
            weapon_class_general="C",
            share_patrol_with=None,
        )
        signup_a3 = Signup(
            id=2,
            spsf_club_number="12-239",
            shooting_card_number="53780",
            fullname="Test Shooter",
            lane=2,
            weapon_class="A3",
            weapon_class_general="A",
            share_patrol_with=None,
        )

        signup_medal = Signup(
            id=3,
            spsf_club_number="12-239",
            shooting_card_number="99999",
            fullname="Medal Winner",
            lane=3,
            weapon_class="C3",
            weapon_class_general="C",
            share_patrol_with=None,
        )

        c3_result = FieldResult(
            signup=signup_c3,
            placement=15,
            std_medal=StdMedal.BRONZE,
            points=0,
            stations=[StationResult(hits=5, figure_hits=3) for _ in range(8)],
        )

        a3_result = FieldResult(
            signup=signup_a3,
            placement=2,
            std_medal=StdMedal.SILVER,
            points=0,
            stations=[StationResult(hits=6, figure_hits=4) for _ in range(8)],
        )

        medal_result = FieldResult(
            signup=signup_medal,
            placement=1,
            std_medal=StdMedal.BRONZE,
            points=0,
            stations=[StationResult(hits=6, figure_hits=4) for _ in range(8)],
        )

        competition = Competition(
            id=288,
            name="Test Field Competition",
            type=CompetitionType.FIELD,
            competition_date=date(2026, 1, 18),
            signups_close=date(2026, 1, 10),
            venue="Test Venue",
            city="Test City",
        )

        # Mock the API calls
        with (
            patch(
                "webshooter_client.common.fetch_utils.get_competitions",
                return_value={288: competition},
            ),
            patch(
                "webshooter_client.common.fetch_utils.get_results",
                return_value=[c3_result, a3_result, medal_result],
            ),
        ):
            results = fetch_field_competition_results([2026], "53780", show_progress=False)

        # Verify both weapon classes are collected
        assert 2026 in results
        assert len(results[2026]) == 2  # Should have 2 tuples (one per weapon class)

        # Extract the results
        weapon_classes = []
        for my_result, medal_results in results[2026]:
            weapon_classes.append(my_result.signup.weapon_class)

        # Verify both C3 and A3 are present
        assert "C3" in weapon_classes
        assert "A3" in weapon_classes

        # Verify placements are correct
        placements = {my_result.signup.weapon_class: my_result.placement for my_result, _ in results[2026]}
        assert placements["C3"] == 15
        assert placements["A3"] == 2

    def test_single_weapon_class_still_works(self):
        """Test that single weapon class per card still works after refactoring."""
        signup = Signup(
            id=1,
            spsf_club_number="12-239",
            shooting_card_number="53780",
            fullname="Test Shooter",
            lane=1,
            weapon_class="C3",
            weapon_class_general="C",
            share_patrol_with=None,
        )

        signup_medal = Signup(
            id=2,
            spsf_club_number="12-239",
            shooting_card_number="99999",
            fullname="Medal Winner",
            lane=2,
            weapon_class="C3",
            weapon_class_general="C",
            share_patrol_with=None,
        )

        my_result = FieldResult(
            signup=signup,
            placement=5,
            std_medal=StdMedal.BRONZE,
            points=0,
            stations=[StationResult(hits=5, figure_hits=3) for _ in range(8)],
        )

        medal_result = FieldResult(
            signup=signup_medal,
            placement=1,
            std_medal=StdMedal.BRONZE,
            points=0,
            stations=[StationResult(hits=6, figure_hits=4) for _ in range(8)],
        )

        competition = Competition(
            id=100,
            name="Single Class Field Competition",
            type=CompetitionType.FIELD,
            competition_date=date(2026, 1, 15),
            signups_close=date(2026, 1, 10),
            venue="Test Venue",
            city="Test City",
        )

        with (
            patch(
                "webshooter_client.common.fetch_utils.get_competitions",
                return_value={100: competition},
            ),
            patch(
                "webshooter_client.common.fetch_utils.get_results",
                return_value=[my_result, medal_result],
            ),
        ):
            results = fetch_field_competition_results([2026], "53780", show_progress=False)

        # Should return exactly 1 result tuple
        assert 2026 in results
        assert len(results[2026]) == 1
        assert results[2026][0][0].placement == 5
