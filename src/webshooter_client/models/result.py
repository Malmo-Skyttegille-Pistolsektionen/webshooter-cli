from dataclasses import dataclass, field
from typing import List, Optional

from webshooter_client.models.signup import Signup
from webshooter_client.common.enums import DisplayEnum


class StdMedal(DisplayEnum):
    """Standard medal enum with display names."""

    BRONZE = "B", "Brons"
    SILVER = "S", "Silver"


@dataclass(kw_only=True)
class ResultBase:
    signup: Signup
    placement: int
    std_medal: Optional[StdMedal]
    points: int
    calculated_std_medal: Optional[StdMedal] = None


@dataclass(kw_only=True)
class SeriesResult:
    points: int
    inner_tens: int


@dataclass(kw_only=True)
class PrecisionResult(ResultBase):
    series: List[SeriesResult] = field(default_factory=list)


@dataclass(kw_only=True)
class MilitaryResult(ResultBase):
    series: List[SeriesResult] = field(default_factory=list)


@dataclass(kw_only=True)
class StationResult:
    hits: int
    figure_hits: int
    points: Optional[int] = None


@dataclass(kw_only=True)
class FieldResult(ResultBase):
    stations: List[StationResult] = field(default_factory=list)
