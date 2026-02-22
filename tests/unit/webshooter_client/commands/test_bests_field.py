"""Unit tests for Field competition support in bests command."""

from datetime import date
from unittest.mock import Mock

from webshooter_client.commands.bests import (
    FieldPersonalBest,
    _extract_field_personal_best,
    _group_field_by_type_and_class,
    _format_field_type_class_section,
)
from webshooter_client.models.competition import Competition, CompetitionType
from webshooter_client.models.result import FieldResult, StationResult


def make_station(hits: int, figure_hits: int = 3, points: int = 10) -> StationResult:
    return StationResult(hits=hits, figure_hits=figure_hits, points=points)


def make_field_result(card: str, hits_per_station: list, placement: int = 5) -> FieldResult:
    signup = Mock()
    signup.shooting_card_number = card
    signup.weapon_class = "C3"
    stations = [make_station(h) for h in hits_per_station]
    return FieldResult(
        signup=signup, placement=placement, std_medal=None, points=sum(hits_per_station), stations=stations
    )


def make_field_competition(name: str = "Fält Test") -> Competition:
    return Competition(
        id=1,
        name=name,
        competition_date=date(2024, 5, 15),
        signups_close=date(2024, 5, 10),
        city="Test",
        venue="Test",
        type=CompetitionType.FIELD,
    )


class TestExtractFieldPersonalBest:
    def test_returns_field_personal_best_for_matching_card(self):
        result = make_field_result("10008", [5, 6, 4, 6, 5, 6, 5, 6])
        comp = make_field_competition()

        fpb = _extract_field_personal_best(result, comp, "10008")

        assert fpb is not None
        assert isinstance(fpb, FieldPersonalBest)
        assert fpb.hits == 43  # sum of [5,6,4,6,5,6,5,6]
        assert fpb.num_stations == 8
        assert fpb.competition_name == "Fält Test"

    def test_returns_none_for_non_matching_card(self):
        result = make_field_result("99999", [5, 6, 4, 6])
        comp = make_field_competition()

        fpb = _extract_field_personal_best(result, comp, "10008")
        assert fpb is None

    def test_returns_none_for_non_field_result(self):
        from webshooter_client.models.result import PrecisionResult, SeriesResult

        signup = Mock()
        signup.shooting_card_number = "10008"
        signup.weapon_class = "C3"
        series = [SeriesResult(points=45, inner_tens=2) for _ in range(7)]
        precision = PrecisionResult(signup=signup, placement=1, std_medal=None, points=315, series=series)
        comp = make_field_competition()

        fpb = _extract_field_personal_best(precision, comp, "10008")
        assert fpb is None

    def test_returns_none_for_empty_stations(self):
        signup = Mock()
        signup.shooting_card_number = "10008"
        signup.weapon_class = "C3"
        result = FieldResult(signup=signup, placement=1, std_medal=None, points=0, stations=[])
        comp = make_field_competition()

        fpb = _extract_field_personal_best(result, comp, "10008")
        assert fpb is None

    def test_field_personal_best_figures_and_points(self):
        signup = Mock()
        signup.shooting_card_number = "10008"
        signup.weapon_class = "C3"
        stations = [
            StationResult(hits=5, figure_hits=4, points=10),
            StationResult(hits=6, figure_hits=5, points=15),
        ]
        result = FieldResult(signup=signup, placement=2, std_medal=None, points=25, stations=stations)
        comp = make_field_competition()

        fpb = _extract_field_personal_best(result, comp, "10008")

        assert fpb is not None
        assert fpb.hits == 11  # 5 + 6
        assert fpb.figures == 9  # 4 + 5
        assert fpb.points == 25  # 10 + 15
        assert fpb.placement == 2

    def test_competition_type_is_display_name(self):
        result = make_field_result("10008", [5, 6, 4, 6, 5])
        comp = make_field_competition()
        fpb = _extract_field_personal_best(result, comp, "10008")
        assert fpb.competition_type == "Fält"

    def test_pointfield_competition_type(self):
        result = make_field_result("10008", [5, 6, 4, 6, 5])
        comp = Competition(
            id=2,
            name="Poängfält Test",
            competition_date=date(2024, 6, 1),
            signups_close=date(2024, 5, 25),
            city="Test",
            venue="Test",
            type=CompetitionType.POINTFIELD,
        )
        fpb = _extract_field_personal_best(result, comp, "10008")
        assert fpb.competition_type == "Poängfält"


class TestGroupFieldByTypeAndClass:
    def make_fpb(self, comp_type: str, weapon_class: str, hits: int) -> FieldPersonalBest:
        return FieldPersonalBest(
            competition_name="Test",
            competition_date=date(2024, 1, 1),
            competition_type=comp_type,
            weapon_class=weapon_class,
            hits=hits,
            figures=hits - 2,
            points=hits * 2,
            num_stations=8,
            placement=1,
        )

    def test_groups_by_type_and_class(self):
        bests = [
            self.make_fpb("Fält", "C3", 40),
            self.make_fpb("Fält", "C3", 45),
            self.make_fpb("Fält", "A1", 38),
        ]
        grouped = _group_field_by_type_and_class(bests)

        assert "Fält - C3" in grouped
        assert "Fält - A1" in grouped
        assert len(grouped["Fält - C3"]) == 2

    def test_sorted_by_hits_descending(self):
        bests = [
            self.make_fpb("Fält", "C3", 35),
            self.make_fpb("Fält", "C3", 45),
            self.make_fpb("Fält", "C3", 40),
        ]
        grouped = _group_field_by_type_and_class(bests)
        hits = [fpb.hits for fpb in grouped["Fält - C3"]]
        assert hits == [45, 40, 35]


class TestFormatFieldTypeClassSection:
    def test_produces_table_output(self):
        bests = [
            FieldPersonalBest(
                competition_name="Fält Stockholm",
                competition_date=date(2024, 5, 15),
                competition_type="Fält",
                weapon_class="C3",
                hits=43,
                figures=38,
                points=50,
                num_stations=8,
                placement=5,
            )
        ]
        output = _format_field_type_class_section("Fält - C3", bests, top_n=5)
        assert "Fält - C3" in output
        assert "43" in output  # hits
        assert "38" in output  # figures
        assert "Fält Stockholm" in output
        assert "Hits" in output

    def test_top_n_limits_output(self):
        bests = [
            FieldPersonalBest(
                competition_name=f"Comp {i}",
                competition_date=date(2024, 1, i + 1),
                competition_type="Fält",
                weapon_class="C3",
                hits=40 + i,
                figures=35 + i,
                points=50 + i,
                num_stations=8,
                placement=i + 1,
            )
            for i in range(5)
        ]
        output = _format_field_type_class_section("Fält - C3", bests, top_n=3)
        # Only top 3 should appear (after sorting by hits, indices 4, 3, 2 are top)
        # Rank column should go up to 3
        assert "4" not in output.split("===")[1].split("Comp")[0]
