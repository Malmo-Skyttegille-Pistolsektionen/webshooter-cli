import unicodedata
from typing import Any, Dict, Optional

from webshooter_client.common.application_config import ApplicationConfig


def printable(string: str) -> str:
    if ApplicationConfig().unicode:
        string = unicodedata.normalize("NFKD", string)
        string = "".join([c for c in string if not unicodedata.combining(c)])
    return string


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
