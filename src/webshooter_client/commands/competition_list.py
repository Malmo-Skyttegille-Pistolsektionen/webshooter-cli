from dataclasses import dataclass
import re

from webshooter_client.common.common import fetch_data, printable


@dataclass(kw_only=True)
class CompetitionsListCommand:
    @staticmethod
    def get_competitions_list(year: int):
        result = {}

        data = fetch_data()

        for competition in data["competitions"]["data"]:
            if re.match(f"^{year}-", competition["date"]) or year is None:
                result[competition["id"]] = {}
                result[competition["id"]]["name"] = competition["name"]
                result[competition["id"]]["date"] = competition["date"]
                result[competition["id"]]["type"] = competition["results_type"]
                result[competition["id"]]["type_readable"] = printable(string=competition["results_type_human"])

        return result

    @staticmethod
    def get_competitions(year: int):
        competitions = CompetitionsListCommand.get_competitions_list(year=year)

        print(f"Total: {len(competitions)}")
        for competition in competitions.keys():
            print(
                f"Datum: {competitions[competition]['date']} ID: {competition:5} Typ: {competitions[competition]['type_readable']}"
            )

        return None
