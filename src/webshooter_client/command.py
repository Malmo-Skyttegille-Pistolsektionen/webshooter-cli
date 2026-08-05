#!/usr/bin/env python3

from importlib.metadata import version
import logging
import os
import sys

import configargparse

if __package__ is None or len(__package__) == 0:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from webshooter_client.api import api_calls
from webshooter_client.common.application_config import ApplicationConfig
from webshooter_client.commands import (
    bests,
    competitions,
    medals,
    results,
    signups,
    start_times,
    ical_export,
    starts,
    stats,
    sync,
)


class Command:
    __parser: configargparse.ArgumentParser = None

    def _add_argument_version(self, argument_parser: configargparse.ArgumentParser) -> configargparse.ArgumentParser:
        ver: str = "local dev" if (__package__ is None or len(__package__) == 0) else f"{version('webshooter_client')}"
        argument_parser.add_argument("-V", "--version", action="version", version=f"{ver}")
        return argument_parser

    def get_arguments(self) -> configargparse.Namespace:

        self.__parser = configargparse.ArgumentParser(
            default_config_files=[os.path.expanduser("~/.webshooter.rc")],
            description=(
                "Webshooter CLI - Browse Swedish shooting competition data from webshooter.se\n\n"
                "DATA QUERIES:\n"
                "  competitions  - List all competitions (filter by year/type)\n"
                "  signups       - Show shooters registered for a competition\n"
                "  results       - Display competition results and placements\n"
                "  medals        - Count standard medals earned (Silver/Bronze)\n\n"
                "FILTERING & ANALYSIS:\n"
                "  starts        - Count yearly competition participation\n"
                "  starttimes    - Show start times/schedule for a competition\n"
                "  bests         - Display personal best scores by weapon class\n"
                "  stats         - Year-by-year performance analysis with trends\n\n"
                "EXPORT:\n"
                "  ical          - Export competition start times to calendar file\n\n"
                "For detailed help on a command: command.py COMMAND --help"
            ),
            epilog=(
                "\nCOMMON OPTIONS (available on most commands):\n\n"
                "  Filtering by shooter/club:\n"
                "    --card XXXX           Filter by shooting card number (e.g., 12345)\n"
                "    --club XX-XXX         Filter by club (e.g., 12-239)\n\n"
                "  Filtering by year:\n"
                "    --year YYYY           Filter by single year\n"
                "    --years YYYY          Specific years (e.g., --years 2023 2024 2025)\n"
                "    --from YYYY --to YYYY Filter by year range (inclusive)\n"
                "    --all-years           Include all available years\n\n"
                "COMMAND DETAILS:\n\n"
                "  competitions [--year YYYY] [--type {Precision,Military,Fält,Poängfält}]\n"
                "    • Lists all available competitions, searchable by year or competition type\n"
                "    • Useful for finding competition IDs needed for other commands\n\n"
                "  signups <competition_id> [--card XXXX] [--club XX-XXX]\n"
                "    • Shows who is registered for a specific competition\n"
                "    • Can filter to a specific shooter or club\n\n"
                "  results <competition_id> [--card XXXX] [--club XX-XXX]\n"
                "    • Displays scores and placements from a competition\n"
                "    • Can show one shooter's results or all results by club\n\n"
                "  starttimes <competition_id> [--card XXXX] [--club XX-XXX]\n"
                "    • Shows when specific shooters/groups are scheduled to shoot\n"
                "    • Useful for knowing your start time before competition day\n\n"
                "  starts [--card XXXX | --club XX-XXX] [--year YYYY]\n"
                "    • Count yearly competition participation (total competitions shot per year)\n"
                "    • Shows activity level for a shooter or club per year\n\n"
                "  bests <year> [--card XXXX] [--club XX-XXX] [--top N]\n"
                "    • Shows personal best scores for each weapon class\n"
                "    • Weapon classes: Precision (7-series), Military, Field, Point Field\n"
                "    • Scores ranked by points/hits with medal status\n\n"
                "  stats [--card XXXX] [--club XX-XXX] [--year YYYY | --all-years | --from YYYY --to YYYY]\n"
                "    • Year-by-year performance analysis with trends\n"
                "    • Includes averages, deviations from winners, participation counts\n\n"
                "  medals [--card XXXX | --club XX-XXX] [--year YYYY]\n"
                "    • Count total standard medals earned (Silver/Bronze by competition type)\n"
                "    • Shows total medals across all competitions, or filtered by year\n"
                "    • Standard medals: Silver and Bronze (awarded per competition result)\n"
                "    • Useful for tracking achievement and medal progress\n\n"
                "  ical <competition_id> [--card XXXX] [--club XX-XXX] [--output FILE]\n"
                "    • Exports start times to .ics calendar file\n"
                "    • Can be imported into calendar apps (Google, Outlook, Apple, etc.)\n\n"
                "CONFIG FILE FORMAT (~/.webshooter.rc):\n\n"
                "  [global]\n"
                "  token = your_api_token_here\n"
                "  card = 12345\n"
                "  club = 12-239\n"
                "  unicode = true\n"
                "  use_cache = true\n"
                "  cache_dir = /custom/cache/path\n\n"
                "USAGE EXAMPLES:\n\n"
                "  # Find a competition\n"
                "  command.py competitions --year 2024\n\n"
                "  # View results for a specific competition\n"
                "  command.py results 288 --card 12345\n\n"
                "  # Get personal bests for 2024\n"
                "  command.py bests 2024 --card 12345\n\n"
                "  # Count total medals earned\n"
                "  command.py medals --card 12345\n\n"
                "  # Show yearly participation\n"
                "  command.py starts --club 12-239 --all-years\n\n"
                "  # Analyze performance trends\n"
                "  command.py stats --card 12345 --year 2024\n\n"
                "  # Export calendar for competition start times\n"
                "  command.py ical 288 --card 12345 --output my_comp.ics\n\n"
                "CONFIGURATION PRIORITY (highest to lowest):\n"
                "  1. Command-line arguments (override everything)\n"
                "  2. Config file values (~/.webshooter.rc)\n"
                "  3. Built-in defaults"
            ),
            formatter_class=configargparse.RawDescriptionHelpFormatter,
        )

        self._add_argument_version(self.__parser)

        self.__parser.add_argument(
            "--token",
            help="API token from webshooter.se (get from: Browser DevTools → Storage → Local Storage)",
        )
        self.__parser.add_argument(
            "-u", "--unicode", help="Use Unicode table formatting", action="store_true", default=False
        )
        self.__parser.add_argument(
            "-v", "--verbose", help="Enable verbose output and progress messages", action="store_true", default=False
        )
        self.__parser.add_argument(
            "--use-cache",
            help="Use locally cached API responses (faster, no network required)",
            action="store_true",
            default=False,
        )
        self.__parser.add_argument(
            "--cache-dir",
            help="Custom cache directory (default: ~/.cache/webshooter)",
            type=str,
            default=None,
        )
        self.__parser.add_argument(
            "--offline",
            help="Never call the API; use only locally downloaded data (implies --use-cache)",
            action="store_true",
            default=False,
        )
        self.__parser.add_argument(
            "--clear-cache",
            help="Clear all cached data and exit",
            action="store_true",
            default=False,
        )
        self.__parser.add_argument("-c", "--config", is_config_file=True, help="Config file path")

        subparsers = self.__parser.add_subparsers(dest="command", required=False)

        # can specify a particular competion

        parser_signups = subparsers.add_parser(
            "signups",
            help="Show shooters registered for a competition",
        )
        parser_signups.add_argument("competition", help="Competition ID", type=int, default=None)
        self.add_card_and_club(parser_signups)

        parser_starttimes = subparsers.add_parser(
            "starttimes",
            help="Show start times and schedule for a competition",
        )
        parser_starttimes.add_argument("competition", help="Competition ID", type=int, default=None)
        self.add_card_and_club(parser_starttimes)

        parser_ical = subparsers.add_parser(
            "ical",
            help="Export competition start times to an iCal calendar file",
        )
        parser_ical.add_argument("competition", help="Competition ID", type=int, default=None)
        self.add_card_and_club(parser_ical)

        parser_results = subparsers.add_parser(
            "results",
            help="Display competition results (scores and placements)",
        )
        parser_results.add_argument("competition", help="Competition ID", type=int, default=None)
        self.add_card_and_club(parser_results)

        # summaries
        parser_medals = subparsers.add_parser(
            "medals",
            help="Count standard medals earned (Silver/Bronze by competition type)",
        )
        parser_medals.add_argument("year", nargs="?", help="Optional year", type=int)
        self.add_card_and_club(parser_medals)

        parser_starts = subparsers.add_parser(
            "starts",
            help="Count yearly competition participation (by card or club)",
        )
        parser_starts.add_argument("year", nargs="?", help="Optional year", type=int)
        self.add_card_and_club(parser_starts)

        parser_competitions = subparsers.add_parser(
            "competitions",
            help="List all competitions (optionally filtered by year or type)",
        )
        parser_competitions.add_argument("year", nargs="?", help="Optional year", type=int)

        parser_bests = subparsers.add_parser(
            "bests",
            help="Display personal best scores by weapon class (Precision, Military, Field)",
        )
        parser_bests.add_argument("year", help="Year to analyze", type=int)
        parser_bests.add_argument(
            "--top",
            help="Number of top results to show per weapon class (default: 10)",
            type=int,
            default=10,
        )
        parser_bests.add_argument("--card", help="Pistolskyttekort number, e.g. 12345", required=True)

        parser_stats = subparsers.add_parser(
            "stats",
            help="Year-by-year performance analysis with trends and statistics",
        )
        parser_stats.add_argument("--card", help="Pistolskyttekort number, e.g. 12345", required=True)
        parser_stats.add_argument(
            "--competition",
            help="Competition ID for single Field competition analysis (Field-specific, overrides year args)",
            type=int,
            default=None,
        )
        year_group = parser_stats.add_mutually_exclusive_group(required=False)
        year_group.add_argument(
            "--all-years", help="Fetch all available years from 2000 to current year", action="store_true"
        )
        year_group.add_argument(
            "--years",
            help="Specific years to show (e.g., --years 2023 2024 2025)",
            nargs="+",
            type=int,
        )
        year_group.add_argument(
            "--from",
            help="Start year for range (inclusive)",
            type=int,
            dest="from_year",
        )
        parser_stats.add_argument(
            "--to",
            help="End year for range (inclusive)",
            type=int,
            dest="to_year",
        )

        parser_sync = subparsers.add_parser(
            "sync",
            help="Download new competition data into the local store",
        )
        parser_sync.add_argument("--card", help="Pistolskyttekort number, e.g. 12345")
        parser_sync.add_argument(
            "--since",
            help="Start date (YYYY-MM-DD) instead of the automatic watermark",
            type=str,
            default=None,
        )
        parser_sync.add_argument(
            "--full",
            help="Consider every past competition, not just those after the last download",
            action="store_true",
            default=False,
        )
        parser_sync.add_argument(
            "--dry-run",
            help="Show what would be downloaded without downloading anything",
            action="store_true",
            default=False,
        )
        parser_sync.add_argument(
            "--reindex",
            help="Rebuild the index from data already downloaded (no network access)",
            action="store_true",
            default=False,
        )
        parser_sync.add_argument(
            "--limit",
            help="Download at most this many competitions",
            type=int,
            default=None,
        )

        parser_store = subparsers.add_parser(
            "store",
            help="Show what the local store contains (no network access)",
        )
        parser_store.add_argument("--card", help="Pistolskyttekort number, e.g. 12345")

        parser_mcp = subparsers.add_parser(
            "mcp",
            help="Run the MCP server exposing locally downloaded data to AI agents",
        )
        parser_mcp.add_argument("--card", help="Default pistolskyttekort number for MCP tools")
        parser_mcp.add_argument(
            "--transport",
            help="MCP transport (default: stdio)",
            choices=["stdio", "sse", "streamable-http"],
            default="stdio",
        )
        parser_mcp.add_argument("--host", help="Bind host for HTTP transports", default="127.0.0.1")
        parser_mcp.add_argument("--port", help="Bind port for HTTP transports", type=int, default=8000)
        parser_mcp.add_argument(
            "--allow-sync",
            help="Allow the MCP server to download new data (otherwise it is read-only)",
            action="store_true",
            default=False,
        )

        args = self.__parser.parse_args()

        return args

    @staticmethod
    def add_card_and_club(parser: configargparse.ArgumentParser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--club", help="Club number, e.g. 12-239, use 'None' to unset")
        group.add_argument("--card", help="Pistolskyttekort number, e.g. 12345, use 'None' to unset")

    def print_help(self):
        self.__parser.print_help(sys.stderr)


#: Commands that must never trigger a network lookup just to resolve the card.
_NO_CARD_LOOKUP_COMMANDS = {"store", "mcp"}


def _normalize_card_club_args(args):
    """Normalize card and club arguments, handling None values and defaults."""
    if getattr(args, "command", None) in _NO_CARD_LOOKUP_COMMANDS or ApplicationConfig().offline:
        # Looking up the authenticated card requires the API; these paths are
        # expected to work with no network at all.
        return

    # Unset club if user passed --club=None or --club ""
    val = getattr(args, "club", None)
    if isinstance(val, str) and (val.strip().lower() == "none" or val.strip() == ""):
        setattr(args, "club", None)

    # Handle card: fetch authenticated card if not specified, or unset if "none"
    val = getattr(args, "card", None)
    club = getattr(args, "club", None)
    if not isinstance(val, str) and not club:
        setattr(args, "card", api_calls.get_authenticated_shooting_card_number())
    elif isinstance(val, str) and (val.strip().lower() == "none" or val.strip() == ""):
        setattr(args, "card", None)


def _execute_command(command, args):
    """Execute the appropriate command based on args."""
    if command == "signups":
        signups.get_signups(competition_id=args.competition, club=args.club, card=args.card)
    elif command == "starttimes":
        start_times.get_starttimes(competition_id=args.competition, club=args.club, card=args.card)
    elif command == "ical":
        ical_export.export_starttimes(competition_id=args.competition, club=args.club, card=args.card)
    elif command == "results":
        results.get_results_for_competition(competition_id=args.competition, club=args.club, card=args.card)
    elif command == "medals":
        medals.get_medals(club=args.club, card=args.card, year=args.year)
    elif command == "starts":
        starts.get_starts_total(club=args.club, card=args.card, year=args.year)
    elif command == "competitions":
        competitions.get_competitions(year=args.year)
    elif command == "bests":
        bests.get_personal_bests(card=args.card, year=args.year, top_n=args.top)
    elif command == "stats":
        if getattr(args, "competition", None) is not None:
            stats.get_single_field_competition_analysis(
                competition_id=args.competition,
                card=args.card,
            )
        else:
            stats.get_yearly_stats(
                card=args.card,
                years=args.years,
                from_year=args.from_year,
                to_year=getattr(args, "to_year", None),
                all_years=args.all_years,
            )
    elif command == "sync":
        if args.reindex:
            sync.reindex(card=args.card)
        else:
            sync.sync(
                card=args.card,
                since=args.since,
                full=args.full,
                dry_run=args.dry_run,
                limit=args.limit,
            )
    elif command == "store":
        sync.status(card=args.card)
    elif command == "mcp":
        from webshooter_client.mcp.server import start_server

        start_server(
            card=args.card,
            transport=args.transport,
            host=args.host,
            port=args.port,
            allow_sync=args.allow_sync,
        )
    elif command == "exit":
        sys.exit(1)
    else:
        return False
    return True


def main():
    command = Command()
    args = command.get_arguments()

    # Configure logging based on verbose flag
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING, format="%(levelname)s: %(message)s")

    # Initialize config (needed for cache_dir in --clear-cache)
    ApplicationConfig(
        token=args.token,
        unicode=args.unicode,
        verbose=args.verbose,
        # Offline is meaningless without reading the local store.
        use_cache=args.use_cache or args.offline,
        cache_dir=args.cache_dir,
        offline=args.offline,
    )

    # Handle --clear-cache before normal command execution
    if args.clear_cache:
        from webshooter_client.api.cache import clear_cache, _get_cache_dir

        deleted_count = clear_cache()
        cache_dir_display = _get_cache_dir()
        if deleted_count > 0:
            print(f"Cleared {deleted_count} cache file{'s' if deleted_count != 1 else ''} from {cache_dir_display}")
        else:
            print(f"No cache files to clear in {cache_dir_display}")
        sys.exit(0)

    _normalize_card_club_args(args)

    if not _execute_command(args.command, args):
        command.print_help()
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
