# Agent Guide: Webshooter Client Development

This document provides essential context for agents working on the Webshooter client project.

---

## ⚠️ BEFORE YOU COMMIT: Mandatory Quality Gates

**Every commit must pass these checks:**

1. **Format code with Black**
   ```bash
   hatch run black src tests
   ```

2. **Lint with Flake8**
   ```bash
   hatch run flake8 src tests
   ```
   (Output should be empty if passing)

3. **Run all tests**
   ```bash
   hatch test
   ```
   (All tests must pass; 0 failures)

4. **Quick validation script**
   ```bash
   hatch run black src tests && hatch run flake8 src tests && hatch test && echo "✅ All checks passed"
   ```

**If any check fails**: Fix the issues, don't commit. See [Running Lints & Format](#running-lints--format---required-before-commit) section for detailed guidance.

---

## Quick Reference: Standard Test Parameters

Use these parameters for consistent testing across unit, E2E, and manual tests:

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Test Card (Synthetic)** | 10008 | Anonymized from real card 53780 |
| **Test Card (Real)** | 53780 | Real shooter data, requires GDPR handling |
| **Test Club** | 12-239 | Malmö Skyttegille Pistolsektionen |
| **Test Years** | 2022-2025 | Available in cached test data |
| **Test Data Cache** | `tests/resources/test_data/competitions/` | Use with `--use-cache --cache-dir` |
| **Precision Max** | 350 points | 7 series × 50 points (validation rule) |
| **Military Series** | 12 | Standard military series count |

**Command Template**:
```bash
# With test data (fastest, no API calls)
python -m webshooter_client.command \
  --use-cache \
  --cache-dir tests/resources/test_data/competitions/ \
  <command> --card 10008 <options>

# With real API (requires token)
webshooter <command> --card 53780 <options>
```

---

## Project Overview

**Webshooter** is a Python CLI client for interacting with WebShooter.se (Swedish shooting competition platform).

### Key URLs
- Main platform: https://webshooter.se
- API: Webshooter.se API v4.1.9
- Repository: https://github.com/frazz/webshooter

---

## Critical Technical Knowledge

### Precision Competition Filtering ⚠️ CRITICAL RULE

**ONLY use precision competitions with EXACTLY 7 series. Finals are stored separately and increase `result.points` but NOT the series list.**

#### The Key Insight
- **`result.series`** = The 7 base series (or 6, 8, 9, 10 depending on format)
- **`result.points`** = Includes finals if present (can be 350+ if finals added)
- **Finals are NOT in `result.series`** - they're stored elsewhere but added to `result.points`

#### Filtering Rule (From bests.py - PROVEN WORKING)
```python
# From bests.py lines 57-63 (WORKING IMPLEMENTATION)
if isinstance(result, PrecisionResult):
    if len(result.series) != 7:
        return None
    # Use series sum, not total points (which may include finals)
    points = sum(s.points for s in result.series)
```

**This is the EXACT pattern to use for both bests and stats.**

#### Why This Works
1. **Check 1**: `len(result.series) == 7` filters non-standard (6, 8, 9, 10 series)
2. **Check 2**: `sum(s.points for s in result.series)` automatically excludes finals
   - Finals are NOT in the series list
   - By summing only series, finals are excluded
   - Max for 7-series: 7 × 50 = 350 points

#### How to Handle (Code Pattern)
```python
# ✅ CORRECT: This is what bests.py does (PROVEN)
if len(result.series) == 7:
    points = sum(s.points for s in result.series)
    # points will be ≤ 350
    # Finals excluded because they're not in series list

# ❌ WRONG: Using result.points
points = result.points  # Includes finals! Can be 452+

# ❌ WRONG: Using >= 7
if len(result.series) >= 7:  # Could be 8, 9, 10+ series
    points = sum(s.points for s in result.series[:7])
```

#### Real World Example: Competition 259 (B3, Card 53780)
- **Format**: 7-series base competition with 3-series finals added
- `len(result.series) = 7` (only base series) ✓
- `result.points = 452` (includes 3 finals series worth ~102 points)
- `sum(result.series) = 350` (only the 7 base series)
- **Correct handling**: Use `sum(result.series) = 350` NOT `result.points = 452`
- **Key observation**: Finals increase `result.points` but NOT the `result.series` list

#### Stats Command Bug (Current)
- stats.py uses `result.points` for precision scores → includes finals → 452 shows up
- **Fix**: Use `sum(result.series)` like bests.py does → only 350

#### Military Competitions
- Military: Use `result.points` (no finals in military)
- No special filtering needed beyond having series data

#### Commands Affected
- `bests`: Currently CORRECT - checks `len(result.series) == 7` before using points
- `stats`: Currently BUGGY - filtering exists but may not enforce it properly

### Military Competition Filtering

**Military competitions** use all available series (typically 12).
- Accept any Military result with series data
- Use `result.points` directly (already correct)
- No series count validation needed

### Standard Medals (Silver & Bronze)

**Standard medals** are the two qualification levels in Swedish shooting competitions:
- **Silver (S)** - Higher qualification threshold
- **Bronze (B)** - Lower qualification threshold
- Awarded per competition result when a shooter meets the threshold
- NOT the same as final placements (1st, 2nd, 3rd place)

**Key Facts:**
- Only two medal levels exist: Silver and Bronze (no Gold)
- In models: `StdMedal` enum with `SILVER` and `BRONZE` values
- In results: `result.std_medal` contains the medal earned, or `None` if no medal
- Tracked by: `medals` command (counts total per shooter/club/type)
- `result.std_medal: Optional[StdMedal]` - can be None if no medal earned

### Competition Type Detection

```python
from webshooter_client.models.result import PrecisionResult, MilitaryResult

if isinstance(result, PrecisionResult):
    # Apply 7-series filtering
    if len(result.series) != 7:
        skip_result()
    points = sum(s.points for s in result.series)
elif isinstance(result, MilitaryResult):
    # Accept any result
    points = result.points
```

---

## Architecture Patterns

### Competition Validation

**Current State**: Each command has inline filtering logic.

**Desired State**: Extract to shared utility module `src/webshooter_client/common/competition_filter.py`

```python
# Proposed utility functions
def is_valid_precision_result(result: PrecisionResult) -> bool:
    """Only True if exactly 7 series (no finals)."""
    return len(result.series) == 7

def is_valid_military_result(result: MilitaryResult) -> bool:
    """True for any military result with series."""
    return result.series is not None

def get_result_points(result: ResultBase) -> int:
    """Get correct points, handling finals correctly."""
    if isinstance(result, PrecisionResult):
        return sum(s.points for s in result.series)
    else:
        return result.points
```

### Commands Architecture

#### Bests Command (`src/webshooter_client/commands/bests.py`)
- Lists personal best results per weapon class
- Line 59-63: **Correct** filtering for 7-series precision
- Should be refactored to use shared utility

#### Stats Command (`src/webshooter_client/commands/stats.py`)
- Year-by-year progression analysis
- Line 58-63: Has filtering but implementation unclear
- **BUG**: Shows 452+ scores for precision (violates max 350 rule)
- Should use shared utility to fix

#### Medals Command (`src/webshooter_client/commands/medals.py`)
- Counts standard medals earned (per card or club)
- **Standard Medals**: Silver (S) and Bronze (B) only - NOT gold/silver/bronze
- Displays medals per competition type and shooter
- Optional year filtering to show medals by year
- Format: Card Number, Name, Competition Type, Silver Count, Bronze Count

#### Cache System
- Automatic caching to `~/.cache/webshooter` (XDG compliant)
- `--use-cache` flag to use cached data
- `--cache-dir` to override cache location
- `--clear-cache` to delete cache

---

## Test Data & Examples

### Test Data Location
```
tests/resources/test_data/competitions/
├── 2022/
├── 2023/
├── 2024/
└── 2025/
```

**Anonymization**: Real card 53780 → synthetic card 10008 (for GDPR compliance)
**Club**: 12-239 (Malmö Skyttegille Pistolsektionen)
**Years**: 2022-2025
**Contains**: Precision and Military competitions

### Test Data Reference

| Card | Real | Synthetic | Years | Club | Status |
|------|------|-----------|-------|------|--------|
| 53780 | Real shooter | 10008 | 2022-2025 | 12-239 | In test data |
| 53780 | Competition 259 | B3, 2024 | Precision bug example | — | Known issue |

### Known Good Examples

#### Competition 259 (B3, Card 53780) - **Precision Filtering Bug Example**
- **Location**: 2024 data
- **Shooter**: Shooter_10000 (card 53780)
- **Class**: B3
- **Points shown**: 452 (includes finals) ❌
- **Points should be**: 335 (7 series only) ✓
- **Series count**: 10 (has finals)
- **Purpose**: Test case for verifying series filtering
- **Status**: KNOWN BUG - should not appear in stats or show corrected points
- **Fix verification**: After fix, comp 259 should be filtered out OR show ≤350

#### Other Good Test Cases
- **2024 Precision A-class**: Standard 7-series competitions
- **2024-2025 Military**: 12-series competitions
- **Multi-year progression**: C1 → C2 → C3 class changes
- **Year gaps**: 2022 has fewer competitions than 2024

### Using Test Data

**Minimal test command**:
```bash
python -m webshooter_client.command \
  --use-cache \
  --cache-dir tests/resources/test_data/competitions/ \
  stats --card 10008 --all-years
```

**Verifying precision filtering fix**:
```bash
# Should show NO precision scores > 350
python -m webshooter_client.command \
  --use-cache \
  --cache-dir tests/resources/test_data/competitions/ \
  stats --card 10008 --years 2024

# Look for: "Best / Worst" columns in Precision - Weapon Group B
# Expected: All values ≤ 350
# Bug indicator: Any value > 350 means finals are included
```

---

## Code Style & Conventions

### Formatting
- **Line length**: 120 (Black), 125 (Flake8)
- **Tool**: Black formatter
- **Linter**: Flake8 (ignores W503)

### Type Hints
- Use throughout, including function returns
- Example: `def get_results(competition_id: int) -> List[ResultBase]:`

### Docstrings
- Use for all public functions
- Include Args, Returns, Raises sections
- Add examples for complex logic

### Error Handling
- Log to stderr (not stdout)
- Progress messages to stderr
- Output data to stdout only

---

## Development Workflow

### Running Tests

#### Unit Tests
```bash
# All unit tests
pytest tests/unit/

# Specific test module
pytest tests/unit/webshooter_client/stats/test_calculator.py

# Specific test function
pytest tests/unit/webshooter_client/stats/test_calculator.py::test_calculate_basic_stats_empty

# With verbose output
pytest tests/unit/ -v

# With coverage report
pytest tests/unit/ --cov=src/webshooter_client --cov-report=html
```

#### E2E Tests (Integration Tests)

**Prerequisites**: Requires cached test data in `tests/resources/test_data/competitions/`

**Test Data Available**:
- Years: 2022-2025
- Test card: 53780 (anonymized to 10008 in test data)
- Club: 12-239 (Malmö Skyttegille Pistolsektionen)
- Competition types: Precision, Military

```bash
# All E2E tests
pytest tests/e2e/ -v

# E2E tests for specific command
pytest tests/e2e/test_stats_e2e.py -v
pytest tests/e2e/test_bests_e2e.py -v

# E2E test for precision filtering bug
pytest tests/e2e/test_stats_e2e.py::test_stats_command_all_years -v
# Should show no precision scores > 350
```

#### Running Tests with Specific Data

**Test with cache (fastest, no API calls)**:
```bash
# Stats with all years 2022-2025
pytest tests/e2e/test_stats_e2e.py -v --use-cache

# Bests for 2024
pytest tests/e2e/test_bests_e2e.py -v --use-cache

# With specific card
pytest tests/e2e/ -v --card 10008 --use-cache
```

**Test with real API (requires token)**:
```bash
# Get token from browser local storage, then:
export WEBSHOOTER_TOKEN="your_token_here"

# Real card 53780
pytest tests/e2e/ -v --card 53780

# Year range 2023-2024
pytest tests/e2e/test_stats_e2e.py -v --from 2023 --to 2024
```

#### Manual Testing Commands

**With cached test data** (synthetic card 10008):
```bash
# Test stats command with all years
python -m webshooter_client.command \
  --use-cache \
  --cache-dir tests/resources/test_data/competitions/ \
  stats --card 10008 --all-years

# Test stats with year range
python -m webshooter_client.command \
  --use-cache \
  --cache-dir tests/resources/test_data/competitions/ \
  stats --card 10008 --from 2024 --to 2025

# Test bests for 2024
python -m webshooter_client.command \
  --use-cache \
  --cache-dir tests/resources/test_data/competitions/ \
  bests 2024 --card 10008 --top 5
```

**With real API** (card 53780, club 12-239):
```bash
# Export token first
export WEBSHOOTER_TOKEN="$(grep token ~/.webshooter.rc | cut -d' ' -f3)"

# Stats for all years
webshooter stats --card 53780 --all-years

# Stats for 2024-2025
webshooter stats --card 53780 --from 2024 --to 2025

# Bests for 2024
webshooter bests 2024 --card 53780 --top 10

# By club instead of card
webshooter bests 2024 --club 12-239
```

#### Testing Specific Bug Fix (Precision Filtering)

To verify Competition 259 B3 bug is fixed:

```bash
# Manual inspection (should NOT show 452 score)
python -m webshooter_client.command \
  --use-cache \
  --cache-dir tests/resources/test_data/competitions/ \
  stats --card 10008 --years 2024

# Look in output for:
# - Precision - Weapon Group B
# - Should show max ≤ 350 for any year
# - Competition 259 should not appear (or only with corrected points)
```

Unit test to add (verify fix):
```python
def test_precision_max_score_is_350():
    """Verify no precision results exceed 350 (7 series × 50 points)."""
    # Fetch stats, verify max(best_scores) <= 350
    assert all(stat.basic_stats.max_score <= 350 
               for stat in stats if "Precision" in stat.type_group_key)
```

### Running Lints & Format — **REQUIRED BEFORE COMMIT**

⚠️ **CRITICAL**: Linting and formatting MUST be run before committing. Non-compliant code will fail CI.

```bash
# Step 1: Format with Black (automatically fixes most issues)
hatch run black src tests

# Step 2: Check with Flake8 (catches remaining issues)
hatch run flake8 src tests

# Full validation: Format + Check in one command
hatch run black src tests && hatch run flake8 src tests && echo "✅ All checks passed"

# Optional: Check only (don't modify)
hatch run black --check src tests
hatch run flake8 src tests --statistics
```

**Configuration**:
- **Black line length**: 120 characters
- **Flake8 max line length**: 125 characters (allows 5-char overage for pragmatic cases)
- **Flake8 ignores**: W503 (line break before binary operator)

**Common issues to fix**:
- Unused imports → Remove or use with `# noqa` if intentional
- Long lines → Use parentheses to break across lines
- Trailing whitespace → Black removes automatically
- Multiple blank lines → Black normalizes to max 2
- Inconsistent spacing → Black standardizes

**When to NOT use `# noqa`**:
- DON'T silence linting issues — fix the root cause
- DON'T accumulate `# noqa` comments (indicates design problem)
- If an import is unused, remove it
- If a line is too long, refactor it

**Workflow checklist before pushing**:
- [ ] Run `hatch run black src tests`
- [ ] Run `hatch run flake8 src tests` (should output nothing if passing)
- [ ] Run `hatch test` (all tests pass)
- [ ] Review git diff to ensure formatting is intentional
- [ ] Commit with clear message

### Building & Installing
```bash
hatch build
pip install -e .
```

### Test Coverage Report
```bash
# Generate coverage
pytest tests/ --cov=src/webshooter_client --cov-report=html

# View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

---

## Common Pitfalls

1. **Using `result.points` for precision** → Includes finals, breaks filtering
2. **Not checking `result.series` length** → Allows non-standard competitions
3. **Forgetting stderr for progress** → Breaks output redirection
4. **Mixing military and precision rules** → Different validation logic needed
5. **Not using sum of series** → Precision calculations incorrect

---

## Recent Changes (as of 2026-02-15)

### PR #59: Tabular Stats Format
- Converted stats output to grid format (Option A: Years as Rows)
- Removed stats from bests command (deferred feature)
- Stats command now standalone with tabular output

### Current Issue: Precision Filtering Bug
- Stats shows 452-point scores (max should be 350)
- Plan: Extract filtering to shared utility module
- Both commands should use identical logic
- Example: Competition 259 B3 (card 53780)

---

## Useful Resources

- **API Documentation**: See BASE_URL constants in `src/webshooter_client/api/api_calls.py`
- **Models**: `src/webshooter_client/models/` for data structures
- **Configuration**: `~/.webshooter.rc` format in CLAUDE.md
- **Test Fixtures**: `tests/conftest.py` for fixture definitions

---

## Questions & Clarifications

When unsure:
1. Check CLAUDE.md for project conventions
2. Review similar code in bests/stats/results commands
3. Look at test examples in tests/unit/ and tests/e2e/
4. Verify with actual data before committing
