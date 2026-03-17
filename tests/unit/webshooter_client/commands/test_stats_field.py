"""Unit tests for Field competition stats functionality."""

from unittest.mock import patch
from webshooter_client.commands.stats import get_single_field_competition_analysis
from webshooter_client.models.result import FieldResult, StationResult
from webshooter_client.models.signup import Signup
from webshooter_client.models.result import StdMedal
from webshooter_client.models.competition import Competition, CompetitionType
from datetime import date


class TestSingleFieldCompetitionMultipleWeaponClasses:
    """Test that single competition analysis handles multiple weapon classes."""

    def test_multiple_weapon_classes_shown_separately(self, capsys):
        """Test that results for multiple weapon classes are shown in separate tables."""
        # Setup: Create two FieldResults for same card but different weapon classes
        signup_c3 = Signup(
            id=1,
            spsf_club_number="12-239",
            shooting_card_number="10000",
            fullname="Test Shooter",
            lane=1,
            weapon_class="C3",
            weapon_class_general="C",
            share_patrol_with=None,
        )
        signup_a3 = Signup(
            id=2,
            spsf_club_number="12-239",
            shooting_card_number="10000",
            fullname="Test Shooter",
            lane=2,
            weapon_class="A3",
            weapon_class_general="A",
            share_patrol_with=None,
        )

        # Create medal winner result
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
            calculated_std_medal=StdMedal.BRONZE,
            stations=[
                StationResult(hits=5, figure_hits=3),
                StationResult(hits=5, figure_hits=2),
                StationResult(hits=5, figure_hits=3),
                StationResult(hits=5, figure_hits=3),
                StationResult(hits=5, figure_hits=3),
                StationResult(hits=6, figure_hits=4),
                StationResult(hits=5, figure_hits=2),
                StationResult(hits=6, figure_hits=2),
            ],
        )

        a3_result = FieldResult(
            signup=signup_a3,
            placement=2,
            std_medal=StdMedal.SILVER,
            points=0,
            calculated_std_medal=StdMedal.SILVER,
            stations=[
                StationResult(hits=6, figure_hits=4),
                StationResult(hits=5, figure_hits=3),
                StationResult(hits=5, figure_hits=3),
                StationResult(hits=6, figure_hits=4),
                StationResult(hits=5, figure_hits=3),
                StationResult(hits=5, figure_hits=3),
                StationResult(hits=5, figure_hits=2),
                StationResult(hits=5, figure_hits=2),
            ],
        )

        medal_result = FieldResult(
            signup=signup_medal,
            placement=1,
            std_medal=StdMedal.BRONZE,
            points=0,
            calculated_std_medal=StdMedal.BRONZE,
            stations=[
                StationResult(hits=6, figure_hits=4),
                StationResult(hits=5, figure_hits=3),
                StationResult(hits=5, figure_hits=3),
                StationResult(hits=6, figure_hits=4),
                StationResult(hits=5, figure_hits=3),
                StationResult(hits=6, figure_hits=4),
                StationResult(hits=6, figure_hits=4),
                StationResult(hits=6, figure_hits=4),
            ],
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
            patch("webshooter_client.commands.stats.get_competition", return_value=competition),
            patch(
                "webshooter_client.commands.stats.get_results",
                return_value=[c3_result, a3_result, medal_result],
            ),
        ):
            get_single_field_competition_analysis(competition_id=288, card="10000")

        captured = capsys.readouterr()
        output = captured.out

        # Should show both weapon classes
        assert "Weapon Class: C3" in output
        assert "Weapon Class: A3" in output

        # Should show both medals
        assert "Medal: Brons" in output
        assert "Medal: Silver" in output

        # Should show two separate Your Result lines with correct placement
        assert "Placement: 15" in output  # C3
        assert "Placement: 2" in output  # A3

        # Should have two tables (one per weapon class)
        assert output.count("Comp ID") >= 2

    def test_single_weapon_class_still_works(self, capsys):
        """Test that single weapon class still works after refactoring."""
        signup = Signup(
            id=1,
            spsf_club_number="12-239",
            shooting_card_number="10000",
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
            calculated_std_medal=StdMedal.BRONZE,
            stations=[
                StationResult(hits=5, figure_hits=3),
                StationResult(hits=5, figure_hits=2),
                StationResult(hits=5, figure_hits=3),
                StationResult(hits=5, figure_hits=3),
                StationResult(hits=5, figure_hits=3),
                StationResult(hits=6, figure_hits=4),
                StationResult(hits=5, figure_hits=2),
                StationResult(hits=6, figure_hits=2),
            ],
        )

        medal_result = FieldResult(
            signup=signup_medal,
            placement=1,
            std_medal=StdMedal.BRONZE,
            points=0,
            calculated_std_medal=StdMedal.BRONZE,
            stations=[
                StationResult(hits=6, figure_hits=4),
                StationResult(hits=5, figure_hits=3),
                StationResult(hits=5, figure_hits=3),
                StationResult(hits=6, figure_hits=4),
                StationResult(hits=5, figure_hits=3),
                StationResult(hits=6, figure_hits=4),
                StationResult(hits=6, figure_hits=4),
                StationResult(hits=6, figure_hits=4),
            ],
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
            patch("webshooter_client.commands.stats.get_competition", return_value=competition),
            patch("webshooter_client.commands.stats.get_results", return_value=[my_result, medal_result]),
        ):
            get_single_field_competition_analysis(competition_id=100, card="10000")

        captured = capsys.readouterr()
        output = captured.out

        # Should show single weapon class
        assert "Weapon Class: C3" in output
        assert "Your Result:" in output
        assert "Placement: 5" in output
