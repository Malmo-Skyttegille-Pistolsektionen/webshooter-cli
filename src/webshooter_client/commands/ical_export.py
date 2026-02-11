from typing import List, Optional, TextIO
from datetime import datetime, timezone
from webshooter_client.api.api_calls import get_patrols, get_competition
from webshooter_client.models.competition import Competition, CompetitionType
from webshooter_client.models.patrol import Patrol


class ICalExportCommand:
    """Command to export start times to iCal format."""

    @staticmethod
    def export_starttimes(competition_id: int, club: str, card: Optional[str]) -> None:

        patrols: List[Patrol] = get_patrols(competition_id=competition_id)
        filename: str = f"webshooter_{competition_id}.ical"

        with open(filename, "w") as file:
            ICalExportCommand.write_ical_header(file)

            competition: Competition = get_competition(competition_id=competition_id)

            for patrol in patrols:
                for signup in patrol.signups:
                    if club == signup.spsf_club_number and card is None or card == signup.shooting_card_number:

                        ICalExportCommand.write_ical_event(
                            file=file,
                            competition=competition,
                            signup_id=signup.id,
                            patrol_number=patrol.number,
                            start_time=patrol.start_time,
                            end_time=patrol.end_time,
                            weapon_group=signup.weapon_class,
                            lane=signup.lane,
                        )

            ICalExportCommand.write_ical_footer(file)

        print(f"Start times written to {filename}")

    @staticmethod
    def write_ical_event(
        file: TextIO,
        competition: Competition,
        signup_id: int,
        patrol_number: int,
        start_time: datetime,
        end_time: datetime,
        weapon_group: str,
        lane: int,
    ) -> None:
        file.write("BEGIN:VEVENT\n")
        file.write(f"UID:webshooter_{competition.id}-{signup_id}\n")
        file.write(f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}\n")
        file.write(f"DTSTART;TZID=Europe/Stockholm:{start_time.strftime('%Y%m%dT%H%M%S')}\n")
        file.write(f"DTEND;TZID=Europe/Stockholm:{end_time.strftime('%Y%m%dT%H%M%S')}\n")
        file.write(f"SUMMARY:{competition.name}\n")
        file.write(f"LOCATION:{competition.city}\n")
        file.write("DESCRIPTION:")
        file.write(f"{competition.name}\\n")
        file.write(f"{competition.competition_date}\\n")
        file.write(f"{competition.city}\\n")
        file.write(f"{competition.venue}\\n")
        file.write(f"{competition.type.display_name}\\n")
        file.write("\\n")
        file.write(f"Vapengrupp: {weapon_group}\\n")
        file.write(f"{'Patrull' if competition.type == CompetitionType.FIELD else 'Skjutlag'}: {patrol_number}\\n")
        file.write(f"Plats: {lane}\\n")
        file.write("\\n")
        file.write(
            f"<a href='https://webshooter.se/app/competitions/{competition.id}/information'>Webshooter Info</a>\n"
        )
        file.write("END:VEVENT\n")

    @staticmethod
    def write_ical_header(file: TextIO) -> None:
        file.write("BEGIN:VCALENDAR\n")
        file.write("VERSION:2.0\n")
        file.write("PRODID:-//Webshooter//Pistol//SV\n")
        file.write("CALSCALE:GREGORIAN\n")
        file.write("BEGIN:VTIMEZONE\n")
        file.write("TZID:Europe/Stockholm\n")
        file.write(f"LAST-MODIFIED:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}\n")
        file.write("TZURL:https://www.tzurl.org/zoneinfo-outlook/Europe/Stockholm\n")
        file.write("X-LIC-LOCATION:Europe/Stockholm\n")
        file.write("BEGIN:DAYLIGHT\n")
        file.write("TZOFFSETFROM:+0100\n")
        file.write("TZOFFSETTO:+0200\n")
        file.write("TZNAME:CEST\n")
        file.write("DTSTART:19700329T020000\n")
        file.write("RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=3\n")
        file.write("END:DAYLIGHT\n")
        file.write("BEGIN:STANDARD\n")
        file.write("TZOFFSETFROM:+0200\n")
        file.write("TZOFFSETTO:+0100\n")
        file.write("TZNAME:CET\n")
        file.write("DTSTART:19701025T030000\n")
        file.write("RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=10\n")
        file.write("END:STANDARD\n")
        file.write("END:VTIMEZONE\n")

    @staticmethod
    def write_ical_footer(file: TextIO) -> None:
        file.write("END:VCALENDAR\n")
