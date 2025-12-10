from typing import Optional
from dataclasses import dataclass


@dataclass(kw_only=True, frozen=True)
class Signup:
    id: int
    spsf_club_number: str
    shooting_card_number: Optional[str]  # there are data such as "12 456", "A1234", "Xx" etc
    fullname: str
    lane: int
    weapon_class: str
    weapon_class_general: str
    share_patrol_with: Optional[int]
