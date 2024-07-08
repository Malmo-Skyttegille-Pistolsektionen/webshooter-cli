from dataclasses import dataclass
import time

from webshooter_client.commands.competition_list import CompetitionsListCommand
from webshooter_client.commands.results import ResultsCommand
from webshooter_client.common.application_config import ApplicationConfig
from webshooter_client.common.common import get_info, printable


@dataclass(kw_only=True)
class MedalsCommand:
    def get_medals(club, card, year: int):
        medals = {}

        competitions = CompetitionsListCommand.get_competitions_list(year=year)
        for competition in competitions.keys():
            info = get_info(competition=competition)
            results = ResultsCommand.get_results(competition=competition, club=club, card=card, info_type=info["type"])
            for card in results.keys():
                if card != 0:
                    if results[card]["medals"]["S"] != 0 or results[card]["medals"]["B"] != 0:
                        if not info["type"] in medals:
                            medals[info["type"]] = {
                                "S": 0,
                                "B": 0,
                                "type_readable": competitions[competition]["type_readable"],
                            }

                        print(printable(string=f"{info['name']} - {info['city']} - {info['venue']}"))
                        print(f"Medals: B: {results[card]['medals']['B']} S: {results[card]['medals']['S']}")
                        if ApplicationConfig().verbose:
                            for line in results[card]["lines"]:
                                name = printable(results[card]["name"])
                                print(f"{name:<20} - {line}")

                        medals[info["type"]]["S"] += results[card]["medals"]["S"]
                        medals[info["type"]]["B"] += results[card]["medals"]["B"]
            time.sleep(1)

        print("")
        print("")
        print(f"Card: {card}")
        print("")
        for type in medals.keys():
            print(f"{medals[type]['type_readable']:<20} S: {medals[type]['S']} B: {medals[type]['B']}")
        print("---")
        s = sum(m["S"] for m in medals.values() if m)
        b = sum(m["B"] for m in medals.values() if m)
        print(f"{'Total':<20} S: {s} B: {b}")

        return None
