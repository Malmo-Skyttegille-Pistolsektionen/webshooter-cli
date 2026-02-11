from typing import Dict, List

from webshooter_client.api.api_calls import get_competition, get_signups
from webshooter_client.models.competition import Competition
from webshooter_client.models.signup import Signup
from webshooter_client.common.output_utils import print_competition_header, matches_club_and_card
from webshooter_client.commands.base_command import BaseCommand


class SignupsCommand(BaseCommand):
    """Command to display signups for a competition."""

    @staticmethod
    def get_signups(competition_id: int, club: str, card: int) -> None:  # noqa: C901
        result: Dict[int, Dict[str, object]] = {}

        competition: Competition = get_competition(competition_id=competition_id)
        print_competition_header(competition)

        signups: List[Signup] = get_signups(competition_id=competition_id)

        counter_all_starts_in_weaponclasses: Dict[str, int] = {}
        counter_club_starts_in_weaponclasses: Dict[str, int] = {}

        for signup in signups:
            counter_all_starts_in_weaponclasses[signup.weapon_class_general] = (
                counter_all_starts_in_weaponclasses.get(signup.weapon_class_general, 0) + 1
            )

            if matches_club_and_card(signup, club, card):

                counter_club_starts_in_weaponclasses[signup.weapon_class_general] = (
                    counter_club_starts_in_weaponclasses.get(signup.weapon_class_general, 0) + 1
                )

                card_number = signup.shooting_card_number
                if card_number not in result:
                    result[card_number] = {
                        "card": card_number,
                        "name": signup.fullname,
                        "classes": set(),
                        "patrol_mates": list(),
                    }
                result[card_number]["classes"].add(signup.weapon_class)

                if signup.share_patrol_with:
                    mate = next(
                        (mate for mate in signups if mate.shooting_card_number == signup.share_patrol_with), None
                    )
                    if mate:
                        result[card_number]["patrol_mates"].append(f"{mate.fullname} ({mate.weapon_class})")
                    else:
                        result[card_number]["patrol_mates"].append(str(signup.share_patrol_with))

        # Build table data signups
        table_data = []
        for card_number in sorted(result.keys()):
            signup_data = result[card_number]
            classes_str = ", ".join(sorted(signup_data["classes"]))
            patrol_mates_str = ", ".join(sorted(signup_data["patrol_mates"]))
            table_data.append([signup_data["card"], signup_data["name"], classes_str, patrol_mates_str])

        headers = ["Card", "Name", "Classes", "Patrol Mates"]
        BaseCommand.print_table(table_data, headers)

        BaseCommand.print_section_separator()

        # Create table for signups per weapon class
        signups_stats_table_data = []
        all_classes = sorted(
            set(counter_all_starts_in_weaponclasses.keys()) | set(counter_club_starts_in_weaponclasses.keys())
        )

        total_club = 0
        total_all = 0
        for weapon_class in all_classes:
            all_count = counter_all_starts_in_weaponclasses.get(weapon_class, 0)
            club_count = counter_club_starts_in_weaponclasses.get(weapon_class, 0)
            signups_stats_table_data.append([weapon_class, club_count, all_count])
            total_club += club_count
            total_all += all_count

        # Add total row
        signups_stats_table_data.append(["Total", total_club, total_all])

        stats_headers = ["Weapon Class", f"Club {club}", "All"]
        BaseCommand.print_table(signups_stats_table_data, stats_headers)
