"""Tests for webshooter_client.services.local_query."""

from datetime import date
from unittest.mock import patch

import pytest

from webshooter_client.api.exceptions import WebShooterAPIError
from webshooter_client.models.competition import Competition, CompetitionType
from webshooter_client.models.result import PrecisionResult, SeriesResult
from webshooter_client.models.signup import Signup
from webshooter_client.services.local_query import (
    UnknownCompetitionTypeError,
    competition_results,
    my_results,
    personal_bests,
    resolve_competition_types,
)

MODULE = "webshooter_client.services.local_query"


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


class TestResolveCompetitionTypes:
    def test_none_or_empty_returns_none(self):
        assert resolve_competition_types(None) is None
        assert resolve_competition_types([]) is None

    def test_accepts_api_value(self):
        assert resolve_competition_types(["military"]) == {CompetitionType.MILITARY}

    def test_accepts_swedish_display_name(self):
        assert resolve_competition_types(["Militär snabbmatch"]) == {CompetitionType.MILITARY}

    def test_case_insensitive_for_both_forms(self):
        assert resolve_competition_types(["MILITARY"]) == {CompetitionType.MILITARY}
        assert resolve_competition_types(["militär SNABBMATCH"]) == {CompetitionType.MILITARY}

    def test_multiple_names_combine(self):
        result = resolve_competition_types(["military", "Fält"])
        assert result == {CompetitionType.MILITARY, CompetitionType.FIELD}

    def test_raises_on_unknown_type(self):
        with pytest.raises(UnknownCompetitionTypeError):
            resolve_competition_types(["not-a-real-type"])


class TestPersonalBests:
    def test_ranks_precision_by_points_then_inner_tens(self):
        results = [
            {"competition": {"type": "Precision"}, "weapon_class": "C3", "points": 340, "inner_tens": 5, "hits": None},
            {"competition": {"type": "Precision"}, "weapon_class": "C3", "points": 350, "inner_tens": 2, "hits": None},
            {"competition": {"type": "Precision"}, "weapon_class": "C3", "points": 350, "inner_tens": 8, "hits": None},
        ]

        with patch(f"{MODULE}.my_results", return_value=results) as mock_my_results:
            bests = personal_bests("CARD1")

        key = "Precision - C3"
        assert list(bests.keys()) == [key]
        assert [(r["points"], r["inner_tens"]) for r in bests[key]] == [(350, 8), (350, 2), (340, 5)]
        assert mock_my_results.call_args.kwargs["comparable_only"] is True

    def test_ranks_field_by_hits_then_figure_hits(self):
        results = [
            {
                "competition": {"type": "Fält"},
                "weapon_class": "R1",
                "points": None,
                "hits": 20,
                "figure_hits": 15,
                "inner_tens": 0,
            },
            {
                "competition": {"type": "Fält"},
                "weapon_class": "R1",
                "points": None,
                "hits": 22,
                "figure_hits": 10,
                "inner_tens": 0,
            },
            {
                "competition": {"type": "Fält"},
                "weapon_class": "R1",
                "points": None,
                "hits": 22,
                "figure_hits": 18,
                "inner_tens": 0,
            },
        ]

        with patch(f"{MODULE}.my_results", return_value=results):
            bests = personal_bests("CARD1")

        key = "Fält - R1"
        assert [(r["hits"], r["figure_hits"]) for r in bests[key]] == [(22, 18), (22, 10), (20, 15)]

    def test_groups_by_type_and_weapon_class(self):
        results = [
            {"competition": {"type": "Precision"}, "weapon_class": "C3", "points": 300, "inner_tens": 1, "hits": None},
            {"competition": {"type": "Precision"}, "weapon_class": "R1", "points": 310, "inner_tens": 1, "hits": None},
            {
                "competition": {"type": "Militär snabbmatch"},
                "weapon_class": "C3",
                "points": 200,
                "inner_tens": 1,
                "hits": None,
            },
        ]

        with patch(f"{MODULE}.my_results", return_value=results):
            bests = personal_bests("CARD1")

        assert set(bests.keys()) == {"Precision - C3", "Precision - R1", "Militär snabbmatch - C3"}

    def test_honours_top(self):
        results = [
            {"competition": {"type": "Precision"}, "weapon_class": "C3", "points": p, "inner_tens": 0, "hits": None}
            for p in [300, 310, 320, 330]
        ]

        with patch(f"{MODULE}.my_results", return_value=results):
            bests = personal_bests("CARD1", top=2)

        assert len(bests["Precision - C3"]) == 2
        assert [r["points"] for r in bests["Precision - C3"]] == [330, 320]


class TestMyResults:
    def test_comparable_only_drops_precision_without_seven_series(self):
        competition = make_competition(1, date(2024, 1, 1), CompetitionType.PRECISION)
        comparable = make_precision_result("CARD1", "C3", [50] * 7)
        not_comparable = make_precision_result("CARD1", "C3", [50] * 5)

        with (
            patch(f"{MODULE}.downloaded_competitions", return_value=[competition]),
            patch(f"{MODULE}.is_cached", return_value=True),
            patch(f"{MODULE}.load_index", return_value={}),
            patch(f"{MODULE}.get_results", return_value=[comparable, not_comparable]),
        ):
            results = my_results("CARD1", comparable_only=True)

        assert len(results) == 1
        assert results[0]["series_count"] == 7

    def test_without_comparable_only_keeps_all_matching_results(self):
        competition = make_competition(1, date(2024, 1, 1), CompetitionType.PRECISION)
        comparable = make_precision_result("CARD1", "C3", [50] * 7)
        not_comparable = make_precision_result("CARD1", "C3", [50] * 5)

        with (
            patch(f"{MODULE}.downloaded_competitions", return_value=[competition]),
            patch(f"{MODULE}.is_cached", return_value=True),
            patch(f"{MODULE}.load_index", return_value={}),
            patch(f"{MODULE}.get_results", return_value=[comparable, not_comparable]),
        ):
            results = my_results("CARD1", comparable_only=False)

        assert len(results) == 2

    def test_only_includes_results_for_the_given_card(self):
        competition = make_competition(1, date(2024, 1, 1), CompetitionType.PRECISION)
        mine = make_precision_result("CARD1", "C3", [50] * 7)
        other = make_precision_result("OTHER", "C3", [50] * 7)

        with (
            patch(f"{MODULE}.downloaded_competitions", return_value=[competition]),
            patch(f"{MODULE}.is_cached", return_value=True),
            patch(f"{MODULE}.load_index", return_value={}),
            patch(f"{MODULE}.get_results", return_value=[mine, other]),
        ):
            results = my_results("CARD1")

        assert len(results) == 1
        assert results[0]["card"] == "CARD1"


class TestCompetitionResults:
    def test_raises_when_competition_not_in_local_store(self):
        with patch(f"{MODULE}.is_cached", return_value=False):
            with pytest.raises(WebShooterAPIError):
                competition_results(999)

    def test_returns_results_when_competition_is_cached(self):
        competition = make_competition(1, date(2024, 1, 1), CompetitionType.PRECISION)
        result = make_precision_result("CARD1", "C3", [50] * 7)

        with (
            patch(f"{MODULE}.is_cached", return_value=True),
            patch(f"{MODULE}.get_competition", return_value=competition),
            patch(f"{MODULE}.get_results", return_value=[result]),
        ):
            data = competition_results(1)

        assert data["result_count"] == 1
        assert data["competition"]["id"] == 1

    def test_filters_by_card(self):
        competition = make_competition(1, date(2024, 1, 1), CompetitionType.PRECISION)
        mine = make_precision_result("CARD1", "C3", [50] * 7)
        other = make_precision_result("OTHER", "C3", [50] * 7)

        with (
            patch(f"{MODULE}.is_cached", return_value=True),
            patch(f"{MODULE}.get_competition", return_value=competition),
            patch(f"{MODULE}.get_results", return_value=[mine, other]),
        ):
            data = competition_results(1, card="CARD1")

        assert data["result_count"] == 1
        assert data["results"][0]["card"] == "CARD1"
