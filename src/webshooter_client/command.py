#!/usr/bin/python3

import argparse
from importlib.metadata import version
import os
import sys


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
from webshooter_client.common.webshooter_rc import WebShooterRC


class Command:
    __parser: argparse.ArgumentParser = None

    def _add_argument_version(self, argument_parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        ver: str = "local dev" if (__package__ is None or len(__package__) == 0) else f"{version('webshooter_client')}"
        argument_parser.add_argument("-V", "--version", action="version", version=f"{ver}")
        return argument_parser

    def get_arguments(self, webshooter_rc: WebShooterRC) -> argparse.Namespace:
        class ComboRawTextandArgsDefaultUltimateHelpFormatter(
            argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter
        ):
            pass

        self.__parser = argparse.ArgumentParser(
            description="Webshooter CLI tool",
            formatter_class=ComboRawTextandArgsDefaultUltimateHelpFormatter,
            epilog=(
                "Use --token or create config file (all options are optional) as per example:\n\n"
                "[global]\n"
                "token = <token>\n"
                "club = xx-yyy\n"
                "unicode = [True|False]\n"
            ),
        )

        self._add_argument_version(self.__parser)

        subparsers = self.__parser.add_subparsers(dest="command", required=True)

        # Create parsers for each command
        common_parser = argparse.ArgumentParser(add_help=False)
        common_parser.add_argument(
            "--token",
            help="web token, copy from Browser -> Developer Tools -> Storage -> Local Storage -> token",
        )
        common_parser.add_argument("--name", help="Name")
        common_parser.add_argument("--club", help="Club, use 'None' to unset")
        common_parser.add_argument("--card", help="Card, use 'None' to unset")
        common_parser.add_argument("-u", "--unicode", help="Unicode", action="store_true", default=False)
        common_parser.add_argument("-v", "--verbose", help="Verbose", action="store_true", default=False)

        # Update common_parser with values from webshooter_rc
        if webshooter_rc.club is not None:
            common_parser.set_defaults(club=webshooter_rc.club)
        if webshooter_rc.card is not None:
            common_parser.set_defaults(card=webshooter_rc.card)
        if webshooter_rc.token is not None:
            common_parser.set_defaults(token=webshooter_rc.token)
        if webshooter_rc.unicode is not None:
            common_parser.set_defaults(unicode=webshooter_rc.unicode)

        parser_starttimes = subparsers.add_parser(
            "starttimes",
            parents=[common_parser],
            help="List start times for a competition",
        )
        parser_starttimes.add_argument("competition", help="Competition ID", type=int, default=None)

        parser_ical = subparsers.add_parser(
            "ical",
            parents=[common_parser],
            help="Save start times for a competition (in ical format) to webshooter.ical",
        )
        parser_ical.add_argument("competition", help="Competition ID", type=int, default=None)

        parser_results = subparsers.add_parser(
            "results",
            parents=[common_parser],
            help="List results from a competition",
        )
        parser_results.add_argument("competition", help="Competition ID", type=int, default=None)

        parser_signups = subparsers.add_parser(
            "signups",
            parents=[common_parser],
            help="List signups for a competition",
        )
        parser_signups.add_argument("competition", help="Competition ID", type=int, default=None)

        parser_medals = subparsers.add_parser(
            "medals",
            parents=[common_parser],
            help="List standard medals awarded for a card",
        )
        parser_medals.add_argument("year", nargs="?", help="Optional year", type=int)

        parser_starts = subparsers.add_parser(
            "starts",
            parents=[common_parser],
            help="List total starts from a club",
        )
        parser_starts.add_argument("year", nargs="?", help="Optional year", type=int)

        parser_competitions = subparsers.add_parser(
            "competitions",
            parents=[common_parser],
            help="List all competitions in webshooter",
        )
        parser_competitions.add_argument("year", nargs="?", help="Optional year", type=int)

        args = self.__parser.parse_args()

        return args

    def print_help(self):
        self.__parser.print_help(sys.stderr)


def main():
    command = Command()
    webshooter_rc: WebShooterRC = WebShooterRC.load_config()
    args = command.get_arguments(webshooter_rc=webshooter_rc)

    ApplicationConfig(unicode=args.unicode, verbose=args.verbose, token=args.token)

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
    else:
        command.print_help()
        sys.exit(1)

    print("")
    print_info(club=args.club, info=info)
    print_result(result=result)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
