from typing import Optional

from webshooter_client.api import api_calls
from webshooter_client.models.competition import Competition
from webshooter_client.commands.base_command import BaseCommand


class CompetitionsCommand(BaseCommand):

    @staticmethod
    def get_competitions(year: Optional[int]) -> None:
        competitions: dict[int, Competition] = api_calls.get_competitions(year=year)
        table_data = [
            [comp.competition_date, comp.type.display_name, comp_id, comp.name]
            for comp_id, comp in competitions.items()
        ]

        BaseCommand.print_table(table_data, headers=["Date", "Type", "ID", "Name"])
        print(f"\nTotal: {len(competitions)}")
