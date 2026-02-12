"""Display competition results command."""

from typing import Optional

from webshooter_client.api.api_calls import get_results, get_competition
from webshooter_client.models.competition import Competition
from webshooter_client.common.output_utils import print_competition_header
from webshooter_client.commands.result_formatters import ResultFormatterFactory


def get_results_for_competition(competition_id: int, club: str, card: Optional[str] = None) -> None:
    """Display competition results filtered by club/card.

    Args:
        competition_id: ID of the competition
        club: Club number to filter by
        card: Optional shooting card number to filter by

    Returns:
        Dictionary of results organized by card number (for starts command)
    """
    competition: Competition = get_competition(competition_id=competition_id)
    results = get_results(competition_id=competition_id)

    print_competition_header(competition)

    # Use strategy pattern to format results based on competition type
    formatter = ResultFormatterFactory.get_formatter(competition.type)
    return formatter.format_and_print(results, club, card)
