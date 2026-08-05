"""Incremental synchronisation of competition data into the local store.

The local store is the on-disk cache written by :mod:`webshooter_client.api.cache`
(``~/.cache/webshooter`` by default). Everything an agent or an offline command
reads comes from there; ``sync`` is the only operation that fills it.

Strategy
--------
The webshooter API has no "changed since" endpoint, so syncing works from the
competition calendar:

1. Re-fetch the competition list from the API (bypassing any cached copy — a
   cached list can never contain competitions published after it was written).
2. Find the most recent competition whose *results* are already downloaded.
   That date is the sync watermark.
3. Download results for every competition on or after the watermark that has
   already taken place and is not downloaded yet. The watermark date itself is
   included so that competitions held on the same day as the last downloaded one
   are not silently skipped.
4. Record, per competition, whether the shooter has a result there — that is
   what makes later offline queries cheap.

``--full`` drops the watermark and considers every past competition, which is
how the store is populated the first time.
"""

import logging
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional

from webshooter_client.api.api_calls import get_competitions, get_results
from webshooter_client.api.cache import (
    get_cache_dir,
    list_cached_competition_ids,
    load_index,
    save_index,
)
from webshooter_client.api.exceptions import WebShooterAPIError
from webshooter_client.common.application_config import ApplicationConfig
from webshooter_client.models.competition import Competition

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, Competition], None]


@dataclass(kw_only=True)
class SyncedCompetition:
    """A competition that was downloaded during a sync run."""

    id: int
    name: str
    competition_date: date
    type: str
    my_weapon_classes: List[str] = field(default_factory=list)

    @property
    def has_my_results(self) -> bool:
        return bool(self.my_weapon_classes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "date": self.competition_date.isoformat(),
            "type": self.type,
            "my_weapon_classes": self.my_weapon_classes,
        }


@dataclass(kw_only=True)
class SyncReport:
    """Outcome of a sync run."""

    cache_dir: str
    card: Optional[str]
    dry_run: bool
    watermark: Optional[date]
    considered: List[Competition] = field(default_factory=list)
    downloaded: List[SyncedCompetition] = field(default_factory=list)
    failed: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def with_my_results(self) -> List[SyncedCompetition]:
        return [c for c in self.downloaded if c.has_my_results]

    @property
    def up_to_date(self) -> bool:
        return not self.considered

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cache_dir": self.cache_dir,
            "card": self.card,
            "dry_run": self.dry_run,
            "up_to_date": self.up_to_date,
            "watermark": self.watermark.isoformat() if self.watermark else None,
            "considered": len(self.considered),
            "downloaded": [c.to_dict() for c in self.downloaded],
            "with_my_results": [c.to_dict() for c in self.with_my_results],
            "failed": self.failed,
        }


@dataclass(kw_only=True)
class LocalStoreStatus:
    """What the local store currently holds — answerable without any network call."""

    cache_dir: str
    competition_count: int
    earliest_date: Optional[date]
    latest_date: Optional[date]
    last_sync: Optional[str]
    card: Optional[str]
    my_competition_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cache_dir": self.cache_dir,
            "competition_count": self.competition_count,
            "earliest_date": self.earliest_date.isoformat() if self.earliest_date else None,
            "latest_date": self.latest_date.isoformat() if self.latest_date else None,
            "last_sync": self.last_sync,
            "card": self.card,
            "my_competition_count": self.my_competition_count,
        }


def _watermark(competitions: Dict[int, Competition], until: date) -> Optional[date]:
    """Date of the most recent competition whose results are already downloaded.

    Competitions dated in the future are ignored: an entry may be cached for one
    that has not been shot yet (an empty results file), and letting that set the
    watermark would push it past every competition still worth downloading.
    """
    cached_ids = list_cached_competition_ids()
    dates = [c.competition_date for cid, c in competitions.items() if cid in cached_ids and c.competition_date <= until]
    return max(dates) if dates else None


def _select_candidates(
    competitions: Dict[int, Competition],
    floor: Optional[date],
    until: date,
) -> List[Competition]:
    """Competitions that have taken place, are not downloaded, and are new enough."""
    cached_ids = list_cached_competition_ids()
    candidates = [
        c
        for c in competitions.values()
        if c.competition_date <= until and c.id not in cached_ids and (floor is None or c.competition_date >= floor)
    ]
    return sorted(candidates, key=lambda c: (c.competition_date, c.id))


def _my_weapon_classes(results: List[Any], card: Optional[str]) -> List[str]:
    """Weapon classes the given card competed in, in the order they appear."""
    if not card:
        return []
    classes: List[str] = []
    for result in results:
        if result.signup.shooting_card_number != card:
            continue
        weapon_class = result.signup.weapon_class
        if weapon_class not in classes:
            classes.append(weapon_class)
    return classes


def _default_progress(current: int, total: int, competition: Competition) -> None:
    print(
        f"\r[{current}/{total}] {competition.competition_date} {competition.name[:60]}...",
        end="",
        flush=True,
        file=sys.stderr,
    )


def sync_competitions(
    card: Optional[str] = None,
    since: Optional[date] = None,
    full: bool = False,
    dry_run: bool = False,
    limit: Optional[int] = None,
    show_progress: bool = True,
    progress_callback: Optional[ProgressCallback] = None,
) -> SyncReport:
    """Download competitions that are missing from the local store.

    Args:
        card: Shooting card number used to record where the shooter has results.
        since: Explicit start date, overriding the automatic watermark.
        full: Ignore the watermark and consider every past competition.
        dry_run: Work out what would be downloaded without fetching or writing.
        limit: Stop after this many competitions (useful for a first, partial run).
        show_progress: Print per-competition progress to stderr.
        progress_callback: Called as ``(current, total, competition)`` instead of
            the default stderr progress line.

    Returns:
        A :class:`SyncReport` describing what was downloaded.
    """
    config = ApplicationConfig()
    if config.offline:
        raise WebShooterAPIError("sync requires network access but offline mode is enabled")

    # Syncing is by definition a cache-populating operation. Reads that hit the
    # cache are exactly the incremental behaviour we want: already-downloaded
    # competitions are never re-fetched.
    config.use_cache = True

    competitions = get_competitions(year=None, force_refresh=True)

    today = date.today()
    watermark = _watermark(competitions, until=today)
    if full:
        floor = None
    elif since is not None:
        floor = since
    else:
        floor = watermark

    candidates = _select_candidates(competitions, floor=floor, until=today)
    if limit is not None:
        candidates = candidates[:limit]

    report = SyncReport(
        cache_dir=str(get_cache_dir()),
        card=card,
        dry_run=dry_run,
        watermark=watermark,
        considered=candidates,
    )

    if dry_run or not candidates:
        return report

    total = len(candidates)
    for position, competition in enumerate(candidates, start=1):
        if progress_callback is not None:
            progress_callback(position, total, competition)
        elif show_progress:
            _default_progress(position, total, competition)

        try:
            results = get_results(competition_id=competition.id)
        except WebShooterAPIError as e:
            # A competition whose results are not published yet is normal, not fatal.
            logger.warning(f"Could not download competition {competition.id}: {e}")
            report.failed.append({"id": competition.id, "name": competition.name, "error": str(e)})
            continue

        report.downloaded.append(
            SyncedCompetition(
                id=competition.id,
                name=competition.name,
                competition_date=competition.competition_date,
                type=competition.type.display_name,
                my_weapon_classes=_my_weapon_classes(results, card),
            )
        )

    if show_progress and progress_callback is None:
        print(file=sys.stderr)

    _update_index(report)

    return report


def _update_index(report: SyncReport) -> None:
    """Merge a sync run's findings into the persistent index."""
    index = load_index()
    competitions: Dict[str, Any] = index.get("competitions", {})

    for synced in report.downloaded:
        competitions[str(synced.id)] = synced.to_dict()

    index["competitions"] = competitions
    index["last_sync"] = datetime.now().isoformat(timespec="seconds")
    if report.card:
        index["card"] = report.card

    save_index(index)


def reindex_local_store(
    card: Optional[str] = None,
    show_progress: bool = True,
) -> SyncReport:
    """Rebuild the index from what is already on disk, without any network call.

    A store populated before the index existed — or synced under a different
    card — has no record of which competitions the shooter has results in.
    Reindexing reads every downloaded competition once so that later queries can
    open only the relevant files.
    """
    config = ApplicationConfig()
    config.use_cache = True

    competitions = get_competitions(year=None)
    cached_ids = list_cached_competition_ids()
    targets = sorted(
        (c for cid, c in competitions.items() if cid in cached_ids),
        key=lambda c: (c.competition_date, c.id),
    )

    report = SyncReport(
        cache_dir=str(get_cache_dir()),
        card=card,
        dry_run=False,
        watermark=_watermark(competitions, until=date.today()),
        considered=targets,
    )

    total = len(targets)
    for position, competition in enumerate(targets, start=1):
        if show_progress:
            _default_progress(position, total, competition)
        try:
            results = get_results(competition_id=competition.id)
        except WebShooterAPIError as e:
            logger.warning(f"Could not read competition {competition.id} from the local store: {e}")
            report.failed.append({"id": competition.id, "name": competition.name, "error": str(e)})
            continue

        report.downloaded.append(
            SyncedCompetition(
                id=competition.id,
                name=competition.name,
                competition_date=competition.competition_date,
                type=competition.type.display_name,
                my_weapon_classes=_my_weapon_classes(results, card),
            )
        )

    if show_progress:
        print(file=sys.stderr)

    _update_index(report)

    return report


def get_local_store_status(card: Optional[str] = None) -> LocalStoreStatus:
    """Describe the local store without touching the network.

    Falls back to the raw cache files for competitions downloaded before the
    index existed, so a store populated by an older version still reports
    sensible counts.
    """
    index = load_index()
    competitions: Dict[str, Any] = index.get("competitions", {})
    known_card = card or index.get("card")

    dates = [date.fromisoformat(c["date"]) for c in competitions.values() if c.get("date")]
    my_count = sum(1 for c in competitions.values() if c.get("my_weapon_classes"))

    # Competitions on disk but not in the index still count towards the total.
    cached_ids = list_cached_competition_ids()
    total = len(cached_ids | {int(cid) for cid in competitions})

    return LocalStoreStatus(
        cache_dir=str(get_cache_dir()),
        competition_count=total,
        earliest_date=min(dates) if dates else None,
        latest_date=max(dates) if dates else None,
        last_sync=index.get("last_sync"),
        card=known_card,
        my_competition_count=my_count,
    )
