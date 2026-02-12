"""List competitions command."""

from typing import Optional

from webshooter_client.api import api_calls
from webshooter_client.models.competition import Competition
from webshooter_client.common.output_utils import print_table


def get_competitions(year: Optional[int] = None) -> None:
    """List all competitions, optionally filtered by year.

    Args:
        year: Optional year to filter competitions
    """
    competitions: dict[int, Competition] = api_calls.get_competitions(year=year)
    table_data = [
        [comp.competition_date, comp.type.display_name, comp_id, comp.name] for comp_id, comp in competitions.items()
    ]

    print_table(table_data, headers=["Date", "Type", "ID", "Name"])
    print(f"\nTotal: {len(competitions)}")
