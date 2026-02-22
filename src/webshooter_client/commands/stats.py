"""Display year-by-year statistics and trends."""

import sys
from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional

from tabulate import tabulate

from webshooter_client.api.api_calls import get_competition, get_results
from webshooter_client.common.competition_filter import (
    is_valid_precision_result,
    is_valid_military_result,
)
from webshooter_client.common.fetch_utils import fetch_results_for_card, fetch_field_competition_results
from webshooter_client.models.competition import CompetitionType
from webshooter_client.models.result import FieldResult, PrecisionResult, MilitaryResult
from webshooter_client.stats.calculator import (
    calculate_yearly_stats,
    calculate_trend,
    calculate_field_yearly_stats,
    calculate_field_trend,
    calculate_field_station_deviations,
    get_num_series,
    get_weapon_group,
)
from webshooter_client.stats.models import FieldYearlyStats, YearlyStats


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


def _format_field_yearly_section(type_group_key: str, yearly_stats_dict: Dict[int, FieldYearlyStats]) -> str:
    """Format a section for Field competition statistics.

    Shows per-station deviations from std medal winners, total deviation, and miss rate.

    Args:
        type_group_key: e.g., "Fält - Weapon Group C"
        yearly_stats_dict: Dict mapping year to FieldYearlyStats

    Returns:
        Formatted section as string with tabular layout
    """
    output = [f"\n=== {type_group_key} ===\n"]

    sorted_years = sorted(yearly_stats_dict.keys())

    # Determine max stations seen across all years
    max_stations = max(
        (max(stats.station_deviations.keys(), default=0) for stats in yearly_stats_dict.values()),
        default=0,
    )

    # Build headers dynamically based on max stations
    station_headers = [f"Sta{i}Δ" for i in range(1, max_stations + 1)]
    headers = ["Year", "Comps"] + station_headers + ["TotalΔ", "FigsΔ", "Miss/Sta", "Trend"]

    table_data = []
    for i, year in enumerate(sorted_years):
        stats = yearly_stats_dict[year]

        # Trend vs previous year
        if i > 0:
            prev_year = sorted_years[i - 1]
            prev_avg = yearly_stats_dict[prev_year].avg_hits
            change = stats.avg_hits - prev_avg
            trend_str = f"{change:+.1f} {'⬆️' if change > 0 else '⬇️' if change < 0 else '➡️'}"
        else:
            trend_str = "—"

        # Station deviations (use — for stations not present this year)
        station_devs = []
        for station_pos in range(1, max_stations + 1):
            if station_pos in stats.station_deviations:
                dev = stats.station_deviations[station_pos]
                station_devs.append(f"{dev:+.1f}")
            else:
                station_devs.append("—")

        total_dev_str = f"{stats.total_deviation:+.1f}" if stats.num_with_medal_data > 0 else "—"
        total_figs_dev_str = f"{stats.total_figures_deviation:+.1f}" if stats.num_with_medal_data > 0 else "—"

        row = (
            [
                year,
                stats.num_competitions,
            ]
            + station_devs
            + [total_dev_str, total_figs_dev_str, f"{stats.avg_misses_per_station:.2f}", trend_str]
        )
        table_data.append(row)

    table = tabulate(table_data, headers=headers, tablefmt="grid", stralign="left", numalign="right")
    output.append(table)
    output.append("")

    if len(sorted_years) > 1:
        trend = calculate_field_trend(yearly_stats_dict)
        first_year = sorted_years[0]
        last_year = sorted_years[-1]
        total_change = yearly_stats_dict[last_year].avg_hits - yearly_stats_dict[first_year].avg_hits
        progression_line = (
            f"Overall: Total: {total_change:+.1f} hits | "
            f"Trend: {trend:+.1f} hits/year "
            f"{'⬆️' if trend > 0 else '⬇️' if trend < 0 else '➡️'}"
        )
        output.append(progression_line)
        output.append(
            "Note: Δ = deviation from std medal winners (positive = above, negative = below). "
            "— = no std medal winner data available."
        )

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
    print("Competition Types: Precision, Militär snabbmatch, Fält, Poängfält", file=sys.stderr)
    print(file=sys.stderr)

    # Fetch Precision/Military results
    results_by_year = _fetch_all_results_for_years(years_to_fetch, card)

    # Fetch Field results (all competition results for medal deviation calculation)
    field_results_by_year = fetch_field_competition_results(years_to_fetch, card, show_progress=True)

    if not results_by_year and not field_results_by_year:
        print(f"No results found for card {card} in years {years_to_fetch}", file=sys.stderr)
        return

    # --- Precision / Military stats ---
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

    for type_group_key in sorted(type_group_yearly_stats.keys()):
        yearly_stats_dict = type_group_yearly_stats[type_group_key]
        section = _format_yearly_section(type_group_key, yearly_stats_dict)
        print(section)

    # --- Field stats ---
    # Group by weapon group (weapon_class first char) across years
    field_type_group_yearly: Dict[str, Dict[int, FieldYearlyStats]] = defaultdict(dict)

    for year, comp_data_list in sorted(field_results_by_year.items()):
        # Group by competition type + weapon group
        grouped_field: Dict[str, list] = defaultdict(list)
        for my_result, medal_results in comp_data_list:
            weapon_group = get_weapon_group(my_result.signup.weapon_class) if my_result.signup else "?"
            # Determine type label from competition type (we need it from context)
            # Use result's station count to infer nothing - just group by weapon group
            key = f"Fält/Poängfält - Weapon Group {weapon_group}"
            grouped_field[key].append((my_result, medal_results))

        for key, comp_data in grouped_field.items():
            field_stats = calculate_field_yearly_stats(comp_data, year)
            if field_stats:
                field_type_group_yearly[key][year] = field_stats

    for key in sorted(field_type_group_yearly.keys()):
        section = _format_field_yearly_section(key, field_type_group_yearly[key])
        print(section)

    print()
    print("Note: Only showing weapon groups where you competed.", file=sys.stderr)


def get_single_field_competition_analysis(competition_id: int, card: str) -> None:
    """Display single Field competition using the same format as yearly stats.

    Shows station deviations from std medal winners in tabular format.
    Only available for Field competitions. Handles multiple weapon classes (e.g., C3 and A3).

    Args:
        competition_id: Competition ID to analyze
        card: Shooting card number
    """
    print(f"Fetching competition {competition_id}...", file=sys.stderr)

    competition = get_competition(competition_id)

    if competition.type not in (CompetitionType.FIELD, CompetitionType.POINTFIELD):
        print(
            f"Error: Competition {competition_id} is type '{competition.type.display_name}'. "
            "Single competition analysis is only available for Field (Fält/Poängfält) competitions.",
            file=sys.stderr,
        )
        return

    print(f"Fetching results for competition {competition_id}...", file=sys.stderr)
    all_results = get_results(competition_id=competition_id)

    my_results: List[FieldResult] = []
    medal_winners: List[FieldResult] = []

    for result in all_results:
        if not isinstance(result, FieldResult):
            continue
        if result.signup.shooting_card_number == card:
            my_results.append(result)
        elif result.calculated_std_medal is not None:
            medal_winners.append(result)

    if not my_results:
        print(f"No result found for card {card} in competition {competition_id}.", file=sys.stderr)
        return

    if not medal_winners:
        print("\nNo std medal winner data available for this competition.")
        return

    # Print header info (use first result for competition details)
    comp_date_year = competition.competition_date.year
    print(f"\nCompetition: {competition.name} ({comp_date_year})")
    print(f"Type: {competition.type.display_name}")

    # Display a table for each weapon class
    for my_result in my_results:
        num_stations = len(my_result.stations)
        my_total_hits = sum(s.hits for s in my_result.stations)
        my_total_figures = sum(s.figure_hits or 0 for s in my_result.stations)

        print(f"\nWeapon Class: {my_result.signup.weapon_class}")
        medal_str = f", Medal: {my_result.calculated_std_medal.display_name}" if my_result.calculated_std_medal else ""
        print(
            f"Your Result: {my_total_hits} hits, {my_total_figures} figures, Placement: {my_result.placement}{medal_str}"
        )

        # Calculate deviations using same logic as yearly stats
        station_deviations, total_deviation, total_figures_deviation = calculate_field_station_deviations(
            my_result, medal_winners
        )

        # Calculate misses per station
        avg_hits_per_station = my_total_hits / num_stations if num_stations > 0 else 0
        avg_misses_per_station = 6.0 - avg_hits_per_station

        # Build single-row stats using same format as yearly stats
        max_stations = max(station_deviations.keys(), default=0)
        station_headers = [f"Sta{i}Δ" for i in range(1, max_stations + 1)]

        # Build row data
        station_devs = []
        for station_pos in range(1, max_stations + 1):
            if station_pos in station_deviations:
                dev = station_deviations[station_pos]
                station_devs.append(f"{dev:+.1f}")
            else:
                station_devs.append("—")

        total_dev_str = f"{total_deviation:+.1f}"
        total_figs_dev_str = f"{total_figures_deviation:+.1f}"

        row = (
            [
                competition_id,
            ]
            + station_devs
            + [total_dev_str, total_figs_dev_str, f"{avg_misses_per_station:.2f}"]
        )

        # Format table for single competition (no Year, no Trend)
        headers = ["Comp ID"] + station_headers + ["TotalΔ", "FigsΔ", "Miss/Sta"]
        table_data = [row]

        print()
        print(tabulate(table_data, headers=headers, tablefmt="grid", stralign="left", numalign="right"))

    # Note about deviations (shown once at the end)
    print("\nNote: Δ = deviation from std medal winners (positive = above, negative = below).")
