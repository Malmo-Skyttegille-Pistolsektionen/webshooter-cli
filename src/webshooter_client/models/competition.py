from dataclasses import dataclass
from enum import Enum
from datetime import date


class CompetitionType(Enum):
    def __new__(cls, value, display_name):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.display_name = display_name
        return obj

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
