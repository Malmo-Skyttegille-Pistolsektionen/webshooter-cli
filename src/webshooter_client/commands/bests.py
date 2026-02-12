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
    """Extract PersonalBest from result if card matches and has series data."""
    if result.signup.shooting_card_number != card:
        return None

    # Only handle Precision and Military results
    if not isinstance(result, (PrecisionResult, MilitaryResult)):
        return None

    if not result.series:
        return None

    return PersonalBest(
        competition_name=competition.name,
        competition_date=competition.competition_date,
        weapon_class=result.signup.weapon_class,
        points=result.points,
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


def _group_by_weapon_class(personal_bests: List[PersonalBest]) -> Dict[str, List[PersonalBest]]:
    """Group personal bests by weapon class and sort by points descending."""
    grouped = defaultdict(list)

    for pb in personal_bests:
        grouped[pb.weapon_class].append(pb)

    # Sort each group by points (descending), then by date (newest first)
    for weapon_class in grouped:
        grouped[weapon_class].sort(key=lambda x: (-x.points, x.competition_date), reverse=False)

    return dict(grouped)


def _determine_competition_type_for_class(weapon_class: str, personal_bests: List[PersonalBest]) -> str:
    """Determine competition type name based on series count."""
    if not personal_bests:
        return "Unknown"

    # Use first result to determine type
    series_count = len(personal_bests[0].series)
    if series_count == 7:
        return "Precision"
    elif series_count == 12:
        return "Militär snabbmatch"
    return "Unknown"


def _format_weapon_class_section(weapon_class: str, personal_bests: List[PersonalBest], top_n: int) -> str:
    """Format a single weapon class section."""
    competition_type = _determine_competition_type_for_class(weapon_class, personal_bests)

    output = [f"\n=== {competition_type} - {weapon_class} ==="]

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

    # Group by weapon class
    grouped = _group_by_weapon_class(personal_bests)

    # Display each weapon class (only those with results)
    weapon_classes = sorted(grouped.keys())
    for weapon_class in weapon_classes:
        section = _format_weapon_class_section(weapon_class, grouped[weapon_class], top_n)
        print(section)

    print()
    print("Note: Only showing weapon classes where you competed.")
