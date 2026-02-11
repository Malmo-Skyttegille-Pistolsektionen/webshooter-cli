from typing import List, Optional
from webshooter_client.api.api_calls import get_patrols, get_competition
from webshooter_client.models.competition import Competition
from webshooter_client.models.patrol import Patrol
from webshooter_client.common.output_utils import print_competition_header, matches_club_and_card
from webshooter_client.commands.base_command import BaseCommand


class StartTimesCommand(BaseCommand):
    """Command to display start times for a competition."""

    @staticmethod
    def get_starttimes(competition_id: int, club: str, card: Optional[str]) -> None:

        competition: Competition = get_competition(competition_id=competition_id)
        print_competition_header(competition)

        patrols: List[Patrol] = get_patrols(competition_id=competition_id)

        table_data = []
        for patrol in patrols:
            for signup in patrol.signups:
                if matches_club_and_card(signup, club, card):
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
        BaseCommand.print_table(table_data, headers)
