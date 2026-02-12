"""Display signups for a competition command."""

from typing import Dict, List, Set, Optional
from dataclasses import dataclass

from webshooter_client.api.api_calls import get_competition
from webshooter_client.api.api_calls import get_signups as fetch_signups
from webshooter_client.models.competition import Competition
from webshooter_client.models.signup import Signup
from webshooter_client.common.output_utils import (
    print_competition_header,
    matches_club_and_card,
    print_table,
)


@dataclass
class SignupData:
    """Data structure for aggregated signup information."""

    card: int
    name: str
    classes: Set[str]
    patrol_mates: List[str]


def get_signups(competition_id: int, club: str, card: Optional[int] = None) -> None:
    """Display signups for a competition filtered by club/card.

    Args:
        competition_id: ID of the competition
        club: Club number to filter by
        card: Optional shooting card number to filter by
    """
    competition: Competition = get_competition(competition_id=competition_id)
    print_competition_header(competition)

    signups: List[Signup] = fetch_signups(competition_id=competition_id)

    # Build indexed lookup for efficient patrol mate resolution
    signups_by_card = {s.shooting_card_number: s for s in signups}

    # Aggregate signup data
    signup_data_map = _aggregate_signup_data(signups, signups_by_card, club, card)

    # Count weapon class distribution
    counter_all, counter_club = _count_weapon_classes(signups, club, card)

    # Display results
    _display_signup_table(signup_data_map)
    print("\n\n")
    _display_stats_table(counter_all, counter_club, club)


def _aggregate_signup_data(
    signups: List[Signup], signups_by_card: Dict[int, Signup], club: str, card: int
) -> Dict[int, SignupData]:
    """Aggregate signup information for matching club/card.

    Args:
        signups: All signups for the competition
        signups_by_card: Indexed lookup of signups by card number
        club: Club number filter
        card: Optional card number filter

    Returns:
        Dictionary mapping card numbers to SignupData objects
    """
    result: Dict[int, SignupData] = {}

    for signup in signups:
        if not matches_club_and_card(signup, club, card):
            continue

        card_number = signup.shooting_card_number
        if card_number not in result:
            result[card_number] = SignupData(card=card_number, name=signup.fullname, classes=set(), patrol_mates=[])

        result[card_number].classes.add(signup.weapon_class)

        # Resolve patrol mate using indexed lookup
        if signup.share_patrol_with:
            mate = signups_by_card.get(signup.share_patrol_with)
            if mate:
                result[card_number].patrol_mates.append(f"{mate.fullname} ({mate.weapon_class})")
            else:
                result[card_number].patrol_mates.append(str(signup.share_patrol_with))

    return result


def _count_weapon_classes(
    signups: List[Signup], club: str, card: Optional[int]
) -> tuple[Dict[str, int], Dict[str, int]]:
    """Count signups by weapon class for all and club-filtered signups.

    Args:
        signups: All signups for the competition
        club: Club number filter
        card: Optional card number filter

    Returns:
        Tuple of (all_counts, club_counts) dictionaries
    """
    counter_all: Dict[str, int] = {}
    counter_club: Dict[str, int] = {}

    for signup in signups:
        weapon_class = signup.weapon_class_general
        counter_all[weapon_class] = counter_all.get(weapon_class, 0) + 1

        if matches_club_and_card(signup, club, card):
            counter_club[weapon_class] = counter_club.get(weapon_class, 0) + 1

    return counter_all, counter_club


def _display_signup_table(signup_data_map: Dict[int, SignupData]) -> None:
    """Display table of individual signups.

    Args:
        signup_data_map: Aggregated signup data by card number
    """
    table_data = []
    for card_number in sorted(signup_data_map.keys()):
        signup_data = signup_data_map[card_number]
        classes_str = ", ".join(sorted(signup_data.classes))
        patrol_mates_str = ", ".join(sorted(signup_data.patrol_mates))
        table_data.append([signup_data.card, signup_data.name, classes_str, patrol_mates_str])

    headers = ["Card", "Name", "Classes", "Patrol Mates"]
    print_table(table_data, headers)


def _display_stats_table(counter_all: Dict[str, int], counter_club: Dict[str, int], club: str) -> None:
    """Display statistics table of weapon class distribution.

    Args:
        counter_all: Counts for all signups
        counter_club: Counts for club-filtered signups
        club: Club number for display
    """
    all_classes = sorted(set(counter_all.keys()) | set(counter_club.keys()))

    signups_stats_table_data = []
    total_club = 0
    total_all = 0

    for weapon_class in all_classes:
        all_count = counter_all.get(weapon_class, 0)
        club_count = counter_club.get(weapon_class, 0)
        signups_stats_table_data.append([weapon_class, club_count, all_count])
        total_club += club_count
        total_all += all_count

    signups_stats_table_data.append(["Total", total_club, total_all])

    stats_headers = ["Weapon Class", f"Club {club}", "All"]
    print_table(signups_stats_table_data, stats_headers)
