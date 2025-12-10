#!/usr/bin/env python3

from importlib.metadata import version
import os
import sys

import configargparse


if __package__ is None or len(__package__) == 0:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from webshooter_client.api import api_calls
from webshooter_client.common.application_config import ApplicationConfig
from webshooter_client.commands.competitions import CompetitionsCommand
from webshooter_client.commands.medals import MedalsCommand
from webshooter_client.commands.results import ResultsCommand
from webshooter_client.commands.signups import SignupsCommand
from webshooter_client.commands.start_times import StartTimesCommand
from webshooter_client.commands.ical_export import ICalExportCommand
from webshooter_client.commands.starts import StartsCommand


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
        self.__parser.add_argument("-c", "--config", is_config_file=True, help="Config file path")

        subparsers = self.__parser.add_subparsers(dest="command", required=True)

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

        args = self.__parser.parse_args()

        return args

    @staticmethod
    def add_card_and_club(parser: configargparse.ArgumentParser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--club", help="Club number, e.g. 12-239, use 'None' to unset")
        group.add_argument("--card", help="Pistolskyttekort number, e.g. 12345, use 'None' to unset")

    def print_help(self):
        self.__parser.print_help(sys.stderr)


def main():
    command = Command()

    args = command.get_arguments()

    ApplicationConfig(token=args.token, unicode=args.unicode, verbose=args.verbose)

    # Unset card/club if user passed --card=None or --card ""
    # specifically for club
    val = getattr(args, "club", None)
    if isinstance(val, str) and (val.strip().lower() == "none" or val.strip() == ""):
        setattr(args, "club", None)

    # specifically for card
    val = getattr(args, "card", None)
    if not isinstance(val, str) and not args.club:
        setattr(args, "card", api_calls.get_authenticated_shooting_card_number())
    elif isinstance(val, str) and (val.strip().lower() == "none" or val.strip() == ""):
        setattr(args, "card", None)

    # can specify a particular competion
    if args.command == "signups":
        SignupsCommand.get_signups(competition_id=args.competition, club=args.club, card=args.card)
    elif args.command == "starttimes":
        StartTimesCommand.get_starttimes(competition_id=args.competition, club=args.club, card=args.card)
    elif args.command == "ical":
        ICalExportCommand().export_starttimes(competition_id=args.competition, club=args.club, card=args.card)
    elif args.command == "results":
        ResultsCommand.get_results_for_competition(competition_id=args.competition, club=args.club, card=args.card)

    # summaries
    elif args.command == "medals":
        MedalsCommand.get_medals(club=args.club, card=args.card, year=args.year)
    elif args.command == "starts":
        StartsCommand.get_starts_total(club=args.club, card=args.card, year=args.year)

    elif args.command == "competitions":
        CompetitionsCommand.get_competitions(year=args.year)
    elif args.command == "exit":
        sys.exit(1)
    else:
        command.print_help()
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
