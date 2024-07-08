import configparser
from dataclasses import dataclass, field
import os


@dataclass(kw_only=True)
class WebShooterRC:
    club: str = field(default=None)
    card: str = field(default=None)
    token: str = field(default=None)
    unicode: bool = field(default=False)

    @staticmethod
    def load_config(configfile: str = f"{os.path.expanduser('~')}/.webshooter.rc") -> "WebShooterRC":
        webshooter_rc: WebShooterRC = WebShooterRC()

        if os.path.exists(configfile):
            config = configparser.ConfigParser()
            config.read_file(open(configfile))
            webshooter_rc.club = config.get("global", "club", fallback=None)
            webshooter_rc.card = config.get("global", "card", fallback=None)
            webshooter_rc.token = config.get("global", "token", fallback=None)
            webshooter_rc.unicode = config.get("global", "unicode", fallback=False)

        return webshooter_rc
