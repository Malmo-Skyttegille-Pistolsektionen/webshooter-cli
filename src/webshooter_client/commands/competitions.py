from typing import Optional

from tabulate import tabulate

from webshooter_client.api import api_calls
from webshooter_client.models.competition import Competition


class CompetitionsCommand:

    @staticmethod
    def get_competitions(year: Optional[int]) -> None:
        competitions: dict[int, Competition] = api_calls.get_competitions(year=year)
        table_data = [
            [comp.competition_date, comp.type.display_name, comp_id, comp.name]
            for comp_id, comp in competitions.items()
        ]

        print(
            tabulate(
                table_data,
                headers=[
                    "Date",
                    "Type",
                    "ID",
                    "Name",
                ],
                tablefmt="simple",
            )
        )
        print(f"\nTotal: {len(competitions)}")
