from typing import Optional

from webshooter_client.commands.results import ResultsCommand
from webshooter_client.api import api_calls
from webshooter_client.models.competition import Competition, CompetitionType
from webshooter_client.commands.base_command import BaseCommand
import logging


class StartsCommand(BaseCommand):
    """Command to calculate total starts across competitions."""

    @staticmethod
    def get_starts_total(club: str, card: Optional[str], year: Optional[int] = None) -> None:
        counters = {comp_type: 0 for comp_type in CompetitionType}

        competitions: dict[int, Competition] = api_calls.get_competitions(year=year)

        for competition in competitions.values():
            logging.info(f"Date: {competition.competition_date} ID: {competition.id} Type: {competition.type}")

            results = ResultsCommand.get_results_for_competition(competition_id=competition.id, club=club, card=card)

            if results:
                for card in results.keys():
                    if card != 0:
                        counters[competition.type] += len(results[card]["lines"])

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

        BaseCommand.print_table(table_data, headers=[])

        return
