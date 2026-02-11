from typing import Optional
from webshooter_client.api.api_calls import get_competitions, get_results
from webshooter_client.models.competition import Competition, CompetitionType
from tabulate import tabulate
from webshooter_client.models.result import StdMedal
from webshooter_client.common.output_utils import matches_club_and_card


class MedalsCommand:
    """Command to calculate medal statistics for shooters."""

    @staticmethod
    def get_medals(club: str, card: Optional[str], year: int) -> None:

        shooter_medals: dict[int, dict[CompetitionType, dict[StdMedal, int]]] = {}

        competitions: dict[int, Competition] = get_competitions(year=year)

        for competition in competitions.values():
            # Skip competition 53 - it's a test competition in the webshooter.se system
            if competition.id == 53:
                continue

            results = get_results(competition_id=competition.id)

            # sum up medals per shooter and competition type
            for result in results:
                signup = result.signup
                key = (signup.shooting_card_number, signup.fullname)

                if matches_club_and_card(signup, club, card):

                    if key not in shooter_medals:
                        shooter_medals[key] = {}

                    if competition.type not in shooter_medals[key]:
                        shooter_medals[key][competition.type] = {}

                    if result.std_medal:
                        current_count = shooter_medals[key][competition.type].get(result.std_medal, 0)
                        shooter_medals[key][competition.type][result.std_medal] = current_count + 1

        # Prepare data for tabulate
        table_data = []
        for key, comp_types in shooter_medals.items():
            for comp_type, medals in comp_types.items():
                silver = medals.get(StdMedal.SILVER, 0)
                bronze = medals.get(StdMedal.BRONZE, 0)
                table_data.append([key[0], key[1], comp_type.display_name, silver, bronze])

        print(f"Medals for year {year}" if year else "")

        headers = ["Card Number", "Name", "Type", "Silver", "Bronze"]
        print(tabulate(table_data, headers=headers, tablefmt="simple"))
