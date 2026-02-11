from typing import Optional

from webshooter_client.api.api_calls import get_results, get_competition
from webshooter_client.models.competition import Competition
from webshooter_client.common.output_utils import print_competition_header
from webshooter_client.commands.base_command import BaseCommand
from webshooter_client.commands.result_formatters import ResultFormatterFactory


class ResultsCommand(BaseCommand):
    """Command to display competition results."""

    @staticmethod
    def get_results_for_competition(competition_id: int, club: str, card: Optional[str]) -> None:
        competition: Competition = get_competition(competition_id=competition_id)
        results = get_results(competition_id=competition_id)

        print_competition_header(competition)

        # Use strategy pattern to format results based on competition type
        formatter = ResultFormatterFactory.get_formatter(competition.type)
        formatter.format_and_print(results, club, card)
