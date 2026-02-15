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
            description="Webshooter CLI tool",
            formatter_class=configargparse.ArgumentDefaultsRawHelpFormatter,
        )

        self._add_argument_version(self.__parser)

        self.__parser.add_argument(
            "--token",
            help="web token, copy from Browser -> Developer Tools -> Storage -> Local Storage -> token",
        )
        self.__parser.add_argument("-u", "--unicode", help="Unicode", action="store_true", default=False)
        self.__parser.add_argument("-v", "--verbose", help="Verbose", action="store_true", default=False)
        self.__parser.add_argument(
            "--use-cache",
            help="Use local file cache instead of making API calls",
            action="store_true",
            default=False,
        )
        self.__parser.add_argument(
            "--cache-dir",
            help="Cache directory path (default: $XDG_CACHE_HOME/webshooter or ~/.cache/webshooter)",
            type=str,
            default=None,
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
            help="List signups for a competition",
        )
        parser_signups.add_argument("competition", help="Competition ID", type=int, default=None)
        self.add_card_and_club(parser_signups)

        parser_starttimes = subparsers.add_parser(
            "starttimes",
            help="List start times for a competition",
        )
        parser_starttimes.add_argument("competition", help="Competition ID", type=int, default=None)
        self.add_card_and_club(parser_starttimes)

        parser_ical = subparsers.add_parser(
            "ical",
            help="Save start times for a competition to an iCal file",
        )
        parser_ical.add_argument("competition", help="Competition ID", type=int, default=None)
        self.add_card_and_club(parser_ical)

        parser_results = subparsers.add_parser(
            "results",
            help="List results from a competition",
        )
        parser_results.add_argument("competition", help="Competition ID", type=int, default=None)
        self.add_card_and_club(parser_results)

        # summaries
        parser_medals = subparsers.add_parser(
            "medals",
            help="List standard medals awarded for a card",
        )
        parser_medals.add_argument("year", nargs="?", help="Optional year", type=int)
        self.add_card_and_club(parser_medals)

        parser_starts = subparsers.add_parser(
            "starts",
            help="List total starts from a club",
        )
        parser_starts.add_argument("year", nargs="?", help="Optional year", type=int)
        self.add_card_and_club(parser_starts)

        parser_competitions = subparsers.add_parser(
            "competitions",
            help="List all competitions in webshooter",
        )
        parser_competitions.add_argument("year", nargs="?", help="Optional year", type=int)

        parser_bests = subparsers.add_parser(
            "bests",
            help="Display personal best results in Precision and Military competitions",
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
            help="Display year-by-year statistics and trends",
        )
        parser_stats.add_argument("--card", help="Pistolskyttekort number, e.g. 12345", required=True)
        year_group = parser_stats.add_mutually_exclusive_group(required=True)
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

        args = self.__parser.parse_args()

        return args

    @staticmethod
    def add_card_and_club(parser: configargparse.ArgumentParser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--club", help="Club number, e.g. 12-239, use 'None' to unset")
        group.add_argument("--card", help="Pistolskyttekort number, e.g. 12345, use 'None' to unset")

    def print_help(self):
        self.__parser.print_help(sys.stderr)


def _normalize_card_club_args(args):
    """Normalize card and club arguments, handling None values and defaults."""
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
        stats.get_yearly_stats(
            card=args.card,
            years=args.years,
            from_year=args.from_year,
            to_year=args.to_year,
            all_years=args.all_years,
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
        use_cache=args.use_cache,
        cache_dir=args.cache_dir,
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
