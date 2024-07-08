from dataclasses import dataclass

from webshooter_client.common.common import fetch_data


@dataclass(kw_only=True)
class SignupsCommand:
    def get_signups(competition: int, club: str, card: int):
        result = {}

        data = fetch_data(competition=competition, page="signups?page=1&per_page=1000")

        weaponclasses = {}
        signup_count = 0

        for signup in data["signups"]["data"]:
            weaponclass = signup["weaponclass"]["classname_general"]
            if weaponclass in ["CD", "CVY", "CVÄ"]:
                weaponclass = "C"
            firstname = signup["user"]["name"]
            lastname = signup["user"]["lastname"]
            su_card = signup["user"]["shooting_card_number"]
            name = f"{firstname} {lastname}"
            su_club = str(signup["club"]["districts_id"]) + "-" + str(signup["club"]["clubs_nr"])
            if weaponclass not in weaponclasses:
                weaponclasses[weaponclass] = 0
            weaponclasses[weaponclass] += 1

            if club == su_club and card is None or card == su_card:
                classname = signup["weaponclass"]["classname"]
                share_patrol = signup["share_patrol_with"]
                same_patrol_as = None
                signup_count += 1
                if share_patrol != 0:
                    same_patrol_as = share_patrol
                    for user in data["signups"]["data"]:
                        if user["user"]["shooting_card_number"] == f"{share_patrol}":
                            same_patrol_as = f"{user['user']['name']} {user['user']['lastname']}"
                if su_card not in result.keys():
                    result[su_card] = {"name": name, "lines": []}
                if same_patrol_as is None:
                    result[su_card]["lines"].append(f"{classname:<4}")
                else:
                    result[su_card]["lines"].append(f"{classname:<4} - {same_patrol_as}")

        result[0] = {"name": su_club, "lines": []}
        result[0]["lines"].append("")
        result[0]["lines"].append(f"Total from {su_club}: {signup_count}")
        result[0]["lines"].append("")
        result[0]["lines"].append("Total signups in weapon classes:")
        for key in sorted(weaponclasses):
            result[0]["lines"].append(f"{key}: {weaponclasses[key]}")

        return result
