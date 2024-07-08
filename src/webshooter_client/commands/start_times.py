from dataclasses import dataclass
import time

from webshooter_client.common.common import fetch_data, infotype_to_string


@dataclass(kw_only=True)
class StartTimesCommand:
    @staticmethod
    def get_starttimes(info, competition, club, card, ical=False):
        result = {}

        data = fetch_data(competition=competition, page="patrols")
        filename = f"webshooter_{competition}.ical"
        file = None

        if ical:
            file = open(filename, "w")
            StartTimesCommand.write_ical_header(file)

        for patrol in data["patrols"]:
            start_time = patrol["start_time_human"]
            end_time = patrol["end_time_human"]
            patrol_number = patrol["sortorder"]

            for signup in patrol["signups"]:
                su_club = f"{signup['club']['districts_id']}-{signup['club']['clubs_nr']}"
                su_card = signup["user"]["shooting_card_number"]

                if club == su_club and card is None or card == su_card:
                    user_info = signup["user"]
                    name = f"{user_info['name']} {user_info['lastname']}"
                    class_name = signup["weaponclass"]["classname"]
                    weapon_group = signup["weaponclass"]["classname_general"]
                    lane = signup["lane"]

                    if su_card not in result:
                        result[su_card] = {"name": name, "lines": []}

                    result[su_card]["lines"].append(
                        f"{class_name:<4} : Patrol {patrol_number:<2} ({start_time} - {end_time}) : Lane {lane}"
                    )

                    if ical:
                        StartTimesCommand.write_ical_event(
                            file,
                            info,
                            result[su_card]["lines"],
                            patrol_number,
                            start_time,
                            end_time,
                            weapon_group,
                            lane,
                        )

        if ical:
            StartTimesCommand.write_ical_footer(file)
            file.close()
            if 0 not in result:
                result[0] = {"info": []}
            result[0]["info"].append(f"Start times written to {filename}")

        return result

    @staticmethod
    def write_ical_header(file):
        file.write("BEGIN:VCALENDAR\n")
        file.write("VERSION:2.0\n")
        file.write("PRODID:-//Webshooter//Pistol//SV\n")
        file.write("CALSCALE:GREGORIAN\n")
        file.write("BEGIN:VTIMEZONE\n")
        file.write("TZID:Europe/Stockholm\n")
        file.write(f"LAST-MODIFIED:{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}\n")
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
    def write_ical_event(file, info, lines, patrol_number, start_time, end_time, weapon_group, lane):
        file.write("BEGIN:VEVENT\n")
        file.write(f"UID:webshooter_{info['id']}-{len(lines)}\n")
        file.write(f"DTSTAMP:{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}\n")
        file.write(f"DTSTART;TZID=Europe/Stockholm:{info['date'].replace('-', '')}T{start_time.replace(':', '')}00Z\n")
        file.write(f"DTEND;TZID=Europe/Stockholm:{info['date'].replace('-', '')}T{end_time.replace(':', '')}00Z\n")
        file.write(f"SUMMARY:{info['name']}\n")
        file.write(f"LOCATION:{info['city']}\n")
        file.write("DESCRIPTION:")
        file.write(f"{info['name']}\\n")
        file.write(f"{info['date']}\\n")
        file.write(f"{info['city']}\\n")
        file.write(f"{info['venue']}\\n")
        file.write(f"{infotype_to_string(info['type'])}\\n")
        file.write("\\n")
        file.write(f"Vapengrupp: {weapon_group}\\n")
        file.write(f"{'Patrull' if info['type'] == 'field' else 'Skjutlag'}: {patrol_number}\\n")
        file.write(f"Plats: {lane}\\n")
        file.write("\\n")
        file.write(f"<a href='https://webshooter.se/app/competitions/{info['id']}/information'>Webshooter Info</a>\n")
        file.write("END:VEVENT\n")

    @staticmethod
    def write_ical_footer(file):
        file.write("END:VCALENDAR\n")
