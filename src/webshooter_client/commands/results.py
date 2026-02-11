from typing import Optional
from tabulate import tabulate
import pandas as pd

from webshooter_client.api.api_calls import get_results, get_competition
from webshooter_client.models.competition import Competition, CompetitionType
from webshooter_client.common.output_utils import print_competition_header, matches_club_and_card


class ResultsCommand:
    """Command to display competition results."""

    @staticmethod
    def get_results_for_competition(competition_id: int, club: str, card: Optional[str]) -> None:  # noqa: C901
        competition: Competition = get_competition(competition_id=competition_id)
        results = get_results(competition_id=competition_id)

        print_competition_header(competition)

        #  results for military and precision shall be presented using tabulate

        if competition.type in [
            CompetitionType.PRECISION,
            CompetitionType.MILITARY,
        ]:
            table_data = []
            for result in results:
                signup = result.signup

                if (club == signup.spsf_club_number and not card) or card == signup.shooting_card_number:
                    table_data.append(
                        [
                            signup.shooting_card_number,
                            signup.fullname,
                            signup.weapon_class_general,
                            signup.weapon_class,
                            result.placement,
                            result.std_medal.display_name if result.std_medal else "",
                            result.points,
                            sum(series.inner_tens for series in result.series),
                            " ".join(str(series.points) for series in result.series),
                        ]
                    )

            headers = ["Card", "Name", "Main Class", "Sub class", "Place", "Medal", "Points", "Xs", "Series"]
            df = pd.DataFrame(data=table_data, columns=headers)
            df_sorted = df.sort_values(by=["Main Class", "Place"], ascending=[True, True])

            print(tabulate(df_sorted, headers=headers, tablefmt="simple"))
        elif competition.type == CompetitionType.FIELD:
            table_data = []
            for result in results:
                signup = result.signup

                if matches_club_and_card(signup, club, card):
                    table_data.append(
                        [
                            signup.shooting_card_number,
                            signup.fullname,
                            signup.weapon_class_general,
                            signup.weapon_class,
                            result.placement,
                            result.std_medal.display_name if result.std_medal else "",
                            sum(r.hits for r in result.stations),
                            sum(r.figure_hits for r in result.stations),
                            result.points,
                            " ".join(f"{r.hits}/{r.figure_hits}" for r in result.stations),
                        ]
                    )

            headers = [
                "Card",
                "Name",
                "Main Class",
                "Sub class",
                "Place",
                "Medal",
                "Hits",
                "Figures",
                "Points",
                "Stations",
            ]
            df = pd.DataFrame(data=table_data, columns=headers)
            df_sorted = df.sort_values(by=["Main Class", "Place"], ascending=[True, True])

            print(tabulate(df_sorted, headers=headers, tablefmt="simple"))
