"""Display year-by-year statistics and trends."""

import sys
from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional

from tabulate import tabulate

from webshooter_client.common.competition_filter import (
    is_valid_precision_result,
    is_valid_military_result,
)
from webshooter_client.common.fetch_utils import fetch_results_for_card
from webshooter_client.models.competition import CompetitionType
from webshooter_client.models.result import PrecisionResult, MilitaryResult
from webshooter_client.stats.calculator import (
    calculate_yearly_stats,
    calculate_trend,
    get_num_series,
    get_weapon_group,
)
from webshooter_client.stats.models import YearlyStats


def _result_filter(result) -> bool:
    """Filter function for valid precision/military results with series."""
    if not result.series:
        return False

    if isinstance(result, PrecisionResult):
        return is_valid_precision_result(result)
    elif isinstance(result, MilitaryResult):
        return is_valid_military_result(result)

    return False


def _fetch_all_results_for_years(years: List[int], card: str) -> Dict[int, List[PrecisionResult | MilitaryResult]]:
    """Fetch all results for card across multiple years.

    For Precision: Only includes competitions with exactly 7 series (excludes finals).
    For Military: Includes all competitions with series data.

    Args:
        years: List of years to fetch
        card: Shooting card number

    Returns:
        Dictionary mapping year to list of valid results
    """
    return fetch_results_for_card(
        years=years,
        card=card,
        competition_types={CompetitionType.PRECISION, CompetitionType.MILITARY},
        result_filter=_result_filter,
        show_progress=True,
    )


def _group_results_by_type_and_group(
    results: List[PrecisionResult | MilitaryResult],
) -> Dict[str, List[PrecisionResult | MilitaryResult]]:
    """Group results by competition type and weapon group.

    Returns Dict like: "Precision - C" -> [results]
    """
    grouped = defaultdict(list)

    for result in results:
        # Determine type
        comp_type = "Precision" if isinstance(result, PrecisionResult) else "Militär snabbmatch"

        # Extract weapon group from class (e.g., "C3" -> "C")
        weapon_group = get_weapon_group(result.signup.weapon_class)

        key = f"{comp_type} - Weapon Group {weapon_group}"
        grouped[key].append(result)

    return dict(grouped)


def _format_yearly_section(type_group_key: str, yearly_stats_dict: Dict[int, "YearlyStats"]) -> str:
    """Format a section for one competition type + weapon group combination using tabular format.

    Args:
        type_group_key: e.g., "Precision - Weapon Group C"
        yearly_stats_dict: Dict mapping year to YearlyStats

    Returns:
        Formatted section as string with tabular layout
    """
    output = [f"\n=== {type_group_key} ===\n"]

    sorted_years = sorted(yearly_stats_dict.keys())

    # Build table data
    table_data = []
    for i, year in enumerate(sorted_years):
        yearly_stats = yearly_stats_dict[year]
        basic_stats = yearly_stats.basic_stats

        # Calculate change from previous year
        if i > 0:
            prev_year = sorted_years[i - 1]
            prev_stats = yearly_stats_dict[prev_year]
            prev_mean = prev_stats.basic_stats.mean
            current_mean = basic_stats.mean
            absolute_change = current_mean - prev_mean
            percent_change = (absolute_change / prev_mean * 100) if prev_mean != 0 else 0.0

            if percent_change >= 0:
                change_str = f"+{absolute_change:.1f} (+{percent_change:.1f}%) ⬆️"
            else:
                change_str = f"{absolute_change:.1f} ({percent_change:.1f}%) ⬇️"
        else:
            change_str = "—"

        # Build row
        row = [
            year,
            yearly_stats.weapon_class,
            basic_stats.count,
            f"{basic_stats.mean:.1f} ± {basic_stats.stdev:.1f}",
            f"{basic_stats.median:.0f}",
            f"{basic_stats.max_score} / {basic_stats.min_score}",
            f"{basic_stats.avg_xs:.1f}",
            change_str,
        ]
        table_data.append(row)

    # Format table
    headers = ["Year", "Class", "Comps", "Average ± Stdev", "Median", "Best / Worst", "Avg Xs", "Change YoY"]
    table = tabulate(table_data, headers=headers, tablefmt="grid", stralign="left", numalign="right")
    output.append(table)
    output.append("")

    # Show overall progression if multiple years
    if len(sorted_years) > 1:
        first_year = sorted_years[0]
        last_year = sorted_years[-1]
        first_stats = yearly_stats_dict[first_year]
        last_stats = yearly_stats_dict[last_year]
        first_mean = first_stats.basic_stats.mean
        last_mean = last_stats.basic_stats.mean
        total_change = last_mean - first_mean
        total_percent = (total_change / first_mean * 100) if first_mean != 0 else 0.0
        trend = calculate_trend(yearly_stats_dict)

        progression_line = (
            f"Overall: {first_stats.weapon_class}→{last_stats.weapon_class} | "
            f"Total: {total_change:+.1f} points ({total_percent:+.1f}%) | "
            f"Trend: {trend:+.1f} points/year "
            f"{'⬆️' if trend > 0 else '⬇️' if trend < 0 else '➡️'}"
        )
        output.append(progression_line)

    return "\n".join(output)


def get_yearly_stats(
    card: str,
    years: Optional[List[int]] = None,
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
    all_years: bool = False,
) -> None:
    """Display year-by-year statistics for a shooter.

    Args:
        card: Shooting card number
        years: Specific years as list (e.g., [2022, 2023, 2024])
        from_year: Start year for range (inclusive)
        to_year: End year for range (inclusive)
        all_years: Fetch all available years
    """
    # Parse year arguments
    years_to_fetch = []

    if all_years:
        # Dynamically use current year as upper bound (was hardcoded to 2026)
        # Range from 2000 (reasonable historical limit) to current year
        years_to_fetch = list(range(2000, date.today().year + 1))
    elif years:
        years_to_fetch = years
    elif from_year is not None and to_year is not None:
        years_to_fetch = list(range(from_year, to_year + 1))
    else:
        print("Error: Must specify --years, --from/--to, or --all-years", file=sys.stderr)
        return

    print(f"Year-by-Year Statistics for Card: {card}", file=sys.stderr)
    print(f"Years: {', '.join(map(str, years_to_fetch))}", file=sys.stderr)
    print("Competition Types: Precision, Militär snabbmatch", file=sys.stderr)
    print(file=sys.stderr)

    # Fetch all results
    results_by_year = _fetch_all_results_for_years(years_to_fetch, card)

    if not results_by_year:
        print(f"No results found for card {card} in years {years_to_fetch}", file=sys.stderr)
        return

    # For each year, group by type+group and calculate stats
    type_group_yearly_stats: Dict[str, Dict[int, "YearlyStats"]] = defaultdict(dict)

    for year, results in sorted(results_by_year.items()):
        # Group by type and weapon group
        grouped = _group_results_by_type_and_group(results)

        for type_group_key, group_results in grouped.items():
            # Determine number of series
            num_series = get_num_series(group_results[0]) if group_results else 0

            # Calculate yearly stats for this type+group
            yearly_stats = calculate_yearly_stats(group_results, year, num_series)
            type_group_yearly_stats[type_group_key][year] = yearly_stats

    # Display each type+group section
    for type_group_key in sorted(type_group_yearly_stats.keys()):
        yearly_stats_dict = type_group_yearly_stats[type_group_key]
        section = _format_yearly_section(type_group_key, yearly_stats_dict)
        print(section)

    print()
    print("Note: Only showing weapon groups where you competed.", file=sys.stderr)
