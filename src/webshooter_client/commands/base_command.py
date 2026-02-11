"""Base command class with common functionality for all commands."""

from abc import ABC
from typing import List, Any
from tabulate import tabulate


class BaseCommand(ABC):
    """Abstract base class for all command implementations.

    Provides common utility methods for output formatting and data display.
    Subclasses implement static methods for their specific command logic.
    """

    @staticmethod
    def print_table(data: List[List[Any]], headers: List[str], tablefmt: str = "simple") -> None:
        """Print formatted table output.

        Args:
            data: Table data as list of rows
            headers: Column headers
            tablefmt: Table format (default: simple)
        """
        print(tabulate(data, headers=headers, tablefmt=tablefmt))

    @staticmethod
    def print_section_separator() -> None:
        """Print a blank line separator between sections."""
        print("\n\n")
