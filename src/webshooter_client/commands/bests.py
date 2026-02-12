"""Display personal best results for a shooter."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from tabulate import tabulate

from webshooter_client.api.api_calls import get_competitions, get_results
from webshooter_client.models.competition import Competition, CompetitionType
from webshooter_client.models.result import PrecisionResult, MilitaryResult, ResultBase, SeriesResult


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
    # Use sum of series points (ignores finals that may be in total)
    if isinstance(result, PrecisionResult):
        if len(result.series) != 7:
            return None
        # Use series sum, not total points (which may include finals)
        points = sum(s.points for s in result.series)
        competition_type = "Precision"
    else:
        # Military: use total points as normal
        points = result.points
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


def _fetch_all_personal_bests(year: int, card: str) -> List[PersonalBest]:
    """Fetch all personal bests for a card in given year."""
    competitions_dict = get_competitions(year=year)
    competitions = list(competitions_dict.values())

    # Filter to only Precision and Military
    relevant_competitions = [c for c in competitions if c.type in (CompetitionType.PRECISION, CompetitionType.MILITARY)]

    personal_bests = []
    for i, competition in enumerate(relevant_competitions, 1):
        print(
            f"\rFetching competition {i}/{len(relevant_competitions)}...",
            end="",
            flush=True,
        )
        results = get_results(competition_id=competition.id)

        for result in results:
            pb = _extract_personal_best(result, competition, card)
            if pb:
                personal_bests.append(pb)

    print()  # New line after progress indicator
    return personal_bests


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


def get_personal_bests(card: str, year: int, top_n: int = 10) -> None:
    """Display personal bests for a shooter.

    Args:
        card: Shooting card number
        year: Year to analyze
        top_n: Number of top results to show per weapon class (default: 10)
    """
    print(f"Personal Bests for Card: {card}")
    print(f"Year: {year}")
    print("Competition Types: Precision, Militär snabbmatch")
    print()

    # Fetch all personal bests
    personal_bests = _fetch_all_personal_bests(year, card)

    if not personal_bests:
        print(f"No results found for card {card} in {year}")
        return

    # Group by competition type and weapon class
    grouped = _group_by_type_and_class(personal_bests)

    # Display each type+class combination (only those with results)
    type_class_keys = sorted(grouped.keys())
    for type_class_key in type_class_keys:
        section = _format_type_class_section(type_class_key, grouped[type_class_key], top_n)
        print(section)

    print()
    print("Note: Only showing weapon classes where you competed.")
