#!/usr/bin/env python3

from importlib.metadata import version
import os
import sys

import configargparse

if __package__ is None or len(__package__) == 0:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from webshooter_client.commands.competition_list import CompetitionsListCommand
from webshooter_client.common.application_config import ApplicationConfig
from webshooter_client.commands.medals import MedalsCommand
from webshooter_client.commands.results import ResultsCommand
from webshooter_client.commands.signups import SignupsCommand
from webshooter_client.commands.start_times import StartTimesCommand
from webshooter_client.commands.starts import StartsCommand
from webshooter_client.common.common import get_info, print_info, print_result
from webshooter_client.gui.webshooter_gui_urwid import WebShooterGUI


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
        self.__parser.add_argument("--name", help="Name")
        self.__parser.add_argument("--club", help="Club, use 'None' to unset")
        self.__parser.add_argument("--card", help="Card, use 'None' to unset")
        self.__parser.add_argument("-u", "--unicode", help="Unicode", action="store_true", default=False)
        self.__parser.add_argument("-v", "--verbose", help="Verbose", action="store_true", default=False)
        self.__parser.add_argument("-c", "--config", is_config_file=True, help="Config file path")

        subparsers = self.__parser.add_subparsers(dest="command", required=True)

        parser_starttimes = subparsers.add_parser(
            "starttimes",
            help="List start times for a competition",
        )
        parser_starttimes.add_argument("competition", help="Competition ID", type=int, default=None)

        parser_ical = subparsers.add_parser(
            "ical",
            help="Save start times for a competition (in ical format) to webshooter.ical",
        )
        parser_ical.add_argument("competition", help="Competition ID", type=int, default=None)

        parser_results = subparsers.add_parser(
            "results",
            help="List results from a competition",
        )
        parser_results.add_argument("competition", help="Competition ID", type=int, default=None)

        parser_signups = subparsers.add_parser(
            "signups",
            help="List signups for a competition",
        )
        parser_signups.add_argument("competition", help="Competition ID", type=int, default=None)

        parser_medals = subparsers.add_parser(
            "medals",
            help="List standard medals awarded for a card",
        )
        parser_medals.add_argument("year", nargs="?", help="Optional year", type=int)

        parser_starts = subparsers.add_parser(
            "starts",
            help="List total starts from a club",
        )
        parser_starts.add_argument("year", nargs="?", help="Optional year", type=int)

        parser_competitions = subparsers.add_parser(
            "competitions",
            help="List all competitions in webshooter",
        )
        parser_competitions.add_argument("year", nargs="?", help="Optional year", type=int)

        parser_competitions = subparsers.add_parser(
            "ui",
            help="Run UI",
        )

        args = self.__parser.parse_args()

        return args

    def print_help(self):
        self.__parser.print_help(sys.stderr)


def main():
    command = Command()

    args = command.get_arguments()

    # Unset card/club if user passed --card=None or --card ""
    for key in ("club", "card"):
        val = getattr(args, key, None)
        if isinstance(val, str) and (val.strip().lower() == "none" or val.strip() == ""):
            setattr(args, key, None)

    # # Unset any argument if user passed --arg=None or --arg ""
    # for key, val in vars(args).items():
    #     if isinstance(val, str) and (val.strip().lower() == "none" or val.strip() == ""):
    #         setattr(args, key, None)

    ApplicationConfig(token=args.token, club=args.club, card=args.card, unicode=args.unicode, verbose=args.verbose)

    if args.command == "ui":
        args_for_gui = WebShooterGUI.run(ApplicationConfig())
        if args_for_gui is None:
            sys.exit(1)
        args = configargparse.Namespace(**args_for_gui)

    exit_code: int = 0

    info = None
    result = None

    if args.command == "signups":
        info = get_info(competition=args.competition)
        result = SignupsCommand.get_signups(competition=args.competition, club=args.club, card=args.card)
    elif args.command == "starttimes":
        info = get_info(competition=args.competition)
        result = StartTimesCommand.get_starttimes(
            info=info, competition=args.competition, club=args.club, card=args.card
        )
    elif args.command == "ical":
        info = get_info(competition=args.competition)
        result = StartTimesCommand.get_starttimes(
            info=info, competition=args.competition, club=args.club, card=args.card, ical=True
        )
    elif args.command == "results":
        info = get_info(competition=args.competition)
        result = ResultsCommand.get_results(
            competition=args.competition, club=args.club, card=args.card, info_type=info["type"]
        )
    elif args.command == "medals":
        result = MedalsCommand.get_medals(club=args.club, card=args.card, year=args.year)
    elif args.command == "starts":
        result = StartsCommand.get_starts_total(club=args.club, card=args.card, year=args.year)
    elif args.command == "competitions":
        result = CompetitionsListCommand.get_competitions(year=args.year)
    elif args.command == "exit":
        sys.exit(1)
    else:
        command.print_help()
        sys.exit(1)

    print("")
    print_info(club=args.club, info=info)
    print_result(result=result)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
