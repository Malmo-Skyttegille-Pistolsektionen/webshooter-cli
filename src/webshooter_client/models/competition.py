from dataclasses import dataclass
from datetime import date

from webshooter_client.common.enums import DisplayEnum


class CompetitionType(DisplayEnum):
    """Competition type enum with display names."""

    MILITARY = ("military", "Militär snabbmatch")
    PRECISION = ("precision", "Precision")
    FIELD = ("field", "Fält")
    POINTFIELD = ("pointfield", "Poängfält")


@dataclass(kw_only=True)
class Competition:
    id: int
    name: str
    competition_date: date
    signups_close: date
    city: str
    venue: str
    type: CompetitionType
