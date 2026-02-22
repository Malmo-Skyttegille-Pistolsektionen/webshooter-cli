"""Shared utilities for fetching competition results across commands."""

import sys
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Set, Tuple, TypeVar

from webshooter_client.api.api_calls import get_competitions, get_results
from webshooter_client.models.competition import CompetitionType
from webshooter_client.models.result import FieldResult, ResultBase

T = TypeVar("T")


def fetch_results_for_card(
    years: List[int],
    card: str,
    competition_types: Set[CompetitionType],
    result_filter: Optional[Callable[[ResultBase], bool]] = None,
    show_progress: bool = True,
) -> Dict[int, List[ResultBase]]:
    """Fetch results for a card across multiple years and competition types.

    This is the shared pattern used across bests, stats, and other commands:
    1. Fetch competitions for each year
    2. Filter by competition type
    3. Fetch results for each competition
    4. Filter results by card and optional result_filter
    5. Accumulate and return

    Args:
        years: List of years to fetch
        card: Shooting card number to filter by
        competition_types: Set of CompetitionType to include (e.g., {PRECISION, MILITARY})
        result_filter: Optional callable(result) -> bool for additional filtering
        show_progress: Whether to print progress to stderr

    Returns:
        Dictionary mapping year to list of valid results
    """
    results_by_year = defaultdict(list)

    # Collect all competitions in a single pass (avoids N duplicate fetches)
    all_competitions = []
    for year in years:
        comps_dict = get_competitions(year=year)
        comps = [c for c in comps_dict.values() if c.type in competition_types]
        for comp in comps:
            all_competitions.append((year, comp))

    total_comps = len(all_competitions)
    comp_count = 0

    # Fetch results for each competition
    for year, competition in all_competitions:
        comp_count += 1
        if show_progress:
            print(
                f"\rFetching competition {comp_count}/{total_comps}...",
                end="",
                flush=True,
                file=sys.stderr,
            )
        results = get_results(competition_id=competition.id)

        # Filter results for the card
        for result in results:
            if result.signup.shooting_card_number != card:
                continue

            # Apply optional result_filter if provided
            if result_filter and not result_filter(result):
                continue

            results_by_year[year].append(result)

    if show_progress:
        print(file=sys.stderr)  # New line after progress

    return dict(results_by_year)


def fetch_field_competition_results(
    years: List[int],
    card: str,
    show_progress: bool = True,
) -> Dict[int, List[Tuple[FieldResult, List[FieldResult]]]]:
    """Fetch field competition results with std medal winner context.

    For each year, returns a list of (my_result, std_medal_winners) tuples where:
    - my_result is the shooter's FieldResult for that competition
    - std_medal_winners is a list of FieldResults from std medal winners in that competition
      (those with std_medal set), used for deviation calculation.

    Only competitions where the shooter has a result are included.

    Args:
        years: List of years to fetch
        card: Shooting card number
        show_progress: Whether to print progress to stderr

    Returns:
        Dict mapping year to list of (my_result, std_medal_winners) tuples
    """
    results_by_year: Dict[int, List[Tuple[FieldResult, List[FieldResult]]]] = defaultdict(list)

    # Collect all field competitions across all years
    all_competitions = []
    for year in years:
        comps_dict = get_competitions(year=year)
        comps = [c for c in comps_dict.values() if c.type in (CompetitionType.FIELD, CompetitionType.POINTFIELD)]
        for comp in comps:
            all_competitions.append((year, comp))

    total_comps = len(all_competitions)
    comp_count = 0

    for year, competition in all_competitions:
        comp_count += 1
        if show_progress:
            print(
                f"\rFetching field competition {comp_count}/{total_comps}...",
                end="",
                flush=True,
                file=sys.stderr,
            )

        all_results = get_results(competition_id=competition.id)

        # Separate my results from std medal winners
        # Handle multiple weapon classes (e.g., C3 and A3 in same competition)
        my_results: List[FieldResult] = []
        std_medal_winners: List[FieldResult] = []

        for result in all_results:
            if not isinstance(result, FieldResult):
                continue
            if result.signup.shooting_card_number == card:
                my_results.append(result)
            elif result.std_medal is not None:
                std_medal_winners.append(result)

        # Only include competitions where the shooter participated
        # Add a tuple for each weapon class the shooter competed in
        for my_result in my_results:
            results_by_year[year].append((my_result, std_medal_winners))

    if show_progress:
        print(file=sys.stderr)  # New line after progress

    return dict(results_by_year)
