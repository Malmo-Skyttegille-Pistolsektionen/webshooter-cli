"""MCP server exposing the locally downloaded webshooter data to AI agents.

Design
------
The server is a thin adapter over :mod:`webshooter_client.services.local_query`
and :mod:`webshooter_client.sync` — the same code the CLI uses. No statistics
logic is reimplemented here.

It runs **offline by default**: :class:`ApplicationConfig` is put in offline mode
so that no tool can silently reach the webshooter API, which keeps agent
exploration fast, private and free of rate limits. Only the ``sync_local_store``
tool touches the network, and only when the server was started with
``--allow-sync``.

Run it with::

    wscli mcp --card 12345 --allow-sync

and register that command as an MCP server in your agent's configuration.
"""

import logging
from typing import Any, Dict, List, Literal, Optional

from webshooter_client.api.exceptions import WebShooterAPIError
from webshooter_client.common.application_config import ApplicationConfig
from webshooter_client.services import local_query
from webshooter_client.sync import get_local_store_status, reindex_local_store, sync_competitions

logger = logging.getLogger(__name__)

SERVER_NAME = "webshooter"


def start_server(  # noqa: C901
    card: Optional[str] = None,
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
    allow_sync: bool = False,
) -> None:
    """Run the MCP server.

    Args:
        card: Default shooting card number, so agents can omit it in every call.
        transport: MCP transport to serve on.
        host: Bind host, used by the HTTP transports.
        port: Bind port, used by the HTTP transports.
        allow_sync: Register the network-touching sync tool.
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise ImportError("MCP server requires extra dependencies: pip install 'webshooter-client[mcp]'") from exc

    config = ApplicationConfig()
    config.use_cache = True
    config.offline = True

    default_card = card or get_local_store_status().card

    mcp = FastMCP(SERVER_NAME)
    mcp.settings.host = host
    mcp.settings.port = port
    if transport == "streamable-http":
        mcp.settings.json_response = True
        mcp.settings.stateless_http = True

    def _card(value: Optional[str]) -> str:
        resolved = value or default_card
        if not resolved:
            raise ValueError("No shooting card number available. Pass card=... or start the server with --card.")
        return resolved

    def _types(competition_type: Optional[str]):
        return local_query.resolve_competition_types([competition_type] if competition_type else None)

    @mcp.tool()
    def local_store_status() -> Dict[str, Any]:
        """Describe the locally downloaded data: how many competitions, which date range,
        when it was last synced, and how many contain the shooter's own results.
        Call this first — every other read-only tool can only see what is listed here.
        If the latest date is older than the competitions you are asked about, run
        sync_local_store (if available) or tell the user to run 'wscli sync'."""
        return get_local_store_status(card=default_card).to_dict()

    @mcp.tool()
    def list_competitions(
        year: Optional[int] = None,
        competition_type: Optional[str] = None,
        only_mine: bool = False,
        card: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List downloaded competitions, oldest first, with their IDs and dates.
        competition_type accepts either the Swedish name ('Militär snabbmatch', 'Precision',
        'Fält', 'Poängfält') or the API value ('military', 'precision', 'field', 'pointfield').
        Set only_mine=True to list just the competitions the shooter has results in."""
        competitions = local_query.downloaded_competitions(year=year, competition_types=_types(competition_type))
        listed = [local_query.competition_to_dict(c) for c in competitions]

        if not only_mine:
            return listed

        mine = {r["competition"]["id"] for r in local_query.my_results(_card(card), year=year)}
        return [c for c in listed if c["id"] in mine]

    @mcp.tool()
    def get_competition_results(
        competition_id: int,
        card: Optional[str] = None,
        club: Optional[str] = None,
        mine_only: bool = False,
    ) -> Dict[str, Any]:
        """Full result table for one competition: placements, points, medals and the
        individual series (Precision/Militär snabbmatch) or stations (Fält).
        By default every shooter is returned; set mine_only=True for just the shooter's
        own rows, or pass club='12-239' to filter to a club."""
        return local_query.competition_results(
            competition_id,
            card=_card(card) if mine_only else None,
            club=club,
        )

    @mcp.tool()
    def get_my_results(
        year: Optional[int] = None,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
        competition_type: Optional[str] = None,
        card: Optional[str] = None,
        comparable_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Every downloaded result for one shooter, oldest first, each with its competition.
        This is the raw material for statistics: one entry per weapon class per competition,
        including points, inner tens (Xs) and the full series or station breakdown.
        'points' is the comparable score (for Precision the sum of the seven base series,
        which excludes finals); 'raw_points' is what the API reported.
        comparable_only=True drops results that cannot be compared, such as Precision
        competitions not shot over seven series."""
        return local_query.my_results(
            _card(card),
            year=year,
            from_year=from_year,
            to_year=to_year,
            competition_types=_types(competition_type),
            comparable_only=comparable_only,
        )

    @mcp.tool()
    def get_personal_bests(
        year: Optional[int] = None,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
        competition_type: Optional[str] = None,
        card: Optional[str] = None,
        top: int = 5,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Best results per competition type and weapon class, best first.
        With no year filter this is the all-time personal best across everything downloaded.
        Keys look like 'Militär snabbmatch - C3'. Precision and Militär snabbmatch are
        ranked by points then inner tens; Fält and Poängfält by hits then figure hits."""
        return local_query.personal_bests(
            _card(card),
            year=year,
            from_year=from_year,
            to_year=to_year,
            competition_types=_types(competition_type),
            top=top,
        )

    @mcp.tool()
    def get_participation_summary(card: Optional[str] = None) -> Dict[str, Any]:
        """How many downloaded competitions the shooter has results in, broken down by
        year and by competition type. Useful for a quick overview before drilling in."""
        return local_query.participation_summary(_card(card))

    if allow_sync:

        @mcp.tool()
        def sync_local_store(
            card: Optional[str] = None,
            full: bool = False,
            dry_run: bool = False,
            limit: Optional[int] = None,
        ) -> Dict[str, Any]:
            """Download competitions that are missing from the local store. This is the only
            tool that uses the network, and it can be slow (the API is rate limited and
            frequently returns transient errors that are retried).
            It finds the most recent competition already downloaded and fetches everything
            held on or after that date that is not downloaded yet.
            Use dry_run=True first to see what would be fetched, full=True to reconsider
            every past competition, and limit=N to cap a long first run.
            After it returns, the read-only tools see the new data immediately."""
            resolved_card = _card(card)
            config.offline = False
            try:
                report = sync_competitions(
                    card=resolved_card,
                    full=full,
                    dry_run=dry_run,
                    limit=limit,
                    show_progress=False,
                )
            except WebShooterAPIError as e:
                raise ValueError(f"Sync failed: {e}") from e
            finally:
                config.offline = True

            return report.to_dict()

        @mcp.tool()
        def reindex_store(card: Optional[str] = None) -> Dict[str, Any]:
            """Rebuild the index of which competitions contain the shooter's results, reading
            only data already on disk. Run this once after switching to a different card, or
            if local_store_status reports far fewer of the shooter's competitions than expected."""
            report = reindex_local_store(card=_card(card), show_progress=False)
            return {
                "indexed": len(report.downloaded),
                "considered": len(report.considered),
                "with_my_results": len(report.with_my_results),
                "failed": report.failed,
            }

    logger.info(
        "Starting webshooter MCP server (transport=%s, host=%s, port=%s, card=%s, sync=%s)",
        transport,
        host,
        port,
        default_card,
        allow_sync,
    )
    mcp.run(transport=transport)
