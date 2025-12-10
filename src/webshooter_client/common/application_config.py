from dataclasses import dataclass, field
from typing import Optional

from webshooter_client.common.singleton_meta import SingletonMeta


@dataclass(kw_only=True)
class ApplicationConfig(metaclass=SingletonMeta):
    """
    Holds shared application config.
    Command line options take precedence over webshooter.rc.
    """

    unicode: bool = field(default=True)
    verbose: bool = field(default=False)
    token: Optional[str] = field(default=None)
