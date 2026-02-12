"""Export start times to iCal format command."""

from typing import List, Optional
from datetime import datetime
from icalendar import Calendar, Event
from zoneinfo import ZoneInfo
from webshooter_client.api.api_calls import get_patrols, get_competition
from webshooter_client.models.competition import Competition, CompetitionType
from webshooter_client.models.patrol import Patrol
from webshooter_client.common.output_utils import matches_club_and_card


def export_starttimes(competition_id: int, club: str, card: Optional[str] = None) -> None:
    """Export start times to iCal format file.

    Args:
        competition_id: ID of the competition
        club: Club number to filter by
        card: Optional shooting card number to filter by
    """
    patrols: List[Patrol] = get_patrols(competition_id=competition_id)
    competition: Competition = get_competition(competition_id=competition_id)
    filename: str = f"webshooter_{competition_id}.ical"

    cal = Calendar()
    cal.add("prodid", "-//Webshooter//Pistol//SV")
    cal.add("version", "2.0")

    stockholm_tz = ZoneInfo("Europe/Stockholm")

    for patrol in patrols:
        for signup in patrol.signups:
            if matches_club_and_card(signup, club, card):
                event = Event()
                event.add("uid", f"webshooter_{competition.id}-{signup.id}")
                event.add("dtstamp", datetime.now())
                event.add("dtstart", patrol.start_time.replace(tzinfo=stockholm_tz))
                event.add("dtend", patrol.end_time.replace(tzinfo=stockholm_tz))
                event.add("summary", competition.name)
                event.add("location", competition.city)
                event.add(
                    "description", _format_description(competition, signup.weapon_class, patrol.number, signup.lane)
                )
                cal.add_component(event)

    with open(filename, "wb") as file:
        file.write(cal.to_ical())

    print(f"Start times written to {filename}")


def _format_description(competition: Competition, weapon_group: str, patrol_number: int, lane: int) -> str:
    """Format event description with competition details."""
    patrol_label = "Patrull" if competition.type == CompetitionType.FIELD else "Skjutlag"
    return (
        f"{competition.name}\n"
        f"{competition.competition_date}\n"
        f"{competition.city}\n"
        f"{competition.venue}\n"
        f"{competition.type.display_name}\n"
        f"\n"
        f"Vapengrupp: {weapon_group}\n"
        f"{patrol_label}: {patrol_number}\n"
        f"Plats: {lane}\n"
        f"\n"
        f"https://webshooter.se/app/competitions/{competition.id}/information"
    )
