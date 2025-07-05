import time
from dataclasses import dataclass, field
from webshooter_client.commands.competition_list import CompetitionsListCommand
from webshooter_client.common.common import command_to_string, printable
from webshooter_client.common.application_config import ApplicationConfig
import urwid
from collections.abc import Iterable


@dataclass
class WebShooterGUI:
    app_config: ApplicationConfig
    args: dict = field(default_factory=dict)
    main: any = None

    def __post_init__(self):
        self.args["unicode"] = self.app_config.unicode
        self.args["token"] = self.app_config.token
        self.args["card"] = self.app_config.card
        self.args["club"] = self.app_config.club

    def app_exit(self, button: urwid.Button) -> None:
        self.args["command"] = "exit"
        raise urwid.ExitMainLoop()

    def keyboard_input(self, key: str):
        if key in ("q", "Q", "esc"):
            self.args["command"] = "exit"
            raise urwid.ExitMainLoop()

    def command_chosen(self, choice, button):
        self.args["command"] = choice
        if self.args["command"] not in ["competitions"]:
            self.main.original_widget = urwid.Padding(
                self.menu(
                    f"{command_to_string(self.args['command'])}",
                    ["card", "club"],
                    WebShooterGUI.card_club_to_string,
                    self.user_chosen,
                ),
                left=2,
                right=2,
            )
        else:
            self.user_chosen(None, button)

    def user_chosen(self, choice, button):
        self.args["user"] = choice
        self.args["card"] = None
        self.args["club"] = None
        app_config = ApplicationConfig()
        if self.args["user"] == "card":
            self.args["card"] = app_config.card
        elif choice == "club":
            self.args["club"] = app_config.club

        year = int(time.strftime("%Y", time.gmtime()))
        years = []
        while year >= 2022:
            years.append(str(year))
            year -= 1

        self.main.original_widget = urwid.Padding(
            self.menu(
                f"{command_to_string(self.args['command'])}, {WebShooterGUI.card_club_to_string(self.args['user'])}",
                years,
                None,
                self.year_chosen,
            ),
            left=2,
            right=2,
        )

    def year_chosen(self, choice: str, button: urwid.Button) -> None:
        self.args["year"] = choice
        if self.args["command"] not in ["medals", "starts", "competitions"]:
            c = []
            competitions = CompetitionsListCommand.get_competitions_list(int(self.args["year"]))
            for key, value in competitions.items():
                c.append(f"{str(key)} {value['name']}")
            self.main.original_widget = urwid.Padding(
                self.menu(
                    f"{command_to_string(self.args['command'])}, "
                    f"{WebShooterGUI.card_club_to_string(self.args['user'])}, {self.args['year']}",
                    c,
                    WebShooterGUI.competition_to_string,
                    self.competition_chosen,
                ),
                left=2,
                right=2,
            )
        else:
            self.args["competition"] = None
            raise urwid.ExitMainLoop()

    def competition_chosen(self, choice: str, button: urwid.Button) -> None:
        self.args["competition"] = choice
        raise urwid.ExitMainLoop()

    def menu(self, title: str, choices: Iterable[str], to_string, item_chosen) -> urwid.ListBox:
        body = [urwid.Text(title), urwid.Divider()]
        for c in choices:
            button = urwid.Button(printable(to_string(c))) if to_string else urwid.Button(c)
            urwid.connect_signal(button, "click", item_chosen, user_args=[c.split()[0]])
            body.append(urwid.AttrMap(button, None, focus_map="reversed"))
        button = urwid.Button("")
        body.append(urwid.AttrMap(button, None, focus_map="reversed"))
        button = urwid.Button("Exit")
        urwid.connect_signal(button, "click", self.app_exit)
        body.append(urwid.AttrMap(button, None, focus_map="reversed"))
        return urwid.ListBox(urwid.SimpleFocusListWalker(body))

    @staticmethod
    def card_club_to_string(mode: str) -> str:
        return {
            "card": "Användare",
            "club": "Klubb",
        }.get(mode, "Okänd")

    @staticmethod
    def competition_to_string(competition: str) -> str:
        return competition.split(" ", 1)[1]

    @staticmethod
    def run(app_config: ApplicationConfig) -> dict | None:
        gui: WebShooterGUI = WebShooterGUI(app_config)
        main = urwid.Padding(
            gui.menu(
                "Mode",
                ["signups", "starttimes", "ical", "results", "medals", "starts", "competitions"],
                command_to_string,
                gui.command_chosen,
            ),
            left=2,
            right=2,
        )
        gui.main = main
        top = urwid.Overlay(
            main,
            urwid.SolidFill(),
            align=urwid.CENTER,
            width=(urwid.RELATIVE, 60),
            valign=urwid.MIDDLE,
            height=(urwid.RELATIVE, 60),
        )
        urwid.MainLoop(top, unhandled_input=gui.keyboard_input).run()
        if gui.args.get("command") != "exit":
            return gui.args
        return None
