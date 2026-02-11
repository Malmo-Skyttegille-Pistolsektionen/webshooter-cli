from dataclasses import dataclass, field
from typing import Optional

from webshooter_client.common.singleton_meta import SingletonMeta


@dataclass(kw_only=True)
class ApplicationConfig(metaclass=SingletonMeta):
    """
    Singleton configuration holder for the application.

    This class uses the Singleton pattern to ensure only one configuration instance
    exists throughout the application lifecycle. Configuration is loaded from:
    1. ~/.webshooter.rc config file (if exists)
    2. Command-line arguments (override config file values)

    Rationale for Singleton Pattern:
    - Config needs to be accessible across multiple layers (commands, API, services)
    - Avoids parameter passing through deep call stacks
    - Ensures consistency - prevents conflicting configurations
    - Simple access pattern: ApplicationConfig()
    - Initialized once during CLI startup from configargparse

    Example:
        config = ApplicationConfig()
        if config.verbose:
            print("Verbose mode enabled")

    Attributes:
        unicode: Enable Unicode symbols in output (default: True)
        verbose: Enable verbose logging (default: False)
        token: API authentication token from webshooter.se (default: None)
    """

    unicode: bool = field(default=True)
    verbose: bool = field(default=False)
    token: Optional[str] = field(default=None)
