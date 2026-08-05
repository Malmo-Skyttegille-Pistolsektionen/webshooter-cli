"""Tests for webshooter_client.sync.syncer."""

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from webshooter_client.api.exceptions import WebShooterAPIError
from webshooter_client.common.application_config import ApplicationConfig
from webshooter_client.models.competition import Competition, CompetitionType
from webshooter_client.models.result import PrecisionResult, SeriesResult
from webshooter_client.models.signup import Signup
from webshooter_client.sync.syncer import (
    _my_weapon_classes,
    _select_candidates,
    _watermark,
    sync_competitions,
)

TODAY = date(2026, 8, 5)


@pytest.fixture
def reset_config():
    """Reset the ApplicationConfig singleton between tests."""
    ApplicationConfig._instances = {}
    yield
    ApplicationConfig._instances = {}


@pytest.fixture
def app_config(reset_config, tmp_path):
    """A config pointed at a throwaway cache dir, never the real one."""
    return ApplicationConfig(use_cache=True, cache_dir=str(tmp_path), token="test-token")


def make_competition(comp_id, comp_date, comp_type=CompetitionType.PRECISION):
    return Competition(
        id=comp_id,
        name=f"Competition {comp_id}",
        competition_date=comp_date,
        signups_close=comp_date,
        city="Testcity",
        venue="Testvenue",
        type=comp_type,
    )


def make_signup(card="CARD1", weapon_class="C3"):
    return Signup(
        id=1,
        spsf_club_number="1-2",
        shooting_card_number=card,
        fullname="Test Testsson",
        lane=1,
        weapon_class=weapon_class,
        weapon_class_general=weapon_class[0],
        share_patrol_with=None,
    )


def make_precision_result(card, weapon_class, series_points, placement=1):
    series = [SeriesResult(points=p, inner_tens=0) for p in series_points]
    return PrecisionResult(
        signup=make_signup(card, weapon_class),
        placement=placement,
        std_medal=None,
        points=sum(series_points),
        series=series,
    )


class TestWatermark:
    """Tests for _watermark."""

    def test_ignores_future_dated_cached_competitions(self):
        """A cached future-dated competition must not push the watermark forward.

        This was an actual bug: a cached but not-yet-shot competition (an empty
        results file) pushed the watermark past everything else and made sync a
        permanent no-op.
        """
        past = make_competition(1, TODAY - timedelta(days=10))
        future = make_competition(2, TODAY + timedelta(days=10))
        competitions = {1: past, 2: future}

        with patch("webshooter_client.sync.syncer.list_cached_competition_ids", return_value={1, 2}):
            watermark = _watermark(competitions, until=TODAY)

        assert watermark == past.competition_date

    def test_returns_none_when_nothing_cached_or_all_future(self):
        future = make_competition(1, TODAY + timedelta(days=1))
        competitions = {1: future}

        with patch("webshooter_client.sync.syncer.list_cached_competition_ids", return_value={1}):
            watermark = _watermark(competitions, until=TODAY)

        assert watermark is None

    def test_returns_most_recent_cached_date(self):
        early = make_competition(1, TODAY - timedelta(days=20))
        late = make_competition(2, TODAY - timedelta(days=5))
        competitions = {1: early, 2: late}

        with patch("webshooter_client.sync.syncer.list_cached_competition_ids", return_value={1, 2}):
            watermark = _watermark(competitions, until=TODAY)

        assert watermark == late.competition_date


class TestSelectCandidates:
    """Tests for _select_candidates."""

    def test_excludes_future_competitions(self):
        past = make_competition(1, TODAY - timedelta(days=1))
        future = make_competition(2, TODAY + timedelta(days=1))
        competitions = {1: past, 2: future}

        with patch("webshooter_client.sync.syncer.list_cached_competition_ids", return_value=set()):
            candidates = _select_candidates(competitions, floor=None, until=TODAY)

        assert [c.id for c in candidates] == [1]

    def test_excludes_already_cached_competitions(self):
        cached = make_competition(1, TODAY - timedelta(days=1))
        not_cached = make_competition(2, TODAY - timedelta(days=1))
        competitions = {1: cached, 2: not_cached}

        with patch("webshooter_client.sync.syncer.list_cached_competition_ids", return_value={1}):
            candidates = _select_candidates(competitions, floor=None, until=TODAY)

        assert [c.id for c in candidates] == [2]

    def test_includes_competitions_on_exact_watermark_date(self):
        """Same-day siblings of the watermark competition must not be skipped."""
        watermark_date = TODAY - timedelta(days=3)
        sibling = make_competition(1, watermark_date)
        earlier = make_competition(2, watermark_date - timedelta(days=1))
        competitions = {1: sibling, 2: earlier}

        with patch("webshooter_client.sync.syncer.list_cached_competition_ids", return_value=set()):
            candidates = _select_candidates(competitions, floor=watermark_date, until=TODAY)

        assert [c.id for c in candidates] == [1]

    def test_respects_explicit_floor(self):
        before_floor = make_competition(1, TODAY - timedelta(days=10))
        on_floor = make_competition(2, TODAY - timedelta(days=5))
        after_floor = make_competition(3, TODAY - timedelta(days=1))
        competitions = {1: before_floor, 2: on_floor, 3: after_floor}
        floor = TODAY - timedelta(days=5)

        with patch("webshooter_client.sync.syncer.list_cached_competition_ids", return_value=set()):
            candidates = _select_candidates(competitions, floor=floor, until=TODAY)

        assert [c.id for c in candidates] == [2, 3]

    def test_sorted_by_date_then_id(self):
        c1 = make_competition(5, TODAY - timedelta(days=1))
        c2 = make_competition(3, TODAY - timedelta(days=2))
        c3 = make_competition(4, TODAY - timedelta(days=2))
        competitions = {5: c1, 3: c2, 4: c3}

        with patch("webshooter_client.sync.syncer.list_cached_competition_ids", return_value=set()):
            candidates = _select_candidates(competitions, floor=None, until=TODAY)

        assert [c.id for c in candidates] == [3, 4, 5]


class TestMyWeaponClasses:
    def test_returns_empty_when_no_card_given(self):
        result = make_precision_result("CARD1", "C3", [50] * 7)
        assert _my_weapon_classes([result], None) == []

    def test_returns_classes_in_first_seen_order_deduplicated(self):
        results = [
            make_precision_result("CARD1", "C3", [50] * 7),
            make_precision_result("OTHER", "R1", [50] * 7),
            make_precision_result("CARD1", "C1", [50] * 7),
            make_precision_result("CARD1", "C3", [50] * 7),
        ]
        assert _my_weapon_classes(results, "CARD1") == ["C3", "C1"]


class TestSyncCompetitions:
    """Tests for sync_competitions."""

    def _competitions(self):
        return {
            1: make_competition(1, TODAY - timedelta(days=3)),
            2: make_competition(2, TODAY - timedelta(days=2)),
            3: make_competition(3, TODAY - timedelta(days=1)),
        }

    def test_dry_run_downloads_nothing_and_writes_no_index(self, app_config, tmp_path):
        competitions = self._competitions()

        with (
            patch("webshooter_client.sync.syncer.get_competitions", return_value=competitions) as mock_get_comps,
            patch("webshooter_client.sync.syncer.list_cached_competition_ids", return_value=set()),
            patch("webshooter_client.sync.syncer.get_results") as mock_get_results,
        ):
            report = sync_competitions(dry_run=True, show_progress=False)

        assert report.dry_run is True
        assert len(report.considered) == 3
        assert report.downloaded == []
        mock_get_results.assert_not_called()
        mock_get_comps.assert_called_once()
        assert not (tmp_path / "sync_index.json").exists()

    def test_limit_caps_the_run(self, app_config):
        competitions = self._competitions()

        with (
            patch("webshooter_client.sync.syncer.get_competitions", return_value=competitions),
            patch("webshooter_client.sync.syncer.list_cached_competition_ids", return_value=set()),
            patch("webshooter_client.sync.syncer.get_results", return_value=[]),
        ):
            report = sync_competitions(limit=2, show_progress=False)

        assert len(report.considered) == 2
        assert len(report.downloaded) == 2

    def test_failed_competition_lands_in_report_and_does_not_abort(self, app_config):
        competitions = self._competitions()

        def get_results_side_effect(competition_id):
            if competition_id == 2:
                raise WebShooterAPIError("results not published yet")
            return []

        with (
            patch("webshooter_client.sync.syncer.get_competitions", return_value=competitions),
            patch("webshooter_client.sync.syncer.list_cached_competition_ids", return_value=set()),
            patch("webshooter_client.sync.syncer.get_results", side_effect=get_results_side_effect),
        ):
            report = sync_competitions(show_progress=False)

        assert len(report.considered) == 3
        assert [c.id for c in report.downloaded] == [1, 3]
        assert len(report.failed) == 1
        assert report.failed[0]["id"] == 2

    def test_index_updated_with_my_weapon_classes_for_card(self, app_config, tmp_path):
        competitions = {1: make_competition(1, TODAY - timedelta(days=1))}
        results = [
            make_precision_result("CARD1", "C3", [50] * 7),
            make_precision_result("OTHER", "R1", [50] * 7),
        ]

        with (
            patch("webshooter_client.sync.syncer.get_competitions", return_value=competitions),
            patch("webshooter_client.sync.syncer.list_cached_competition_ids", return_value=set()),
            patch("webshooter_client.sync.syncer.get_results", return_value=results),
        ):
            report = sync_competitions(card="CARD1", show_progress=False)

        assert len(report.downloaded) == 1
        synced = report.downloaded[0]
        assert synced.my_weapon_classes == ["C3"]
        assert synced.has_my_results is True

        from webshooter_client.api.cache import load_index

        index = load_index()
        assert index["competitions"]["1"]["my_weapon_classes"] == ["C3"]
        assert index["card"] == "CARD1"
        assert "last_sync" in index

    def test_raises_when_offline(self, reset_config, tmp_path):
        ApplicationConfig(use_cache=True, cache_dir=str(tmp_path), offline=True)

        with patch("webshooter_client.sync.syncer.get_competitions") as mock_get_comps:
            with pytest.raises(WebShooterAPIError):
                sync_competitions(show_progress=False)

        mock_get_comps.assert_not_called()
