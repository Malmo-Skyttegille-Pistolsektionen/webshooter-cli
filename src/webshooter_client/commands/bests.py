"""Display personal best results for a shooter."""

import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from tabulate import tabulate

from webshooter_client.api.api_calls import get_competitions, get_results
from webshooter_client.common.fetch_utils import is_locally_available
from webshooter_client.common.competition_filter import (
    is_valid_precision_result,
    get_result_points,
    is_valid_field_result,
    get_field_result_hits,
    get_field_result_figures,
    get_field_result_points,
)
from webshooter_client.models.competition import Competition, CompetitionType
from webshooter_client.models.result import PrecisionResult, MilitaryResult, FieldResult, ResultBase, SeriesResult


@dataclass(kw_only=True)
class PersonalBest:
    """Represents a single personal best result."""

    competition_name: str
    competition_date: date
    competition_type: str  # "Precision" or "Militär snabbmatch"
    weapon_class: str
    points: int
    inner_tens: int
    series: List[int]
    placement: int


@dataclass(kw_only=True)
class FieldPersonalBest:
    """Represents a single personal best result for Field competitions."""

    competition_name: str
    competition_date: date
    competition_type: str  # "Fält" or "Poängfält"
    weapon_class: str
    hits: int
    figures: int
    points: int
    num_stations: int
    placement: int


def _calculate_inner_tens(series: List[SeriesResult]) -> int:
    """Calculate total inner tens from series."""
    return sum(s.inner_tens for s in series)


def _format_series(series: List[SeriesResult]) -> str:
    """Format series as space-separated points."""
    return " ".join(str(s.points) for s in series)


def _extract_personal_best(result: ResultBase, competition: Competition, card: str) -> Optional[PersonalBest]:
    """Extract PersonalBest from result if card matches and has series data.

    For Precision competitions, only uses the 7 regular series scores,
    ignoring any finals (which are added to total points but not in series list).
    Military competitions always have 12 series.
    """
    if result.signup.shooting_card_number != card:
        return None

    # Only handle Precision and Military results
    if not isinstance(result, (PrecisionResult, MilitaryResult)):
        return None

    if not result.series:
        return None

    # For Precision: only count competitions with exactly 7 series
    # Use shared filtering utility
    if isinstance(result, PrecisionResult):
        if not is_valid_precision_result(result):
            return None
        points = get_result_points(result)
        competition_type = "Precision"
    else:
        # Military: use total points as normal
        points = get_result_points(result)
        competition_type = "Militär snabbmatch"

    return PersonalBest(
        competition_name=competition.name,
        competition_date=competition.competition_date,
        competition_type=competition_type,
        weapon_class=result.signup.weapon_class,
        points=points,
        inner_tens=_calculate_inner_tens(result.series),
        series=[s.points for s in result.series],
        placement=result.placement,
    )


def _extract_field_personal_best(
    result: ResultBase, competition: Competition, card: str
) -> Optional[FieldPersonalBest]:
    """Extract FieldPersonalBest from result if card matches and has station data.

    Field competitions use station-based structure (hits, figures, points per station).
    Ranked by total hits (primary ranking metric for Field).

    Args:
        result: Result to extract from
        competition: Competition the result belongs to
        card: Shooting card number to match

    Returns:
        FieldPersonalBest if result is valid Field result for this card, None otherwise
    """
    if result.signup.shooting_card_number != card:
        return None

    if not isinstance(result, FieldResult):
        return None

    if not is_valid_field_result(result):
        return None

    hits = get_field_result_hits(result)
    figures = get_field_result_figures(result)
    points = get_field_result_points(result)

    return FieldPersonalBest(
        competition_name=competition.name,
        competition_date=competition.competition_date,
        competition_type=competition.type.display_name,
        weapon_class=result.signup.weapon_class,
        hits=hits,
        figures=figures,
        points=points,
        num_stations=len(result.stations),
        placement=result.placement,
    )


def _fetch_all_personal_bests(year: int, card: str) -> tuple[List[PersonalBest], List[FieldPersonalBest]]:
    """Fetch all personal bests for a card in given year.

    Returns:
        Tuple of (series_bests, field_bests)
    """
    competitions_dict = get_competitions(year=year)
    competitions = list(competitions_dict.values())

    # Filter to Precision, Military, Field, and PointField
    relevant_competitions = [
        c
        for c in competitions
        if c.type
        in (CompetitionType.PRECISION, CompetitionType.MILITARY, CompetitionType.FIELD, CompetitionType.POINTFIELD)
        and is_locally_available(c)
    ]

    personal_bests: List[PersonalBest] = []
    field_bests: List[FieldPersonalBest] = []
    for i, competition in enumerate(relevant_competitions, 1):
        print(
            f"\rFetching competition {i}/{len(relevant_competitions)}...",
            end="",
            flush=True,
            file=sys.stderr,
        )
        results = get_results(competition_id=competition.id)

        for result in results:
            pb = _extract_personal_best(result, competition, card)
            if pb:
                personal_bests.append(pb)
            fpb = _extract_field_personal_best(result, competition, card)
            if fpb:
                field_bests.append(fpb)

    print(file=sys.stderr)  # New line after progress indicator
    return personal_bests, field_bests


def _group_by_type_and_class(
    personal_bests: List[PersonalBest],
) -> Dict[str, List[PersonalBest]]:
    """Group personal bests by competition type and weapon class, sort by points descending."""
    grouped = defaultdict(list)

    for pb in personal_bests:
        # Group by both type and class: "Precision - A3", "Militär snabbmatch - C3"
        key = f"{pb.competition_type} - {pb.weapon_class}"
        grouped[key].append(pb)

    # Sort each group by points (descending), then by date (newest first)
    for key in grouped:
        grouped[key].sort(key=lambda x: (-x.points, x.competition_date), reverse=False)

    return dict(grouped)


def _format_type_class_section(type_class_key: str, personal_bests: List[PersonalBest], top_n: int) -> str:
    """Format a single competition type + weapon class section."""
    output = [f"\n=== {type_class_key} ==="]

    # Take top N
    top_results = personal_bests[:top_n]

    table_data = []
    for rank, pb in enumerate(top_results, 1):
        table_data.append(
            [
                rank,
                pb.points,
                pb.inner_tens,
                pb.competition_date.strftime("%Y-%m-%d"),
                pb.competition_name,
                _format_series([SeriesResult(points=p, inner_tens=0) for p in pb.series]),
            ]
        )

    headers = ["Rank", "Points", "Xs", "Date", "Competition", "Series"]
    output.append(tabulate(table_data, headers=headers, tablefmt="simple"))

    return "\n".join(output)


def _group_field_by_type_and_class(
    field_bests: List[FieldPersonalBest],
) -> Dict[str, List[FieldPersonalBest]]:
    """Group field personal bests by competition type and weapon class, sorted by hits descending."""
    grouped: Dict[str, List[FieldPersonalBest]] = defaultdict(list)

    for fpb in field_bests:
        key = f"{fpb.competition_type} - {fpb.weapon_class}"
        grouped[key].append(fpb)

    # Sort by hits (descending) as primary ranking metric for Field
    for key in grouped:
        grouped[key].sort(key=lambda x: (-x.hits, -x.figures, x.competition_date), reverse=False)

    return dict(grouped)


def _format_field_type_class_section(type_class_key: str, field_bests: List[FieldPersonalBest], top_n: int) -> str:
    """Format a single Field competition type + weapon class section."""
    output = [f"\n=== {type_class_key} ==="]

    top_results = field_bests[:top_n]

    table_data = []
    for rank, fpb in enumerate(top_results, 1):
        table_data.append(
            [
                rank,
                fpb.hits,
                fpb.figures,
                fpb.points,
                fpb.num_stations,
                fpb.competition_date.strftime("%Y-%m-%d"),
                fpb.competition_name,
            ]
        )

    headers = ["Rank", "Hits", "Figures", "Points", "Stations", "Date", "Competition"]
    output.append(tabulate(table_data, headers=headers, tablefmt="simple"))

    return "\n".join(output)


def get_personal_bests(card: str, year: int, top_n: int = 10) -> None:
    """Display personal bests for a shooter.

    Args:
        card: Shooting card number
        year: Year to analyze
        top_n: Number of top results to show per weapon class (default: 10)
    """
    print(f"Personal Bests for Card: {card}", file=sys.stderr)
    print(f"Year: {year}", file=sys.stderr)
    print("Competition Types: Precision, Militär snabbmatch, Fält, Poängfält", file=sys.stderr)
    print(file=sys.stderr)

    # Fetch all personal bests (series-based and field)
    personal_bests, field_bests = _fetch_all_personal_bests(year, card)

    if not personal_bests and not field_bests:
        print(f"No results found for card {card} in {year}", file=sys.stderr)
        return

    # Display series-based bests (Precision / Military)
    if personal_bests:
        grouped = _group_by_type_and_class(personal_bests)
        type_class_keys = sorted(grouped.keys())
        for type_class_key in type_class_keys:
            section = _format_type_class_section(type_class_key, grouped[type_class_key], top_n)
            print(section)

    # Display field bests (Fält / Poängfält) in separate table ranked by hits
    if field_bests:
        field_grouped = _group_field_by_type_and_class(field_bests)
        field_keys = sorted(field_grouped.keys())
        for key in field_keys:
            section = _format_field_type_class_section(key, field_grouped[key], top_n)
            print(section)

    print()
    print("Note: Only showing weapon classes where you competed.", file=sys.stderr)
