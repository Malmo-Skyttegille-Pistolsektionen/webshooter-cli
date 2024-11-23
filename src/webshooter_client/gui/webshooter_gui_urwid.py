import time
from dataclasses import dataclass, field

from webshooter_client.commands.competition_list import CompetitionsListCommand
from webshooter_client.common.common import command_to_string, printable
from webshooter_client.common.webshooter_rc import WebShooterRC

import urwid
from collections.abc import Iterable

webshooter_rc = None
main = None
args = {}


@dataclass(kw_only=True)
class WebShooterGUI:
    unicode: str = field(default=None)
    token: str = field(default=None)
    command: str = field(default=None)
    card: str = field(default=None)
    club: str = field(default=None)
    year: str = field(default=None)
    competition: str = field(default=None)
    verbose: bool = field(default=False)

    def app_exit(button):
        args["command"] = "exit"
        raise urwid.ExitMainLoop()

    def keyboard_input(key):
        if key in ("q", "Q", "esc"):
            args["command"] = "exit"
            raise urwid.ExitMainLoop()

    def card_club_to_string(mode: str) -> str:
        return {
            "card": "Användare",
            "club": "Klubb",
        }.get(mode, "Okänd")

    def competition_to_string(competition: str) -> str:
        return competition.split(" ", 1)[1]

    def menu(title: str, choices: Iterable[str], to_string, item_chosen) -> urwid.ListBox:
        body = [urwid.Text(title), urwid.Divider()]
        for c in choices:
            button = urwid.Button(printable(to_string(c))) if to_string else urwid.Button(c)
            urwid.connect_signal(button, "click", item_chosen, user_args=[c.split()[0]])
            body.append(urwid.AttrMap(button, None, focus_map="reversed"))

        button = urwid.Button("")
        body.append(urwid.AttrMap(button, None, focus_map="reversed"))

        button = urwid.Button("Exit")
        urwid.connect_signal(button, "click", WebShooterGUI.app_exit)
        body.append(urwid.AttrMap(button, None, focus_map="reversed"))

        return urwid.ListBox(urwid.SimpleFocusListWalker(body))

    def command_chosen(choice, button):
        args["command"] = choice

        if args["command"] not in ["competitions"]:
            main.original_widget = urwid.Padding(
                WebShooterGUI.menu(
                    f"{command_to_string(args['command'])}",
                    ["card", "club"],
                    WebShooterGUI.card_club_to_string,
                    WebShooterGUI.user_chosen,
                ),
                left=2,
                right=2,
            )
        else:
            WebShooterGUI.user_chosen(None, button)

    def user_chosen(choice, button):
        args["user"] = choice
        args["card"] = None
        args["club"] = None

        if args["user"] == "card":
            args["card"] = webshooter_rc.card
        elif choice == "club":
            args["club"] = webshooter_rc.club

        year = int(time.strftime("%Y", time.gmtime()))
        years = []
        while year >= 2022:
            years.append(str(year))
            year -= 1

        main.original_widget = urwid.Padding(
            WebShooterGUI.menu(
                f"{command_to_string(args['command'])}, {WebShooterGUI.card_club_to_string(args['user'])}",
                years,
                None,
                WebShooterGUI.year_chosen,
            ),
            left=2,
            right=2,
        )

    def year_chosen(choice, button):
        args["year"] = choice

        if args["command"] not in ["medals", "starts", "competitions"]:
            c = []
            competitions = CompetitionsListCommand.get_competitions_list(int(args["year"]))
            for key, value in competitions.items():
                c.append(f"{str(key)} {value['name']}")

            main.original_widget = urwid.Padding(
                WebShooterGUI.menu(
                    f"{command_to_string(args['command'])}, "
                    f"{WebShooterGUI.card_club_to_string(args['user'])}, {args['year']}",
                    c,
                    WebShooterGUI.competition_to_string,
                    WebShooterGUI.competition_chosen,
                ),
                left=2,
                right=2,
            )

        else:
            args["competition"] = None
            raise urwid.ExitMainLoop()

    def competition_chosen(choice, button):
        args["competition"] = choice
        raise urwid.ExitMainLoop()

    @staticmethod
    def run(webshooter_rc: WebShooterRC) -> "WebShooterGUI":

        globals()["webshooter_rc"] = webshooter_rc

        args["unicode"] = webshooter_rc.unicode
        args["token"] = webshooter_rc.token

        gui: WebShooterGUI = WebShooterGUI()

        global main
        main = urwid.Padding(
            WebShooterGUI.menu(
                "Mode",
                ["signups", "starttimes", "ical", "results", "medals", "starts", "competitions"],
                command_to_string,
                WebShooterGUI.command_chosen,
            ),
            left=2,
            right=2,
        )
        top = urwid.Overlay(
            main,
            urwid.SolidFill(),
            align=urwid.CENTER,
            width=(urwid.RELATIVE, 60),
            valign=urwid.MIDDLE,
            height=(urwid.RELATIVE, 60),
        )
        urwid.MainLoop(top, unhandled_input=WebShooterGUI.keyboard_input).run()

        gui.command = args["command"]
        if args["command"] != "exit":
            gui.unicode = args["unicode"]
            gui.token = args["token"]
            gui.card = args["card"]
            gui.club = args["club"]
            gui.year = args["year"]
            gui.competition = args["competition"]

        return gui
