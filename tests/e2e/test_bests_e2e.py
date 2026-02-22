"""E2E tests for bests command."""

import subprocess
import sys
from pathlib import Path


def test_bests_command_2024():
    """E2E test: bests command with 2024 test data."""
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
            "bests",
            "2024",
            "--card",
            synthetic_card,
            "--top",
            "5",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent / "src",
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"
    # Check results are in output (stdout has tables, stderr has headers)
    output = result.stdout + result.stderr
    assert synthetic_card in output
    assert "2024" in output
    # Should not have errors
    assert "Error" not in result.stderr
    assert "Traceback" not in result.stderr


def test_bests_command_2023():
    """E2E test: bests command with 2023 test data."""
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
            "bests",
            "2023",
            "--card",
            synthetic_card,
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent / "src",
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"
    output = result.stdout + result.stderr
    assert synthetic_card in output or "2023" in output


def test_bests_command_no_results():
    """E2E test: bests command with non-existent card."""
    test_cache = Path(__file__).parent.parent / "resources" / "test_data" / "competitions"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "webshooter_client.command",
            "--use-cache",
            "--cache-dir",
            str(test_cache),
            "bests",
            "2024",
            "--card",
            "99999",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent / "src",
    )

    # Should succeed but show no results
    assert result.returncode == 0


def test_bests_command_shows_field_results():
    """E2E test: bests command shows Field competition results with hits column."""
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
            "bests",
            "2024",
            "--card",
            synthetic_card,
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent / "src",
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Traceback" not in result.stderr
    output = result.stdout
    # Field competitions should appear in separate table with hits column
    assert "Hits" in output
    assert "Figures" in output
    assert "Stations" in output


def test_bests_command_mixed_output_shows_both_sections():
    """E2E test: bests shows both series-based and field-based sections in same output."""
    test_cache = Path(__file__).parent.parent / "resources" / "test_data" / "competitions"
    synthetic_card = "10008"

    # Use a year known to have both Precision/Military AND Field results for card 10008
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "webshooter_client.command",
            "--use-cache",
            "--cache-dir",
            str(test_cache),
            "bests",
            "2024",
            "--card",
            synthetic_card,
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent / "src",
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Traceback" not in result.stderr
    output = result.stdout

    # Both sections should be present in the same output
    # Series-based: Points and Series columns
    assert "Points" in output
    assert "Series" in output
    # Field-based: Hits, Figures, Stations columns
    assert "Hits" in output
    assert "Figures" in output
    assert "Stations" in output
