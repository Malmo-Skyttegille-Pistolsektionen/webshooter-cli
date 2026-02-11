from typing import List
from dataclasses import dataclass
from datetime import datetime

from webshooter_client.models.signup import Signup


@dataclass(kw_only=True)
class Patrol:
    id: int
    start_time: datetime
    end_time: datetime
    number: int
    signups: List[Signup]
