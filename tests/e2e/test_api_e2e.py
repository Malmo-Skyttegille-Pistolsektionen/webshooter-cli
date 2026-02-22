"""Integration tests using real API response data.

These tests use actual API responses stored in tests/resources/ to verify:
- Correct parsing of competition data
- Correct parsing of results (Military, Precision, Field)
- Correct signup parsing
- Proper error handling with malformed data
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from webshooter_client.api.api_calls import get_competition, get_results, get_signups, create_signup_obj
from webshooter_client.api.exceptions import DataValidationError
from webshooter_client.models.competition import CompetitionType
from webshooter_client.models.result import MilitaryResult, PrecisionResult, FieldResult


@pytest.fixture
def test_data_dir():
    """Get the test data directory."""
    return Path(__file__).parent.parent / "resources" / "test_data" / "competitions"


@pytest.fixture
def load_test_data(test_data_dir):
    """Load test data from JSON files - flat structure like cache."""

    def _load(comp_id, filename):
        # Test data uses flat structure (like cache): competitions/competition_149.json
        file_path = test_data_dir / filename
        with open(file_path, "r") as f:
            return json.load(f)

    return _load


class TestCompetitionParsing:
    """Test competition parsing with real API data."""

    def test_parse_military_competition(self, load_test_data):
        """Parse Military competition from real API response."""
        data = load_test_data(149, "competition_149.json")

        with patch("webshooter_client.api.api_calls.fetch_data", return_value=data):
            competition = get_competition(149)

        assert competition.id == 149
        assert competition.name == "Pistol-SM 2024, Militär Snabbmatch (B, C, J), Tisdag 240702"
        assert competition.type == CompetitionType.MILITARY
        assert competition.city == "Malmö"
        assert competition.venue == "Bödkaregårdens Skjutbana"
        assert str(competition.competition_date) == "2024-07-02"

    def test_parse_precision_competition(self, load_test_data):
        """Parse Precision competition from real API response."""
        data = load_test_data(152, "competition_152.json")

        with patch("webshooter_client.api.api_calls.fetch_data", return_value=data):
            competition = get_competition(152)

        assert competition.id == 152
        assert competition.type == CompetitionType.PRECISION
        assert competition.city == "Malmö"

    def test_parse_field_competition(self, load_test_data):
        """Parse Field competition from real API response."""
        data = load_test_data(157, "competition_157.json")

        with patch("webshooter_client.api.api_calls.fetch_data", return_value=data):
            competition = get_competition(157)

        assert competition.id == 157
        assert competition.type == CompetitionType.FIELD

    def test_missing_required_fields_raises_error(self):
        """Missing required fields raises DataValidationError."""
        # Missing 'name' field
        data = {"competitions": {"id": 999, "date": "2024-01-01", "results_type": "field"}}

        with patch("webshooter_client.api.api_calls.fetch_data", return_value=data):
            with pytest.raises(DataValidationError) as exc_info:
                get_competition(999)
            assert "name" in str(exc_info.value)

    def test_empty_competition_data_raises_error(self):
        """Empty competitions field raises DataValidationError."""
        data = {"competitions": None}

        with patch("webshooter_client.api.api_calls.fetch_data", return_value=data):
            with pytest.raises(DataValidationError) as exc_info:
                get_competition(999)
            assert "No competition data" in str(exc_info.value)


class TestResultParsing:
    """Test result parsing with real API data."""

    def test_parse_military_results(self, load_test_data):
        """Parse Military results from real API response."""
        comp_data = load_test_data(149, "competition_149.json")
        results_data = load_test_data(149, "competition_149_results.json")

        with patch("webshooter_client.api.api_calls.fetch_data") as mock_fetch:
            # First call: get_competition(), second call: results URL
            mock_fetch.side_effect = [comp_data, results_data]
            results = get_results(149)

        assert len(results) > 0
        assert all(isinstance(r, MilitaryResult) for r in results)

        # Check first result has expected fields
        first_result = results[0]
        assert hasattr(first_result, "placement")
        assert hasattr(first_result, "points")
        assert hasattr(first_result, "series")
        assert hasattr(first_result, "signup")

    def test_parse_precision_results(self, load_test_data):
        """Parse Precision results from real API response."""
        comp_data = load_test_data(152, "competition_152.json")
        results_data = load_test_data(152, "competition_152_results.json")

        with patch("webshooter_client.api.api_calls.fetch_data") as mock_fetch:
            mock_fetch.side_effect = [comp_data, results_data]
            results = get_results(152)

        assert len(results) > 0
        assert all(isinstance(r, PrecisionResult) for r in results)

    def test_parse_field_results(self, load_test_data):
        """Parse Field results from real API response."""
        comp_data = load_test_data(157, "competition_157.json")
        results_data = load_test_data(157, "competition_157_results.json")

        with patch("webshooter_client.api.api_calls.fetch_data") as mock_fetch:
            mock_fetch.side_effect = [comp_data, results_data]
            results = get_results(157)

        assert len(results) > 0
        assert all(isinstance(r, FieldResult) for r in results)

        # Field results should have stations
        first_result = results[0]
        assert hasattr(first_result, "stations")

    def test_results_have_correct_signup_data(self, load_test_data):
        """Results are correctly linked to signup data."""
        comp_data = load_test_data(149, "competition_149.json")
        results_data = load_test_data(149, "competition_149_results.json")

        with patch("webshooter_client.api.api_calls.fetch_data") as mock_fetch:
            mock_fetch.side_effect = [comp_data, results_data]
            results = get_results(149)

        # Each result should have a signup with required fields
        for result in results[:5]:  # Check first 5
            assert result.signup is not None
            assert hasattr(result.signup, "fullname")
            assert hasattr(result.signup, "weapon_class")
            assert hasattr(result.signup, "spsf_club_number")


class TestSignupParsing:
    """Test signup parsing with real API data."""

    def test_parse_signups(self, load_test_data):
        """Parse signups from real API response."""
        signups_data = load_test_data(12, "competition_12_signups.json")

        with patch("webshooter_client.api.api_calls.fetch_data", return_value=signups_data):
            signups = get_signups(149)

        assert len(signups) > 0

        # Check signups have required fields
        first_signup = signups[0]
        assert hasattr(first_signup, "id")
        assert hasattr(first_signup, "fullname")
        assert hasattr(first_signup, "weapon_class")
        assert hasattr(first_signup, "spsf_club_number")
        assert hasattr(first_signup, "shooting_card_number")

    def test_signup_with_missing_club_raises_error(self):
        """Signup missing club data raises DataValidationError."""
        invalid_signup = {
            "id": 123,
            "club": {},  # Missing districts_id and clubs_nr
            "user": {"fullname": "Test Person"},
            "weaponclass": {"classname": "A", "classname_general": "A"},
            "lane": 1,
            "share_patrol_with": None,
        }

        with pytest.raises(DataValidationError) as exc_info:
            create_signup_obj(invalid_signup)
        assert "club identification" in str(exc_info.value).lower()

    def test_signup_with_missing_user_raises_error(self):
        """Signup missing user data raises DataValidationError."""
        invalid_signup = {
            "id": 123,
            "club": {"districts_id": "12", "clubs_nr": "345"},
            "user": {},  # Missing fullname
            "weaponclass": {"classname": "A", "classname_general": "A"},
            "lane": 1,
            "share_patrol_with": None,
        }

        with pytest.raises(DataValidationError) as exc_info:
            create_signup_obj(invalid_signup)
        assert "fullname" in str(exc_info.value).lower()

    def test_signup_with_missing_weaponclass_raises_error(self):
        """Signup missing weapon class raises DataValidationError."""
        invalid_signup = {
            "id": 123,
            "club": {"districts_id": "12", "clubs_nr": "345"},
            "user": {"fullname": "Test Person"},
            "weaponclass": {},  # Missing classname
            "lane": 1,
            "share_patrol_with": None,
        }

        with pytest.raises(DataValidationError) as exc_info:
            create_signup_obj(invalid_signup)
        assert "weapon class" in str(exc_info.value).lower()


class TestErrorHandling:
    """Test error handling with edge cases."""

    def test_empty_results_list(self, load_test_data):
        """Handle competition with no results gracefully."""
        comp_data = load_test_data(149, "competition_149.json")
        empty_results = {"results": []}

        with patch("webshooter_client.api.api_calls.fetch_data") as mock_fetch:
            mock_fetch.side_effect = [comp_data, empty_results]
            results = get_results(149)

        assert results == []

    def test_empty_signups_list(self):
        """Handle competition with no signups gracefully."""
        empty_signups = {"signups": {"data": []}}

        with patch("webshooter_client.api.api_calls.fetch_data", return_value=empty_signups):
            signups = get_signups(999)

        assert signups == []

    def test_result_missing_placement_raises_error(self, load_test_data):
        """Result missing placement field raises DataValidationError."""
        comp_data = load_test_data(149, "competition_149.json")

        # Load real results data and modify first result to have missing placement
        results_data = load_test_data(149, "competition_149_results.json")
        if results_data["results"]:
            # Remove placement from first result
            del results_data["results"][0]["placement"]

        with patch("webshooter_client.api.api_calls.fetch_data") as mock_fetch:
            mock_fetch.side_effect = [comp_data, results_data]
            with pytest.raises(DataValidationError) as exc_info:
                get_results(149)
            assert "placement" in str(exc_info.value).lower()
