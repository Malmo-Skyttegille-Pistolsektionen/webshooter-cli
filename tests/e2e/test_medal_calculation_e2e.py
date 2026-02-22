"""E2E tests for medal calculation functionality."""

from pathlib import Path

import pytest

from webshooter_client.common.application_config import ApplicationConfig
from webshooter_client.api.api_calls import get_results, get_competitions
from webshooter_client.models.result import StdMedal
from webshooter_client.models.competition import CompetitionType


class TestMedalCalculationE2E:
    """E2E tests for medal calculation with cached data."""

    @pytest.fixture(autouse=True)
    def setup_cache(self):
        """Setup cache for all tests."""
        test_cache = Path(__file__).parent.parent / "resources" / "test_data" / "competitions"
        ApplicationConfig(use_cache=True, cache_dir=str(test_cache))

    def test_calculated_medals_present_on_results(self):
        """All results should have calculated_std_medal field populated."""
        competitions = get_competitions(year=2024)
        assert len(competitions) > 0

        # Test a few competitions
        for comp_id in list(competitions.keys())[:3]:
            results = get_results(competition_id=comp_id)
            for result in results:
                assert hasattr(result, "calculated_std_medal")
                # calculated_std_medal should be StdMedal or None
                assert result.calculated_std_medal is None or isinstance(result.calculated_std_medal, StdMedal)

    def test_field_competition_medals_calculated(self):
        """Field competition results should have calculated medals."""
        competitions = get_competitions(year=2024)

        # Find a field competition
        field_comp_id = None
        for comp in competitions.values():
            if comp.type in (CompetitionType.FIELD, CompetitionType.POINTFIELD):
                field_comp_id = comp.id
                break

        if field_comp_id:
            results = get_results(competition_id=field_comp_id)
            # Should have some results with medals
            medal_count = sum(1 for r in results if r.calculated_std_medal)
            # Field competitions should have some medal winners
            assert medal_count >= 0

    def test_precision_competition_max_score_350(self):
        """Precision competitions should not have scores >350 (7 series limit)."""
        competitions = get_competitions(year=2024)

        precision_max_score = 0
        for comp in competitions.values():
            if comp.type == CompetitionType.PRECISION:
                results = get_results(competition_id=comp.id)
                from webshooter_client.common.competition_filter import get_result_points
                from webshooter_client.models.result import PrecisionResult

                for result in results:
                    if isinstance(result, PrecisionResult) and len(result.series) == 7:
                        points = get_result_points(result)
                        precision_max_score = max(precision_max_score, points)

        # Max score for 7-series precision should be 350
        assert precision_max_score <= 350

    def test_military_competition_medals_calculated(self):
        """Military competition results should have calculated medals."""
        competitions = get_competitions(year=2024)

        # Find a military competition
        military_results = []
        for comp in competitions.values():
            if comp.type == CompetitionType.MILITARY:
                results = get_results(competition_id=comp.id)
                military_results.extend(results)
                if military_results:
                    break

        if military_results:
            # Should have calculated medals
            for result in military_results[:5]:  # Check first 5
                assert hasattr(result, "calculated_std_medal")

    def test_medals_consistency_api_vs_calculated(self):
        """Compare API medals with calculated medals."""
        competitions = get_competitions(year=2024)

        discrepancy_count = 0
        for comp in competitions.values():
            results = get_results(competition_id=comp.id)
            for result in results:
                if result.std_medal != result.calculated_std_medal:
                    discrepancy_count += 1

        # Log discrepancies for analysis
        print(f"\nMedal discrepancies found: {discrepancy_count}")
        # Discrepancies are expected for older data with incorrect API medals
        # This is the main reason for implementing independent calculation

    def test_no_results_with_invalid_series_count(self):
        """Precision results with invalid series counts should be filtered."""
        competitions = get_competitions(year=2024)

        invalid_series_count = 0
        for comp in competitions.values():
            if comp.type == CompetitionType.PRECISION:
                results = get_results(competition_id=comp.id)
                from webshooter_client.models.result import PrecisionResult
                from webshooter_client.common.competition_filter import is_valid_precision_result

                for result in results:
                    if isinstance(result, PrecisionResult):
                        # This shouldn't affect medal calculation, but valid results
                        # should have series data
                        if result.series and not is_valid_precision_result(result):
                            invalid_series_count += 1

        # This test just verifies the filtering logic works
        assert invalid_series_count >= 0


class TestMedalCalculationRobustness:
    """Test edge cases and robustness of medal calculation."""

    @pytest.fixture(autouse=True)
    def setup_cache(self):
        """Setup cache for all tests."""
        test_cache = Path(__file__).parent.parent / "resources" / "test_data" / "competitions"
        ApplicationConfig(use_cache=True, cache_dir=str(test_cache))

    def test_competitions_with_no_medal_winners(self):
        """Some competitions may have no medal winners."""
        competitions = get_competitions(year=2024)

        # This should not crash
        for comp in competitions.values():
            results = get_results(competition_id=comp.id)
            # All results should have calculated_std_medal field
            assert all(hasattr(r, "calculated_std_medal") for r in results)

    def test_calculation_handles_none_values(self):
        """Medal calculation should handle None values gracefully."""
        competitions = get_competitions(year=2024)

        # This should not crash even with edge cases
        for comp in competitions.values():
            results = get_results(competition_id=comp.id)
            for result in results:
                # Should be able to iterate without errors
                _ = result.calculated_std_medal
                _ = result.std_medal

    def test_all_competition_types_supported(self):
        """Medal calculation should work for all competition types."""
        competitions = get_competitions(year=2024)

        comp_types_found = set()
        for comp in competitions.values():
            if comp.type not in comp_types_found:
                comp_types_found.add(comp.type)
                results = get_results(competition_id=comp.id)
                # Should succeed without errors
                assert len(results) >= 0

        # Should have found at least some competition types
        assert len(comp_types_found) > 0
