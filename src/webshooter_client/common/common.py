import json
import time
import unicodedata
from typing import Any, Dict, Optional, Union

import requests

from webshooter_client.common.application_config import ApplicationConfig


def printable(string: str) -> str:
    if ApplicationConfig().unicode:
        string = unicodedata.normalize("NFKD", string)
        string = "".join([c for c in string if not unicodedata.combining(c)])
    return string


def get_info(competition: int) -> Dict[str, Union[str, int]]:
    info: Dict[str, Union[str, int]] = {}
    data = fetch_data(competition=competition)

    info["id"] = competition
    info["name"] = data["competitions"]["name"]
    info["city"] = data["competitions"]["contact_city"]
    info["venue"] = data["competitions"]["contact_venue"]
    info["date"] = data["competitions"]["date"]
    info["signups_close"] = data["competitions"]["signups_closing_date"]
    info["type"] = data["competitions"]["results_type"]

    return info


def print_info(club: str, info: Optional[Dict[str, Union[str, int]]]) -> None:
    if not info:
        return

    print(printable(string=f"{info['name']} - {info['city']} - {info['venue']}"))
    print(f"Date {info['date']}")
    print(f"Type {info['type']}")
    print("")
    print(f"Webshooter id {info['id']}")
    print(f"Signup closing date {info['signups_close']}")
    print("")
    print(f"Club: {club}")
    print("")


def print_result(result: Optional[Dict[int, Any]]) -> None:
    if not result:
        return

    for card, card_info in result.items():
        if card != 0 and "lines" in card_info:
            for line in card_info["lines"]:
                name = printable(string=card_info["name"])
                print(f"{name:<20} - {line}")

    if 0 in result and "lines" in result[0]:
        for line in result[0]["lines"]:
            print(f"{line}")

    if 0 in result and "info" in result[0]:
        for line in result[0]["info"]:
            print(f"{line}")


def infotype_to_string(infotype: str) -> str:
    return {
        "field": "Fält",
        "precision": "Precision",
        "military": "Militär snabbmatch",
    }.get(infotype, "Okänd")


def command_to_string(mode: str) -> str:
    return {
        "signups": "Anmälda",
        "starttimes": "Starttider",
        "ical": "Starttider med ical filer",
        "results": "Resultat",
        "medals": "Standardmedaljer",
        "starts": "Starter",
        "competitions": "Tävlingar",
        "ui": "UI",
    }.get(mode, "Okänd")


def fetch_data(
    competition: Optional[int] = None, page: Optional[str] = None, max_retries: int = 5, backoff_factor: int = 10
) -> Dict[str, Any]:
    BASE_URL_COMP = "https://webshooter.se/api/v4.1.9/competitions?page=1&per_page=1000&status=all&type=0"
    BASE_URL_BASE = "https://webshooter.se/api/v4.1.9/competitions/{competition}"
    BASE_URL_PAGE = "https://webshooter.se/api/v4.1.9/competitions/{competition}/{page}"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:97.0) Gecko/20100101 Firefox/97.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "X-Requested-With": "XMLHttpRequest",
        "DNT": "1",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    headers = HEADERS.copy()
    headers["Authorization"] = f"Bearer {ApplicationConfig().token}"

    if competition is None:
        print("Fetching competitions")
        url = BASE_URL_COMP
    elif page is None:
        print(f"Fetching competition: {competition}")
        url = BASE_URL_BASE.format(competition=competition)
    else:
        print(f"Fetching {page.split('?')[0]}")
        url = BASE_URL_PAGE.format(competition=competition, page=page)

    retries = 0
    while retries < max_retries:
        try:
            response = requests.get(url, headers=headers)

            # Handle HTTP response codes explicitly
            if response.status_code == 200:
                return json.loads(response.text)
            elif response.status_code == 500:
                retries += 1
                wait_time = backoff_factor * retries
                print(f"HTTP 500 Error. Retrying {retries}/{max_retries} in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Unexpected HTTP status code: {response.status_code}. Response: {response.text}")
                response.raise_for_status()  # Optional: Re-raise for unexpected errors
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            raise e

    raise Exception(f"Failed to fetch the URL after {max_retries} retries")
