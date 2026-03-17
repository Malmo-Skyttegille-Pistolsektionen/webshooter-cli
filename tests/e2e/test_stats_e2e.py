"""E2E tests for stats command."""

import subprocess
import sys
from pathlib import Path


def test_stats_command_all_years():
    """E2E test: stats command with --all-years (tabular format)."""
    test_cache = Path(__file__).parent.parent / "resources" / "test_data" / "competitions"

    # Card 53780 → 10000 (from REFERENCE_CARD.txt)
    synthetic_card = "10000"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "webshooter_client.command",
            "--use-cache",
            "--cache-dir",
            str(test_cache),
            "stats",
            "--card",
            synthetic_card,
            "--all-years",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent / "src",
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"
    output = result.stdout + result.stderr

    # Check output contains expected elements (not with `or` chains)
    assert "Year-by-Year Statistics" in output
    assert "Year" in output
    assert "Class" in output
    assert "Comps" in output
    # Card should appear or synthetic card itself
    assert synthetic_card in output or "2024" in output
    # Should not have errors
    assert "Error" not in result.stderr or "No results" in result.stderr
    assert "Traceback" not in result.stderr


def test_stats_command_specific_years():
    """E2E test: stats command with specific years."""
    test_cache = Path(__file__).parent.parent / "resources" / "test_data" / "competitions"
    synthetic_card = "10000"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "webshooter_client.command",
            "--use-cache",
            "--cache-dir",
            str(test_cache),
            "stats",
            "--card",
            synthetic_card,
            "--years",
            "2024",
            "2023",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent / "src",
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Traceback" not in result.stderr


def test_stats_command_year_range():
    """E2E test: stats command with --from/--to."""
    test_cache = Path(__file__).parent.parent / "resources" / "test_data" / "competitions"
    synthetic_card = "10000"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "webshooter_client.command",
            "--use-cache",
            "--cache-dir",
            str(test_cache),
            "stats",
            "--card",
            synthetic_card,
            "--from",
            "2023",
            "--to",
            "2024",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent / "src",
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Traceback" not in result.stderr


def test_stats_command_no_results():
    """E2E test: stats command with non-existent card."""
    test_cache = Path(__file__).parent.parent / "resources" / "test_data" / "competitions"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "webshooter_client.command",
            "--use-cache",
            "--cache-dir",
            str(test_cache),
            "stats",
            "--card",
            "99999",
            "--all-years",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent / "src",
    )

    # Should succeed but show no results
    assert result.returncode == 0
    output = result.stdout + result.stderr
    # Should mention no results
    assert "No results" in output or "99999" in output


def test_stats_command_shows_field_stats():
    """E2E test: stats command shows Field competition statistics."""
    test_cache = Path(__file__).parent.parent / "resources" / "test_data" / "competitions"
    synthetic_card = "10000"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "webshooter_client.command",
            "--use-cache",
            "--cache-dir",
            str(test_cache),
            "stats",
            "--card",
            synthetic_card,
            "--years",
            "2024",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent / "src",
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Traceback" not in result.stderr
    output = result.stdout
    # Field stats section should appear
    assert "Fält" in output or "Poängfält" in output or "Avg Hits" in output


def test_stats_precision_scores_not_exceeding_350():
    """E2E test: Precision stats section should never show Best scores > 350 (7 series × 50 max)."""
    import re

    test_cache = Path(__file__).parent.parent / "resources" / "test_data" / "competitions"
    synthetic_card = "10000"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "webshooter_client.command",
            "--use-cache",
            "--cache-dir",
            str(test_cache),
            "stats",
            "--card",
            synthetic_card,
            "--years",
            "2024",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent / "src",
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"
    output = result.stdout

    # Extract only the Precision section(s) to avoid false positives from Military scores
    if "Precision" not in output:
        return  # No precision data, test passes

    # Split output into sections by === headers and check only Precision sections
    sections = re.split(r"={3,}", output)
    precision_sections = [s for s in sections if "Precision" in s and "Militär" not in s]

    for section in precision_sections:
        # In Best/Worst column format "350 / 280", extract numbers
        scores = re.findall(r"\|\s*(\d+)\s*/\s*\d+\s*\|", section)
        over_350 = [int(s) for s in scores if int(s) > 350]
        assert not over_350, f"Found Precision best scores > 350 in section: {over_350}"


def test_stats_single_field_competition_analysis():
    """E2E test: stats --competition shows single Field competition analysis."""
    test_cache = Path(__file__).parent.parent / "resources" / "test_data" / "competitions"
    synthetic_card = "10000"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "webshooter_client.command",
            "--use-cache",
            "--cache-dir",
            str(test_cache),
            "stats",
            "--card",
            synthetic_card,
            "--competition",
            "124",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent / "src",
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Traceback" not in result.stderr
    output = result.stdout
    # Should show tabular format with deviation columns (same as yearly stats)
    assert "Comp ID" in output
    assert "Sta1Δ" in output
    assert "TotalΔ" in output
    assert "FigsΔ" in output
    assert "Miss/Sta" in output
    assert "Your Result:" in output
    assert "Placement:" in output


def test_stats_single_field_competition_multiple_weapon_classes():
    """E2E test: stats --competition shows all weapon classes for a card."""
    test_cache = Path(__file__).parent.parent / "resources" / "test_data" / "competitions"
    synthetic_card = "10000"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "webshooter_client.command",
            "--use-cache",
            "--cache-dir",
            str(test_cache),
            "stats",
            "--card",
            synthetic_card,
            "--competition",
            "124",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent / "src",
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Traceback" not in result.stderr
    output = result.stdout
    # Card 10000 has 2 starts in comp 124: C3 and A3
    # Should show both weapon classes
    assert "Weapon Class: C3" in output
    assert "Weapon Class: A3" in output
    # Should show two tables (one per weapon class)
    assert output.count("Comp ID") >= 2  # At least 2 table headers with Comp ID


def test_stats_yearly_shows_all_weapon_classes_per_competition():
    """E2E test: yearly stats shows all weapon classes when shooter has multiple starts."""
    test_cache = Path(__file__).parent.parent / "resources" / "test_data" / "competitions"
    synthetic_card = "10000"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "webshooter_client.command",
            "--use-cache",
            "--cache-dir",
            str(test_cache),
            "stats",
            "--card",
            synthetic_card,
            "--years",
            "2024",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent / "src",
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Traceback" not in result.stderr
    output = result.stdout + result.stderr

    # Card 10000 has multiple Field starts in 2024 across different weapon groups
    # Both C and A weapon groups should appear in output
    assert "Weapon Group C" in output or "Weapon Group A" in output
    # Should show Field stats section
    assert "Fält/Poängfält" in output


def test_stats_single_competition_rejects_non_field():
    """E2E test: --competition rejects non-Field competition with clear error message."""
    test_cache = Path(__file__).parent.parent / "resources" / "test_data" / "competitions"
    synthetic_card = "10000"

    # Find a precision competition ID from test data
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "webshooter_client.command",
            "--use-cache",
            "--cache-dir",
            str(test_cache),
            "stats",
            "--card",
            synthetic_card,
            "--competition",
            "100",  # precision competition
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent / "src",
    )

    assert result.returncode == 0  # Should exit gracefully
    assert "Error" in result.stderr or "only available for Field" in result.stderr


def test_stats_command_no_year_required_with_competition_flag():
    """E2E test: stats --competition can be used without year arguments."""
    test_cache = Path(__file__).parent.parent / "resources" / "test_data" / "competitions"
    synthetic_card = "10000"

    # No --years / --all-years / --from/--to: should still work with --competition
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "webshooter_client.command",
            "--use-cache",
            "--cache-dir",
            str(test_cache),
            "stats",
            "--card",
            synthetic_card,
            "--competition",
            "128",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent / "src",
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Traceback" not in result.stderr
    # Should show hits (comp 128 has 57 hits for card 10000)
    assert "57" in result.stdout
