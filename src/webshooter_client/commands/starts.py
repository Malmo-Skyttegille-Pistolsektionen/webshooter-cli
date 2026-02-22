"""Calculate total starts command."""

from typing import Optional
import logging

from webshooter_client.api import api_calls
from webshooter_client.models.competition import Competition, CompetitionType
from webshooter_client.common.output_utils import print_table


def get_starts_total(club: str, card: Optional[str] = None, year: Optional[int] = None) -> None:
    """Calculate and display total starts across competitions.

    Args:
        club: Club number to filter by
        card: Optional shooting card number to filter by
        year: Optional year to filter competitions
    """
    counters = {comp_type: 0 for comp_type in CompetitionType}

    competitions: dict[int, Competition] = api_calls.get_competitions(year=year)

    for competition in competitions.values():
        logging.info(f"Date: {competition.competition_date} ID: {competition.id} Type: {competition.type}")

        results = api_calls.get_results(competition_id=competition.id)

        if results:
            for result in results:
                signup = result.signup
                # Filter by card if provided, otherwise by club
                if card and signup.shooting_card_number == card:
                    counters[competition.type] += 1
                elif not card and signup.spsf_club_number == club:
                    counters[competition.type] += 1

    # Prepare data for tabulate
    table_data = []
    table_data.append(["Club", club])
    table_data.append(["Card", card])
    table_data.append(["Year", year])
    table_data.append(["", ""])

    for comp_type in counters.keys():
        table_data.append([comp_type.display_name, counters[comp_type]])

    table_data.append(["", ""])
    table_data.append(["Total starts", sum([counters[type] for type in counters.keys()])])

    print_table(table_data, headers=[])
