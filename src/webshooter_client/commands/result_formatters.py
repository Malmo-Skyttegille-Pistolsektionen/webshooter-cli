"""Formatters for different competition result types."""

from typing import List, Any, Callable
from tabulate import tabulate

from webshooter_client.models.result import ResultBase
from webshooter_client.models.competition import CompetitionType


def _filter_and_collect_data(results: List[ResultBase], club: str, card: str, row_builder: Callable) -> List[List[Any]]:
    """Filter results and build table data using provided row builder.

    Args:
        results: List of results to process
        club: Club number to filter by
        card: Optional card number to filter by (takes precedence over club)
        row_builder: Function that takes a ResultBase and returns a list of values

    Returns:
        List of table rows
    """
    table_data = []
    for result in results:
        signup = result.signup
        # If card is provided, match only that card (ignore club)
        # Otherwise, match all signups from the club
        if (club == signup.spsf_club_number and not card) or card == signup.shooting_card_number:
            table_data.append(row_builder(result))
    return table_data


def _print_sorted_table(table_data: List[List[Any]], headers: List[str]) -> None:
    """Sort and print table data.

    Args:
        table_data: Table rows
        headers: Column headers
    """
    # Sort by Main Class (index 2) and Place (index 4)
    sorted_data = sorted(table_data, key=lambda row: (row[2], row[4]))
    print(tabulate(sorted_data, headers=headers, tablefmt="simple"))


class PrecisionMilitaryFormatter:
    """Formatter for PRECISION and MILITARY competition results."""

    def format_and_print(self, results: List[ResultBase], club: str, card: str) -> None:
        """Format and print precision/military results with series data."""

        def build_row(result: ResultBase) -> List[Any]:
            signup = result.signup
            return [
                signup.shooting_card_number,
                signup.fullname,
                signup.weapon_class_general,
                signup.weapon_class,
                result.placement,
                result.std_medal.display_name if result.std_medal else "",
                result.points,
                sum(series.inner_tens for series in result.series),
                " ".join(str(series.points) for series in result.series),
            ]

        table_data = _filter_and_collect_data(results, club, card, build_row)
        headers = ["Card", "Name", "Main Class", "Sub class", "Place", "Medal", "Points", "Xs", "Series"]
        _print_sorted_table(table_data, headers)


class FieldFormatter:
    """Formatter for FIELD competition results."""

    def format_and_print(self, results: List[ResultBase], club: str, card: str) -> None:
        """Format and print field results with station data."""

        def build_row(result: ResultBase) -> List[Any]:
            signup = result.signup
            return [
                signup.shooting_card_number,
                signup.fullname,
                signup.weapon_class_general,
                signup.weapon_class,
                result.placement,
                result.std_medal.display_name if result.std_medal else "",
                sum(r.hits for r in result.stations),
                sum(r.figure_hits for r in result.stations),
                result.points,
                " ".join(f"{r.hits}/{r.figure_hits}" for r in result.stations),
            ]

        table_data = _filter_and_collect_data(results, club, card, build_row)
        headers = [
            "Card",
            "Name",
            "Main Class",
            "Sub class",
            "Place",
            "Medal",
            "Hits",
            "Figures",
            "Points",
            "Stations",
        ]
        _print_sorted_table(table_data, headers)


# Mapping of competition types to formatter instances
_FORMATTERS = {
    CompetitionType.PRECISION: PrecisionMilitaryFormatter(),
    CompetitionType.MILITARY: PrecisionMilitaryFormatter(),
    CompetitionType.FIELD: FieldFormatter(),
    CompetitionType.POINTFIELD: FieldFormatter(),
}


def get_formatter(competition_type: CompetitionType):
    """Get the appropriate formatter for a competition type.

    Args:
        competition_type: Type of competition

    Returns:
        Formatter instance for the competition type

    Raises:
        ValueError: If competition type is not supported
    """
    formatter = _FORMATTERS.get(competition_type)
    if not formatter:
        raise ValueError(f"No formatter available for competition type: {competition_type}")
    return formatter
