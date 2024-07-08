from dataclasses import dataclass
import math
import sys

from webshooter_client.common.application_config import ApplicationConfig
from webshooter_client.common.common import fetch_data


@dataclass(kw_only=True)
class ResultsCommand:
    def get_results(competition, club, card, info_type):
        result = {}

        data = fetch_data(competition=competition, page="results")

        total_points = {}
        std_medals = {}
        total_series = 0

        for first_pass in [True, False]:
            if not first_pass:
                if ApplicationConfig().verbose:
                    print("Poängmetoden Precision:")
                if info_type == "precision" or info_type == "military":
                    for key in total_points:
                        if info_type == "precision":
                            if key == "A":
                                s = 46.1 * total_series
                                b = 44.5 * total_series
                            elif key == "B":
                                s = 47.0 * total_series
                                b = 45.5 * total_series
                            elif key == "C":
                                s = 47.1 * total_series
                                b = 46.0 * total_series
                            elif key in ("M1", "M2", "M3", "M4"):
                                s = 282
                                b = 274
                            elif key == "M5":
                                s = 294
                                b = 288
                            elif key in ("M6", "M7"):
                                s = 270
                                b = 253
                            elif key == "M8":
                                s = 999999
                                b = 999998
                            elif key == "M9":
                                s = 999999
                                b = 999998
                            else:
                                raise Exception(f"Unknown weapon group: {key}")
                        if info_type == "military":
                            if key == "A":
                                s = 540
                                b = 516
                            elif key == "R":
                                s = 552
                                b = 528
                            elif key == "B":
                                s = 561
                                b = 537
                            elif key == "C":
                                s = 564
                                b = 540
                            else:
                                raise Exception(f"Unknown weapon group: {key}")
                        s = math.ceil(s)
                        b = math.ceil(b)
                        if ApplicationConfig().verbose:
                            print(f"{key} S: {s} B: {b}")

                        std_medals[key] = {}
                        std_medals[key]["s"] = s
                        std_medals[key]["b"] = b

                    if ApplicationConfig().verbose:
                        print("Beräkningsmetoden:")
                    for key in total_points:
                        total_points[key].sort(reverse=True)
                        count = len(total_points[key])
                        s = 999999
                        b = 999998
                        if count >= 9:
                            s = math.floor(count / 9)
                            s = total_points[key][s - 1]
                        if count >= 3:
                            b = math.floor(count / 3)
                            b = total_points[key][b - 1]
                        if ApplicationConfig().verbose:
                            print(f"{key}({count}) S: {s} B: {b}")

                        std_medals[key]["s"] = min(std_medals[key]["s"], s)
                        std_medals[key]["b"] = min(std_medals[key]["b"], b)

                    if ApplicationConfig().verbose:
                        print("Använda gränser:")
                        for key in std_medals:
                            print(f"{key} S: {std_medals[key]['s']} B: {std_medals[key]['b']}")

            for results in data["results"]:
                series = 0
                firstname = results["signup"]["user"]["name"]
                lastname = results["signup"]["user"]["lastname"]
                su_card = results["signup"]["user"]["shooting_card_number"]
                name = f"{firstname} {lastname}"
                su_club = (
                    str(results["signup"]["club"]["districts_id"]) + "-" + str(results["signup"]["club"]["clubs_nr"])
                )
                classname = results["weaponclass"]["classname"]
                placement = results["placement"]
                if results["placement"] > 0:
                    group = results["weaponclass"]["classname_general"][0]
                    if group != "C":
                        group = results["weaponclass"]["classname_general"]
                    if total_points.get(group) is None:
                        total_points[group] = []
                    total_points[group].append(results["points"])
                if club == su_club and card is None or card == su_card:
                    precision = results["figure_hits"] == 0 and results["points"] != 0
                    points = results["points"] if precision else f"{results['hits']}/{results['figure_hits']}"

                    if not first_pass:
                        line = f"{classname:<4} : {placement:>2} - {points:<6}"
                        if ApplicationConfig().verbose or not precision:
                            if results["std_medal"] is None:
                                result[su_card]["medals"][results["std_medal"]] += 1
                                line += f"({results['std_medal']}) "
                            else:
                                line += "    "
                        if precision:
                            if points >= std_medals[group]["b"]:
                                if points >= std_medals[group]["s"]:
                                    result[su_card]["medals"]["S"] += 1
                                    line += "(S)"
                                else:
                                    result[su_card]["medals"]["B"] += 1
                                    line += "(B)"
                            else:
                                line += "   "
                        line += " -"
                        first = True
                    for point in results["results"]:
                        series += 1
                        if not first_pass:
                            if not first:
                                line += ","
                                first = False

                            line += (
                                f" {point['points']:>2}" if precision else f" {point['hits']}/{point['figure_hits']}"
                            )

                        if su_card not in result.keys():
                            result[su_card] = {
                                "name": name,
                                "lines": [],
                                "medals": {"B": 0, "S": 0},
                            }
                    if not first_pass:
                        result[su_card]["lines"].append(line)
                if series > total_series:
                    total_series = series

        return result
