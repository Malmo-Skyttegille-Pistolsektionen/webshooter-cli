from typing import List, Optional
from tabulate import tabulate
from webshooter_client.api.api_calls import get_patrols, get_competition
from webshooter_client.models.competition import Competition
from webshooter_client.models.patrol import Patrol


class StartTimesCommand:
    """Command to display start times for a competition."""
    
    @staticmethod
    def get_starttimes(competition_id: int, club: str, card: Optional[str]) -> None:

        competition: Competition = get_competition(competition_id=competition_id)

        # output some info about the competition
        print(f"Competition: {competition.name}")
        print(f"Type: {competition.type.display_name}")
        print(f"Date: {competition.competition_date.isoformat()}")
        print(f"Location: {competition.venue}, {competition.city}")
        print("")

        patrols: List[Patrol] = get_patrols(competition_id=competition_id)

        table_data = []
        for patrol in patrols:
            for signup in patrol.signups:
                if club == signup.spsf_club_number and (card is None or card == signup.shooting_card_number):
                    table_data.append(
                        [
                            signup.shooting_card_number,
                            signup.fullname,
                            signup.weapon_class,
                            patrol.start_time.strftime("%H:%M"),
                            patrol.end_time.strftime("%H:%M"),
                            patrol.number,
                            signup.lane,
                            ", ".join(
                                [
                                    f"{mate.fullname} ({mate.lane})"
                                    for mate in patrol.signups
                                    if mate.spsf_club_number == signup.spsf_club_number
                                    and mate.shooting_card_number != signup.shooting_card_number
                                ]
                            ),
                        ]
                    )

        headers = ["Card", "Name", "Class", "Start", "End", "Patrol", "Lane", "Team Mates"]

        print(tabulate(table_data, headers=headers, tablefmt="simple"))
