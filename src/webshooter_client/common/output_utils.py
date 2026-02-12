"""Utility functions for formatting and printing output."""

from typing import List, Any
from tabulate import tabulate

from webshooter_client.models.competition import Competition
from webshooter_client.models.signup import Signup


def print_competition_header(competition: Competition) -> None:
    """Print standard competition information header.

    Args:
        competition: Competition object to print details for
    """
    print(f"Competition: {competition.name}")
    print(f"Type: {competition.type.display_name}")
    print(f"Date: {competition.competition_date.isoformat()}")
    print(f"Location: {competition.venue}, {competition.city}")
    print("")


def matches_club_and_card(signup: Signup, club: str, card: str = None) -> bool:
    """Check if a signup matches the specified club and optional card filter.

    Args:
        signup: Signup object to check
        club: Club number to filter by (can be None if only card is specified)
        card: Optional card number to filter by. If None, all club members match.

    Returns:
        True if signup matches the filters, False otherwise
    """
    # If card is provided, only match that specific card (ignore club)
    if card:
        return card == signup.shooting_card_number

    # If only club is provided, match all members of that club
    if club:
        return club == signup.spsf_club_number

    # If neither is provided, match nothing
    return False


def print_table(data: List[List[Any]], headers: List[str], tablefmt: str = "simple") -> None:
    """Print formatted table output.

    Args:
        data: Table data as list of rows
        headers: Column headers
        tablefmt: Table format (default: simple)
    """
    print(tabulate(data, headers=headers, tablefmt=tablefmt))
