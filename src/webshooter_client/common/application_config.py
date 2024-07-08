from dataclasses import dataclass, field

from webshooter_client.common.singleton_meta import SingletonMeta


@dataclass(kw_only=True)
class ApplicationConfig(metaclass=SingletonMeta):
    """
    Holds shared application config.
    """

    unicode: bool = field(default=True)
    verbose: bool = field(default=False)
    token: str = field(default=None)
