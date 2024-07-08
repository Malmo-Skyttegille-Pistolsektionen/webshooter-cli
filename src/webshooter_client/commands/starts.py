from dataclasses import dataclass

from webshooter_client.commands.competition_list import CompetitionsListCommand
from webshooter_client.commands.results import ResultsCommand
from webshooter_client.common.common import get_info


@dataclass(kw_only=True)
class StartsCommand:
    def get_starts_total(club, card, year=None):
        result = {}
        total = 0

        competitions = CompetitionsListCommand.get_competitions_list(year=year)

        for competition in competitions.keys():
            info = get_info(competition=competition)
            results = ResultsCommand.get_results(competition=competition, club=club, card=card, info_type=info["type"])

            if info["type"] not in result:
                result[info["type"]] = {}
                result[info["type"]]["results"] = 0

            print(f"Datum: {competitions[competition]['date']} ID: {competition} Typ: {info['type']}")

            for card in results.keys():
                if card != 0:
                    for line in results[card]["lines"]:
                        result[info["type"]]["results"] += 1
                        total += 1

        print(f"Club: {club}")
        print(f"Year: {year}")
        print("")
        print(f"Total starts during {year}: {total}")
        print("")

        for type in result.keys():
            print(f"{type}: {result[type]['results']}")

        return None
