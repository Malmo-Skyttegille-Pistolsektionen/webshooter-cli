"""E2E tests for stats command."""

import subprocess
import sys
from pathlib import Path


def test_stats_command_all_years():
    """E2E test: stats command with --all-years (tabular format)."""
    test_cache = Path(__file__).parent.parent / "resources" / "test_data" / "competitions"

    # Card 53780 → 10008 (from REFERENCE_CARD.txt)
    synthetic_card = "10008"

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

    # Check output contains tabular format elements
    assert "Year-by-Year Statistics" in output or "Card" in output or "Year" in output
    assert synthetic_card in output or "2024" in output or "Precision" in output
    # Should show table header
    assert "Year" in output or "Class" in output or "Comps" in output
    # Should not have errors
    assert "Error" not in result.stderr or "No results" in result.stderr
    assert "Traceback" not in result.stderr


def test_stats_command_specific_years():
    """E2E test: stats command with specific years."""
    test_cache = Path(__file__).parent.parent / "resources" / "test_data" / "competitions"
    synthetic_card = "10008"

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
    synthetic_card = "10008"

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
