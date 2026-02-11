from typing import Any, Dict, List, Optional

import logging
import requests
import time
import json


from webshooter_client.common.application_config import ApplicationConfig
from webshooter_client.models.competition import Competition, CompetitionType
from webshooter_client.models.result import (
    PrecisionResult,
    MilitaryResult,
    FieldResult,
    SeriesResult,
    StationResult,
    ResultBase,
    StdMedal,
)
from webshooter_client.models.patrol import Patrol
from webshooter_client.models.signup import Signup

from datetime import datetime, date


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

BASE_URL_COMPETITIONS = "https://webshooter.se/api/v4.1.9/competitions?page=1&per_page=1000&status=all&type=0"
BASE_URL_COMPETITION = "https://webshooter.se/api/v4.1.9/competitions/{competition}"
BASE_URL_COMPETITION_PAGE = "https://webshooter.se/api/v4.1.9/competitions/{competition}/{page}"


def get_competition(competition_id: int) -> Competition:
    """
    Fetch a single competition by its ID from the WebShooter API.
    
    Args:
        competition_id: The unique identifier for the competition
        
    Returns:
        Competition object with details about the competition
    """
    logging.info(f"Fetching competition: {competition_id}")
    url = BASE_URL_COMPETITION.format(competition=competition_id)

    data = fetch_data(url=url)

    competition = data["competitions"]

    competition_obj: Competition = Competition(
        id=competition["id"],
        name=competition["name"],
        competition_date=date.fromisoformat(competition["date"]),
        type=CompetitionType(competition["results_type"]),
        city=competition["contact_city"],
        venue=competition["contact_venue"],
        signups_close=date.fromisoformat(competition["signups_closing_date"]),
    )

    return competition_obj


def get_competitions(year: Optional[int]) -> dict[int, Competition]:
    """
    Fetch all competitions, optionally filtered by year.
    
    Args:
        year: Optional year to filter competitions (e.g., 2024)
        
    Returns:
        Dictionary mapping competition IDs to Competition objects
    """
    competitions: dict[int, Competition] = {}

    logging.info("Fetching competitions")
    url = BASE_URL_COMPETITIONS

    data = fetch_data(url=url)

    for competition in data["competitions"]["data"]:
        if not year or competition["date"].startswith(str(year)):
            competition_obj = Competition(
                id=competition["id"],
                name=competition["name"],
                competition_date=date.fromisoformat(competition["date"]),
                type=CompetitionType(competition["results_type"]),
                city=competition["contact_city"],
                venue=competition["contact_venue"],
                signups_close=date.fromisoformat(competition["signups_closing_date"]),
            )

            competitions[competition_obj.id] = competition_obj

    return competitions


def get_patrols(competition_id: int) -> List[Patrol]:
    """
    Fetch all patrols for a specific competition.
    
    Args:
        competition_id: The unique identifier for the competition
        
    Returns:
        List of Patrol objects with start times and participant signups
    """
    logging.info(f"Fetching competion patrols for {competition_id}")
    url = BASE_URL_COMPETITION_PAGE.format(competition=competition_id, page="patrols")

    data = fetch_data(url=url)

    patrol_objs: List[Patrol] = []

    for patrol in data["patrols"]:
        signup_objs: List[Signup] = []

        for signup in patrol["signups"]:
            signup_obj: Signup = create_signup_obj(signup)

            signup_objs.append(signup_obj)

        patrol_obj = Patrol(
            id=patrol["id"],
            start_time=datetime.fromisoformat(patrol["start_time"]),
            end_time=datetime.fromisoformat(patrol["end_time"]),
            number=patrol["sortorder"],
            signups=signup_objs,
        )

        patrol_objs.append(patrol_obj)

    return patrol_objs


def get_results(competition_id: int) -> List[PrecisionResult | MilitaryResult | FieldResult]:
    """
    Fetch all results for a specific competition.
    
    Args:
        competition_id: The unique identifier for the competition
        
    Returns:
        List of result objects (type depends on competition type: Precision, Military, or Field)
    """
    logging.info(f"Fetching competition results for {competition_id}")
    url = BASE_URL_COMPETITION_PAGE.format(competition=competition_id, page="results")

    competition = get_competition(competition_id)

    data = fetch_data(url=url)

    results: List[PrecisionResult | MilitaryResult | FieldResult] = []
    for result in data.get("results", []):
        result["signup"]["weaponclass"] = result["weaponclass"]
        signup_obj: Signup = create_signup_obj(result["signup"])
        base_kwargs = {
            "signup": signup_obj,
            "placement": int(result["placement"]),
            "std_medal": StdMedal(result["std_medal"]) if result.get("std_medal") else None,
            "points": int(result.get("points", -1)),
        }

        if base_kwargs["points"] == -1:
            logging.warning(f"Result for {base_kwargs['fullname']} has invalid points value: -1")

        if competition.type == CompetitionType.PRECISION:
            series = [SeriesResult(points=s["points"], inner_tens=s.get("hits")) for s in result.get("results", [])]
            results.append(PrecisionResult(**base_kwargs, series=series))
        elif competition.type == CompetitionType.MILITARY:
            series = [SeriesResult(points=s["points"], inner_tens=s.get("hits")) for s in result.get("results", [])]
            results.append(MilitaryResult(**base_kwargs, series=series))
        elif competition.type == CompetitionType.FIELD:
            stations = [
                StationResult(hits=st.get("hits", 0), figure_hits=st.get("figure_hits"), points=st.get("points"))
                for st in result.get("results", [])
            ]
            results.append(FieldResult(**base_kwargs, stations=stations))
        else:
            results.append(ResultBase(**base_kwargs))

    return results


def get_signups(competition_id: int) -> List[Signup]:
    """
    Fetch all signups for a specific competition.
    
    Args:
        competition_id: The unique identifier for the competition
        
    Returns:
        List of Signup objects representing all participants registered for the competition
    """
    logging.info(f"Fetching competition signups for {competition_id}")
    url = BASE_URL_COMPETITION_PAGE.format(competition=competition_id, page="signups?page=1&per_page=1000")

    data = fetch_data(url=url)

    signup_objs: List[Signup] = []

    for signup in data["signups"]["data"]:
        signup_obj: Signup = create_signup_obj(signup)

        signup_objs.append(signup_obj)

    return signup_objs


def fetch_data(url: str, max_retries: int = 5, backoff_factor: int = 10) -> Dict[str, Any]:
    """
    Fetch JSON data from the WebShooter API with retry logic.
    
    Automatically adds authentication headers and retries on HTTP 500 errors
    with exponential backoff.
    
    Args:
        url: The API endpoint URL to fetch
        max_retries: Maximum number of retry attempts on HTTP 500 (default: 5)
        backoff_factor: Seconds to multiply by retry count for backoff (default: 10)
        
    Returns:
        Parsed JSON response as dictionary
        
    Raises:
        requests.exceptions.RequestException: On network or request errors
        Exception: If max retries exceeded
    """
    headers = HEADERS.copy()
    headers["Authorization"] = f"Bearer {ApplicationConfig().token}"

    logging.info(f"Fetching from: {url}")

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


def create_signup_obj(signup: Dict[str, Any]) -> Signup:
    """Create a Signup object from API response data."""
    signup_obj: Signup = Signup(
        id=signup["id"],
        spsf_club_number=f"{signup['club']['districts_id']}-{signup['club']['clubs_nr']}",
        shooting_card_number=(
            "".join(signup["user"]["shooting_card_number"].split())
            if signup["user"]["shooting_card_number"] is not None
            and signup["user"]["shooting_card_number"].strip() != ""
            else None
        ),
        fullname=signup["user"]["fullname"],
        lane=signup["lane"],
        weapon_class=signup["weaponclass"]["classname"],
        weapon_class_general=signup["weaponclass"]["classname_general"][0],
        share_patrol_with=signup["share_patrol_with"],
    )

    return signup_obj


def get_authenticated_shooting_card_number() -> str:
    """
    Fetch the authenticated user's shooting_card_number from the WebShooter API.
    """
    url = "https://webshooter.se/api/v4.1.9/authenticate/user"
    data = fetch_data(url)

    return data["user"]["shooting_card_number"]
