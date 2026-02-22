"""Competition validation and filtering utilities.

This module provides functions to validate and extract data from precision and military
shooting competition results. It implements the filtering rules required by bests and stats
commands.

Key Rule for Precision Competitions:
    Only use competitions with EXACTLY 7 series. Finals are stored separately and increase
    result.points but are NOT included in result.series. By using sum(result.series) instead
    of result.points, finals are automatically excluded.

    Example (Competition 259):
        result.series = [7 base series only]
        result.points = 452 (base 350 + finals 102)
        sum(result.series) = 350 (finals excluded)
"""

from typing import Optional

from webshooter_client.models.result import PrecisionResult, MilitaryResult, FieldResult, ResultBase


def is_valid_precision_result(result: PrecisionResult) -> bool:
    """Check if precision result is valid for stats/bests.

    Valid precision competitions have EXACTLY 7 series (no finals or non-standard formats).
    Finals are stored separately and increase result.points but are NOT in result.series.

    Args:
        result: PrecisionResult to validate

    Returns:
        True if result has exactly 7 series, False otherwise
    """
    return len(result.series) == 7


def is_valid_military_result(result: MilitaryResult) -> bool:
    """Check if military result is valid for stats/bests.

    Military results are valid if they have series data. No series count validation needed.

    Args:
        result: MilitaryResult to validate

    Returns:
        True if result has series data, False otherwise
    """
    return result.series is not None and len(result.series) > 0


def get_result_points(result: ResultBase) -> Optional[int]:
    """Get points from result, handling finals correctly.

    For precision: Returns sum of series (finals NOT included in series list, so automatically
    excluded). This prevents finals from inflating scores.

    For military: Returns result.points directly.

    Args:
        result: ResultBase (PrecisionResult or MilitaryResult)

    Returns:
        Calculated points value, or None if invalid

    Example:
        >>> precision_result.points  # 452 (includes finals)
        >>> sum(precision_result.series)  # 350 (finals excluded)
        >>> get_result_points(precision_result)  # 350 (uses series sum)
    """
    if isinstance(result, PrecisionResult):
        if not is_valid_precision_result(result):
            return None
        # Use series sum only (finals NOT in series list)
        return sum(s.points for s in result.series)

    if isinstance(result, MilitaryResult):
        if not is_valid_military_result(result):
            return None
        return result.points

    if isinstance(result, FieldResult):
        if not is_valid_field_result(result):
            return None
        return get_field_result_hits(result)

    return None


def is_valid_field_result(result: FieldResult) -> bool:
    """Check if field result is valid for stats/bests.

    Field results are valid if they have station data with at least one hit recorded.

    Args:
        result: FieldResult to validate

    Returns:
        True if result has station data, False otherwise
    """
    return result.stations is not None and len(result.stations) > 0


def get_field_result_hits(result: FieldResult) -> Optional[int]:
    """Get total hits from a field result.

    Args:
        result: FieldResult to extract hits from

    Returns:
        Total hits across all stations, or None if invalid
    """
    if not is_valid_field_result(result):
        return None
    return sum(s.hits for s in result.stations)


def get_field_result_figures(result: FieldResult) -> int:
    """Get total figure hits from a field result.

    Args:
        result: FieldResult to extract figures from

    Returns:
        Total figure hits across all stations
    """
    return sum(s.figure_hits or 0 for s in result.stations)


def get_field_result_points(result: FieldResult) -> int:
    """Get total points from a field result.

    Args:
        result: FieldResult to extract points from

    Returns:
        Total points across all stations
    """
    return sum(s.points or 0 for s in result.stations)
