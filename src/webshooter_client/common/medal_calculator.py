"""Medal calculation module for WebShooter competitions.

Implements independent standard medal calculation for Field, Precision, and Military
competitions, to validate historical data and support stats features.
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any

from webshooter_client.models.result import StdMedal
from webshooter_client.models.competition import CompetitionType


class ThresholdType(Enum):
    """Enum for medal threshold types."""

    SILVER = "silver"
    BRONZE = "bronze"


# Fixed threshold tables for medal awards

PRECISION_FIXED_THRESHOLDS = {
    6: {
        "A": {ThresholdType.SILVER: 277, ThresholdType.BRONZE: 267},
        "B": {ThresholdType.SILVER: 282, ThresholdType.BRONZE: 273},
        "C": {ThresholdType.SILVER: 283, ThresholdType.BRONZE: 276},
    },
    7: {
        "A": {ThresholdType.SILVER: 323, ThresholdType.BRONZE: 312},
        "B": {ThresholdType.SILVER: 329, ThresholdType.BRONZE: 319},
        "C": {ThresholdType.SILVER: 330, ThresholdType.BRONZE: 322},
    },
    10: {
        "A": {ThresholdType.SILVER: 461, ThresholdType.BRONZE: 445},
        "B": {ThresholdType.SILVER: 470, ThresholdType.BRONZE: 455},
        "C": {ThresholdType.SILVER: 471, ThresholdType.BRONZE: 460},
    },
}

MILITARY_FIXED_THRESHOLDS = {
    12: {
        "A": {ThresholdType.SILVER: 540, ThresholdType.BRONZE: 516},
        "R": {ThresholdType.SILVER: 552, ThresholdType.BRONZE: 528},
        "B": {ThresholdType.SILVER: 561, ThresholdType.BRONZE: 537},
        "C": {ThresholdType.SILVER: 564, ThresholdType.BRONZE: 540},
    },
}


@dataclass
class MedalCalculationInput:
    """Input data for medal calculation.

    Attributes:
        results: List of result dictionaries with scoring info
        competition_type: Type of competition (Field, Precision, Military)
        weapon_groups: List of weapon groups present in competition
    """

    results: List[Dict[str, Any]]
    competition_type: CompetitionType
    weapon_groups: List[str]


def calculate_medals(input_data: MedalCalculationInput) -> List[Optional[StdMedal]]:
    """Calculate standard medals for all results in a competition.

    Uses both fixed thresholds (where applicable) and relative placement.
    A result receives a medal if it meets EITHER criterion.

    Args:
        input_data: MedalCalculationInput containing results and competition info

    Returns:
        List of StdMedal or None values, one per result in input order

    """
    if not input_data.results:
        return []

    if input_data.competition_type == CompetitionType.FIELD:
        return _calculate_field_medals(input_data.results)
    elif input_data.competition_type == CompetitionType.PRECISION:
        return _calculate_precision_medals(input_data.results)
    elif input_data.competition_type == CompetitionType.MILITARY:
        return _calculate_military_medals(input_data.results)
    else:
        # Unknown competition type
        return [None] * len(input_data.results)


def _calculate_field_medals(results: List[Dict[str, Any]]) -> List[Optional[StdMedal]]:
    """Calculate field competition medals using relative placement only.

    Field results are sorted by: hits DESC, figures DESC, points DESC.
    Silver: top 1/9 of competitors
    Bronze: top 1/3 of competitors

    Args:
        results: List of result dictionaries

    Returns:
        List of StdMedal or None for each result
    """
    if not results:
        return []

    # Create indexed results for sorting and tracking original order
    indexed_results = [(i, r) for i, r in enumerate(results)]

    # Sort by hits (DESC), then figures (DESC), then points (DESC)
    sorted_results = sorted(
        indexed_results,
        key=lambda x: (
            -(x[1].get("hits", 0)),
            -(x[1].get("figures", 0)),
            -(x[1].get("points", 0)),
        ),
    )

    count = len(sorted_results)
    medals: List[Optional[StdMedal]] = [None] * count

    if count == 0:
        return medals

    # Calculate thresholds: floor(count/9) - 1 for silver, floor(count/3) - 1 for bronze
    silver_threshold = math.floor(count / 9) - 1
    bronze_threshold = math.floor(count / 3) - 1

    # Ensure indices are within bounds
    if silver_threshold < 0:
        silver_threshold = -1  # No one gets silver
    if bronze_threshold < 0:
        bronze_threshold = -1  # No one gets bronze

    # Assign medals in sorted order
    for sorted_index, (orig_index, result) in enumerate(sorted_results):
        if sorted_index <= silver_threshold:
            medals[sorted_index] = StdMedal.SILVER
        elif sorted_index <= bronze_threshold:
            medals[sorted_index] = StdMedal.BRONZE

    # Reorder medals back to original order
    original_order_medals = [None] * len(results)
    for sorted_index, (orig_index, _) in enumerate(sorted_results):
        original_order_medals[orig_index] = medals[sorted_index]

    return original_order_medals


def _calculate_precision_medals(results: List[Dict[str, Any]]) -> List[Optional[StdMedal]]:
    """Calculate precision competition medals using fixed thresholds and relative placement.

    For each result, check both fixed thresholds and relative placement.
    Award a medal if EITHER criterion is met.

    Args:
        results: List of result dictionaries with series info

    Returns:
        List of StdMedal or None for each result
    """
    if not results:
        return []

    medals: List[Optional[StdMedal]] = []

    # Calculate relative placement thresholds once
    count = len(results)
    silver_rel_threshold = math.floor(count / 9) - 1
    bronze_rel_threshold = math.floor(count / 3) - 1

    # Sort by points (descending) for relative placement ranking
    indexed_results = [(i, r) for i, r in enumerate(results)]
    sorted_by_points = sorted(indexed_results, key=lambda x: -(x[1].get("points", 0)))

    # Create ranking map
    ranking = {}
    for sorted_index, (orig_index, _) in enumerate(sorted_by_points):
        ranking[orig_index] = sorted_index

    for orig_index, result in enumerate(results):
        points = result.get("points", 0)
        series_list = result.get("series", [])
        weapon_group = result.get("weapon_group", "A")
        series_count = len(series_list)

        medal = None

        # Check fixed thresholds first
        if series_count in PRECISION_FIXED_THRESHOLDS:
            thresholds = PRECISION_FIXED_THRESHOLDS[series_count].get(weapon_group, {})
            silver_threshold = thresholds.get(ThresholdType.SILVER, 0)
            bronze_threshold = thresholds.get(ThresholdType.BRONZE, 0)

            if points >= silver_threshold:
                medal = StdMedal.SILVER
            elif points >= bronze_threshold:
                medal = StdMedal.BRONZE

        # Check relative placement
        relative_medal = None
        rank = ranking[orig_index]
        if rank <= silver_rel_threshold:
            relative_medal = StdMedal.SILVER
        elif rank <= bronze_rel_threshold:
            relative_medal = StdMedal.BRONZE

        # Use the better medal (silver > bronze > none), or relative if fixed didn't give one
        if relative_medal and not medal:
            medal = relative_medal
        elif relative_medal and medal:
            # Prefer the higher medal (silver over bronze)
            if relative_medal == StdMedal.SILVER and medal != StdMedal.SILVER:
                medal = StdMedal.SILVER

        medals.append(medal)

    return medals


def _calculate_military_medals(results: List[Dict[str, Any]]) -> List[Optional[StdMedal]]:
    """Calculate military competition medals using fixed thresholds and relative placement.

    For each result, check both fixed thresholds (12 series only) and relative placement.
    Award a medal if EITHER criterion is met.

    Args:
        results: List of result dictionaries with series info

    Returns:
        List of StdMedal or None for each result
    """
    if not results:
        return []

    medals: List[Optional[StdMedal]] = []

    # Calculate relative placement thresholds once
    count = len(results)
    silver_rel_threshold = math.floor(count / 9) - 1
    bronze_rel_threshold = math.floor(count / 3) - 1

    # Sort by points (descending) for relative placement ranking
    indexed_results = [(i, r) for i, r in enumerate(results)]
    sorted_by_points = sorted(indexed_results, key=lambda x: -(x[1].get("points", 0)))

    # Create ranking map
    ranking = {}
    for sorted_index, (orig_index, _) in enumerate(sorted_by_points):
        ranking[orig_index] = sorted_index

    for orig_index, result in enumerate(results):
        points = result.get("points", 0)
        series_list = result.get("series", [])
        weapon_group = result.get("weapon_group", "A")
        series_count = len(series_list)

        medal = None

        # Check fixed thresholds (military always has 12 series)
        if series_count == 12:
            thresholds = MILITARY_FIXED_THRESHOLDS[12].get(weapon_group, {})
            silver_threshold = thresholds.get(ThresholdType.SILVER, 0)
            bronze_threshold = thresholds.get(ThresholdType.BRONZE, 0)

            if points >= silver_threshold:
                medal = StdMedal.SILVER
            elif points >= bronze_threshold:
                medal = StdMedal.BRONZE

        # Check relative placement
        relative_medal = None
        rank = ranking[orig_index]
        if rank <= silver_rel_threshold:
            relative_medal = StdMedal.SILVER
        elif rank <= bronze_rel_threshold:
            relative_medal = StdMedal.BRONZE

        # Use the better medal (silver > bronze > none), or relative if fixed didn't give one
        if relative_medal and not medal:
            medal = relative_medal
        elif relative_medal and medal:
            # Prefer the higher medal (silver over bronze)
            if relative_medal == StdMedal.SILVER and medal != StdMedal.SILVER:
                medal = StdMedal.SILVER

        medals.append(medal)

    return medals
