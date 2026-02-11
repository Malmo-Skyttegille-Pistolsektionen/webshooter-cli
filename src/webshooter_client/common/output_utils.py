"""Utility functions for formatting and printing output."""

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
        club: Club number to filter by
        card: Optional card number to filter by. If None, all club members match.

    Returns:
        True if signup matches the filters, False otherwise
    """
    if club != signup.spsf_club_number:
        return False
    return card is None or card == signup.shooting_card_number
