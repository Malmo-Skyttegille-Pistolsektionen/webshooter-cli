"""Queries answered entirely from the local store.

Every function here is safe to call with ``ApplicationConfig(offline=True)``: it
reads only competitions that have already been downloaded and never falls back
to the network. Results are returned as plain JSON-friendly dictionaries so that
the CLI, the MCP server and any script can share the same code.

Competitions that are missing from the local store are skipped rather than
fetched. Use ``sync`` to fill the gaps.
"""

import logging
from collections import defaultdict
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Sequence

from webshooter_client.api.api_calls import get_competition, get_competitions, get_results
from webshooter_client.api.cache import is_cached, list_cached_competition_ids, load_index
from webshooter_client.api.exceptions import WebShooterAPIError
from webshooter_client.common.competition_filter import (
    get_field_result_figures,
    get_field_result_hits,
    get_field_result_points,
    get_result_points,
)
from webshooter_client.models.competition import Competition, CompetitionType
from webshooter_client.models.result import FieldResult, PrecisionResult, ResultBase, SeriesResult
from webshooter_client.stats.calculator import get_weapon_group

logger = logging.getLogger(__name__)


class UnknownCompetitionTypeError(ValueError):
    """Raised when a caller passes a competition type that does not exist."""


def resolve_competition_types(names: Optional[Sequence[str]]) -> Optional[set[CompetitionType]]:
    """Turn user-supplied type names into CompetitionType values.

    Accepts both the API value ("military") and the Swedish display name
    ("Militär snabbmatch"), case-insensitively, because agents and humans reach
    for different ones.
    """
    if not names:
        return None

    by_value = {t.value.lower(): t for t in CompetitionType}
    by_display = {t.display_name.lower(): t for t in CompetitionType}

    resolved: set[CompetitionType] = set()
    for name in names:
        key = name.strip().lower()
        competition_type = by_value.get(key) or by_display.get(key)
        if competition_type is None:
            valid = sorted({t.value for t in CompetitionType} | {t.display_name for t in CompetitionType})
            raise UnknownCompetitionTypeError(f"Unknown competition type {name!r}. Valid values: {', '.join(valid)}")
        resolved.add(competition_type)
    return resolved


def competition_to_dict(competition: Competition) -> Dict[str, Any]:
    """Serialise a competition for transport to an agent."""
    return {
        "id": competition.id,
        "name": competition.name,
        "date": competition.competition_date.isoformat(),
        "type": competition.type.display_name,
        "type_value": competition.type.value,
        "city": competition.city,
        "venue": competition.venue,
    }


def _series_to_dict(series: Sequence[SeriesResult]) -> List[Dict[str, int]]:
    return [{"points": s.points, "inner_tens": s.inner_tens} for s in series]


def result_to_dict(result: ResultBase, competition: Optional[Competition] = None) -> Dict[str, Any]:
    """Serialise a single result, flattening the shooter and competition context.

    ``points`` is the comparable score as used by bests/stats (for Precision this
    is the sum of the seven base series, which excludes finals); ``raw_points``
    is whatever the API reported.
    """
    data: Dict[str, Any] = {
        "card": result.signup.shooting_card_number,
        "name": result.signup.fullname,
        "club": result.signup.spsf_club_number,
        "weapon_class": result.signup.weapon_class,
        "weapon_group": get_weapon_group(result.signup.weapon_class),
        "placement": result.placement,
        "points": get_result_points(result),
        "raw_points": result.points,
        "std_medal": result.std_medal.display_name if result.std_medal else None,
        "calculated_std_medal": (result.calculated_std_medal.display_name if result.calculated_std_medal else None),
    }

    if isinstance(result, FieldResult):
        data.update(
            {
                "hits": get_field_result_hits(result),
                "figure_hits": get_field_result_figures(result),
                "station_points": get_field_result_points(result),
                "stations": [
                    {"hits": s.hits, "figure_hits": s.figure_hits, "points": s.points} for s in result.stations
                ],
            }
        )
    else:
        series = getattr(result, "series", [])
        data.update(
            {
                "series": _series_to_dict(series),
                "inner_tens": sum(s.inner_tens for s in series),
                "series_count": len(series),
                "is_comparable": data["points"] is not None,
            }
        )
        if isinstance(result, PrecisionResult):
            # Finals are stored outside `series`, so a gap here means a final was shot.
            data["finals_points"] = (
                result.points - data["points"] if data["points"] is not None else None  # type: ignore[operator]
            )

    if competition is not None:
        data["competition"] = competition_to_dict(competition)

    return data


def downloaded_competitions(
    year: Optional[int] = None,
    competition_types: Optional[set[CompetitionType]] = None,
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
) -> List[Competition]:
    """Competitions present in the local store, newest last.

    Only competitions whose results have been downloaded are returned — those are
    the only ones any statistic can be computed from.
    """
    cached_ids = list_cached_competition_ids()
    all_competitions = get_competitions(year=None)

    selected: List[Competition] = []
    for competition_id, competition in all_competitions.items():
        if competition_id not in cached_ids:
            continue
        competition_year = competition.competition_date.year
        if year is not None and competition_year != year:
            continue
        if from_year is not None and competition_year < from_year:
            continue
        if to_year is not None and competition_year > to_year:
            continue
        if competition_types is not None and competition.type not in competition_types:
            continue
        selected.append(competition)

    return sorted(selected, key=lambda c: (c.competition_date, c.id))


def _indexed_ids_for_card(card: str) -> Optional[set[int]]:
    """Competition IDs the index says this card has results in.

    Returns None when the index cannot answer for this card, in which case the
    caller must fall back to scanning every downloaded competition.
    """
    index = load_index()
    if not index.get("competitions") or index.get("card") != card:
        return None
    return {int(cid) for cid, entry in index["competitions"].items() if entry.get("my_weapon_classes")}


def _iter_results(competitions: Iterable[Competition]):
    """Yield (competition, results) for each competition, skipping unreadable ones."""
    for competition in competitions:
        if not is_cached(f"competition_{competition.id}_results"):
            continue
        try:
            yield competition, get_results(competition_id=competition.id)
        except WebShooterAPIError as e:
            logger.warning(f"Skipping competition {competition.id}: {e}")


def my_results(
    card: str,
    year: Optional[int] = None,
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
    competition_types: Optional[set[CompetitionType]] = None,
    comparable_only: bool = False,
) -> List[Dict[str, Any]]:
    """Every downloaded result for one shooter, oldest first.

    Args:
        card: Shooting card number.
        year / from_year / to_year: Optional year filters.
        competition_types: Optional set of competition types to include.
        comparable_only: Drop results that cannot be compared against others
            (e.g. Precision competitions that were not shot over seven series).
    """
    competitions = downloaded_competitions(
        year=year, competition_types=competition_types, from_year=from_year, to_year=to_year
    )

    # The index lets us open only the files that can contain the shooter.
    indexed = _indexed_ids_for_card(card)
    if indexed is not None:
        competitions = [c for c in competitions if c.id in indexed]

    collected: List[Dict[str, Any]] = []
    for competition, results in _iter_results(competitions):
        for result in results:
            if result.signup.shooting_card_number != card:
                continue
            data = result_to_dict(result, competition)
            if comparable_only and data.get("points") is None:
                continue
            collected.append(data)

    return collected


def personal_bests(
    card: str,
    year: Optional[int] = None,
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
    competition_types: Optional[set[CompetitionType]] = None,
    top: int = 5,
) -> Dict[str, List[Dict[str, Any]]]:
    """Best downloaded results per competition type and weapon class.

    With no year filter this is an all-time personal best across everything in
    the local store. Keys look like ``"Militär snabbmatch - C3"``; each value is
    a list of results, best first.

    Field and Poängfält results are ranked by hits, everything else by points.
    """
    results = my_results(
        card,
        year=year,
        from_year=from_year,
        to_year=to_year,
        competition_types=competition_types,
        comparable_only=True,
    )

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for result in results:
        key = f"{result['competition']['type']} - {result['weapon_class']}"
        grouped[key].append(result)

    ranked: Dict[str, List[Dict[str, Any]]] = {}
    for key, entries in sorted(grouped.items()):
        entries.sort(
            key=lambda r: (
                r.get("hits") if r.get("hits") is not None else r["points"],
                r.get("figure_hits", 0),
                r.get("inner_tens", 0),
            ),
            reverse=True,
        )
        ranked[key] = entries[:top]

    return ranked


def competition_results(
    competition_id: int,
    card: Optional[str] = None,
    club: Optional[str] = None,
) -> Dict[str, Any]:
    """Full result table for one downloaded competition, optionally filtered.

    Raises:
        WebShooterAPIError: If the competition has not been downloaded.
    """
    if not is_cached(f"competition_{competition_id}_results"):
        raise WebShooterAPIError(
            f"Competition {competition_id} is not in the local store. Run 'wscli sync' to download it."
        )

    competition = get_competition(competition_id)
    results = get_results(competition_id=competition_id)

    filtered = []
    for result in results:
        if card and result.signup.shooting_card_number != card:
            continue
        if club and result.signup.spsf_club_number != club:
            continue
        filtered.append(result_to_dict(result))

    filtered.sort(key=lambda r: (r["weapon_class"], r["placement"]))

    return {
        "competition": competition_to_dict(competition),
        "result_count": len(filtered),
        "results": filtered,
    }


def participation_summary(card: str) -> Dict[str, Any]:
    """How many downloaded competitions the shooter has results in, per year and type."""
    results = my_results(card)

    by_year: Dict[int, int] = defaultdict(int)
    by_type: Dict[str, int] = defaultdict(int)
    competitions_seen: set[int] = set()

    for result in results:
        competition = result["competition"]
        if competition["id"] in competitions_seen:
            continue
        competitions_seen.add(competition["id"])
        by_year[date.fromisoformat(competition["date"]).year] += 1
        by_type[competition["type"]] += 1

    return {
        "card": card,
        "competitions": len(competitions_seen),
        "starts": len(results),
        "by_year": dict(sorted(by_year.items())),
        "by_type": dict(sorted(by_type.items())),
    }
