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
)
from webshooter_client.models.patrol import Patrol
from webshooter_client.models.signup import Signup
from webshooter_client.api.exceptions import (
    APIConnectionError,
    APITimeoutError,
    APIServerError,
    APIClientError,
    APIRetryExhaustedError,
)
from webshooter_client.api.cache import (
    load_from_cache,
    save_to_cache,
    get_cache_key_for_competitions,
    get_cache_key_for_competition,
    get_cache_key_for_page,
)

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

    Raises:
        DataValidationError: If response data is missing required fields
    """
    from webshooter_client.api.exceptions import DataValidationError

    logging.info(f"Fetching competition: {competition_id}")
    url = BASE_URL_COMPETITION.format(competition=competition_id)

    data = fetch_data(url=url, cache_key=get_cache_key_for_competition(competition_id))

    if "competitions" not in data or data["competitions"] is None:
        raise DataValidationError(f"No competition data in response for ID {competition_id}")

    competition = data["competitions"]

    # Validate required fields
    required_fields = ["id", "name", "date", "results_type"]
    missing_fields = [field for field in required_fields if field not in competition]
    if missing_fields:
        raise DataValidationError(f"Missing required competition fields: {', '.join(missing_fields)}")

    competition_obj: Competition = Competition(
        id=competition["id"],
        name=competition["name"],
        competition_date=date.fromisoformat(competition["date"]),
        type=CompetitionType(competition["results_type"]),
        city=competition.get("contact_city", "Unknown"),
        venue=competition.get("contact_venue", "Unknown"),
        signups_close=(
            date.fromisoformat(competition["signups_closing_date"]) if competition.get("signups_closing_date") else None
        ),
    )

    return competition_obj


def get_competitions(year: Optional[int]) -> dict[int, Competition]:
    """
    Fetch all competitions, optionally filtered by year.

    Note: The API returns all competitions in one call. The year parameter
    only filters the results client-side. The cache stores all competitions
    regardless of the year parameter.

    Args:
        year: Optional year to filter competitions (e.g., 2024)

    Returns:
        Dictionary mapping competition IDs to Competition objects
    """
    competitions: dict[int, Competition] = {}

    logging.info("Fetching competitions")
    url = BASE_URL_COMPETITIONS

    # Cache key is year-agnostic since API returns all competitions
    data = fetch_data(url=url, cache_key=get_cache_key_for_competitions())

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

    data = fetch_data(url=url, cache_key=get_cache_key_for_page(competition_id, "patrols"))

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
    from webshooter_client.api.result_parsers import ResultParserFactory

    logging.info(f"Fetching competition results for {competition_id}")
    url = BASE_URL_COMPETITION_PAGE.format(competition=competition_id, page="results")

    competition = get_competition(competition_id)
    data = fetch_data(url=url, cache_key=get_cache_key_for_page(competition_id, "results"))

    # Get appropriate parser for this competition type
    parser = ResultParserFactory.get_parser(competition.type)

    results: List[PrecisionResult | MilitaryResult | FieldResult] = []
    for result in data.get("results", []):
        # Skip results with no signup data (can happen in older competitions)
        if result.get("signup") is None:
            logging.warning(f"Skipping result for competition {competition_id}: missing signup data")
            continue

        result["signup"]["weaponclass"] = result["weaponclass"]
        signup_obj: Signup = create_signup_obj(result["signup"])
        results.append(parser.parse(result, signup_obj))

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

    data = fetch_data(url=url, cache_key=get_cache_key_for_page(competition_id, "signups?page=1&per_page=1000"))

    signup_objs: List[Signup] = []

    for signup in data["signups"]["data"]:
        signup_obj: Signup = create_signup_obj(signup)

        signup_objs.append(signup_obj)

    return signup_objs


def fetch_data(  # noqa: C901
    url: str, cache_key: Optional[str] = None, max_retries: int = 5, backoff_factor: int = 10
) -> Dict[str, Any]:
    """
    Fetch JSON data from the WebShooter API with retry logic and optional caching.

    Automatically adds authentication headers and retries on HTTP 500 errors
    with exponential backoff. If cache is enabled and cache_key is provided,
    will try to load from cache first, and save successful responses to cache.

    Args:
        url: The API endpoint URL to fetch
        cache_key: Optional cache identifier for saving/loading cached data
        max_retries: Maximum number of retry attempts on HTTP 500 (default: 5)
        backoff_factor: Seconds to multiply by retry count for backoff (default: 10)

    Returns:
        Parsed JSON response as dictionary

    Raises:
        APIConnectionError: On network connection errors
        APITimeoutError: On request timeout
        APIServerError: On HTTP 5xx errors after retries
        APIClientError: On HTTP 4xx errors
        APIRetryExhaustedError: If max retries exceeded
    """
    # Try loading from cache first
    if cache_key:
        cached_data = load_from_cache(cache_key)
        if cached_data is not None:
            return cached_data

    headers = HEADERS.copy()
    headers["Authorization"] = f"Bearer {ApplicationConfig().token}"

    logging.info(f"Fetching from: {url}")

    retries = 0
    last_error = None

    while retries < max_retries:
        try:
            response = requests.get(url, headers=headers, timeout=30)

            # Handle HTTP response codes explicitly
            if response.status_code == 200:
                data = json.loads(response.text)
                # Save to cache if cache_key provided
                if cache_key:
                    save_to_cache(cache_key, data)
                return data
            elif response.status_code == 500:
                retries += 1
                wait_time = backoff_factor * retries
                logging.warning(f"HTTP 500 Error from {url}. Retry {retries}/{max_retries} in {wait_time}s...")
                time.sleep(wait_time)
                last_error = APIServerError("Server returned HTTP 500", url=url, status_code=500)
            elif 400 <= response.status_code < 500:
                raise APIClientError(
                    f"Client error: {response.status_code} - {response.text}", url=url, status_code=response.status_code
                )
            else:
                raise APIServerError(
                    f"Unexpected status code: {response.status_code} - {response.text}",
                    url=url,
                    status_code=response.status_code,
                )

        except requests.exceptions.Timeout as e:
            raise APITimeoutError(f"Request timed out: {e}", url=url)
        except requests.exceptions.ConnectionError as e:
            raise APIConnectionError(f"Connection failed: {e}", url=url)
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed for {url}: {e}")
            raise APIConnectionError(f"Request failed: {e}", url=url)

    # If we exit the loop, retries were exhausted
    raise APIRetryExhaustedError(
        f"Failed to fetch URL after {max_retries} retries. Last error: {last_error}", url=url, retries=max_retries
    )


def create_signup_obj(signup: Dict[str, Any]) -> Signup:
    """Create a Signup object from API response data.

    Args:
        signup: Raw signup data from API

    Returns:
        Signup object

    Raises:
        DataValidationError: If required fields are missing or invalid
    """
    from webshooter_client.api.exceptions import DataValidationError

    # Validate required fields exist
    required_fields = ["id", "club", "user", "weaponclass"]
    missing_fields = [field for field in required_fields if field not in signup or signup[field] is None]
    if missing_fields:
        raise DataValidationError(f"Missing required signup fields: {', '.join(missing_fields)}")

    # Validate nested required fields
    if "districts_id" not in signup["club"] or "clubs_nr" not in signup["club"]:
        raise DataValidationError("Missing club identification fields (districts_id or clubs_nr)")

    if "fullname" not in signup["user"]:
        raise DataValidationError("Missing user fullname in signup")

    if "classname" not in signup["weaponclass"] or "classname_general" not in signup["weaponclass"]:
        raise DataValidationError("Missing weapon class fields in signup")

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
