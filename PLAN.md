# Implementation Plan: Statistics Features

This document tracks the implementation of statistics features for the webshooter CLI client.

## Issues Overview

- **Issue #56**: Test Data Infrastructure (test data + integration tests)
- **Issue #54**: Statistics in Bests Command
- **Issue #55**: Year-by-Year Statistics Comparison Command

## Implementation Order

1. **Issue #56** - MUST DO FIRST (creates test infrastructure)
2. **Issue #54** - Second (creates statistics functions)
3. **Issue #55** - Third (uses statistics functions from #54)

---

## Issue #56: Test Data Infrastructure

**Status:** IN PROGRESS  
**Branch:** TBD  
**PR:** TBD

### Objectives

1. Create comprehensive anonymized test data from cached files
2. Organize test data by year (2022-2025)
3. Create integration tests that run CLI commands
4. Replace existing 14 test JSON files with complete dataset

### Critical Requirements

#### GDPR & Privacy Compliance ⚠️

**REMOVE completely:**
- Phone numbers, emails, addresses
- Personal notes/comments
- Birth dates, contact info
- Anything not needed for testing

**ANONYMIZE (keep for testing):**
- Shooter names → "Shooter_XXXXX"
- Club names → "Club_001", "Club_002"
- Card numbers (needed for filtering logic)

**KEEP unchanged:**
- Performance data (points, series, placements)
- Competition dates, types, weapon classes

### Step 0: Verify Cache Completeness

**CRITICAL:** Tests cannot make API calls (no valid token), must rely entirely on cached data.

```bash
# Populate cache for all years (if not already complete)
webshooter --use-cache competitions 2022
webshooter --use-cache competitions 2023
webshooter --use-cache competitions 2024
webshooter --use-cache competitions 2025

webshooter --use-cache bests 2022 --card 53780
webshooter --use-cache bests 2023 --card 53780
webshooter --use-cache bests 2024 --card 53780
webshooter --use-cache bests 2025 --card 53780
```

### Implementation Tasks

- [ ] Step 0: Verify cache completeness (~295 files in ~/.cache/webshooter/)
- [ ] Create anonymization script: `scripts/anonymize_test_data.py`
- [ ] Test anonymization on sample data
- [ ] Run anonymization on all cached files
- [ ] Verify no PII remains
- [ ] Delete existing `tests/resources/test_data/` (14 old files)
- [ ] Copy anonymized data to `tests/resources/test_data/competitions/`
- [ ] Organize by year structure
- [ ] Create `tests/integration/` directory
- [ ] Create integration test: `tests/integration/test_bests_integration.py`
- [ ] Update unit tests for new structure
- [ ] **Run all tests: `hatch run dev:pytest tests`**
- [ ] Verify tests pass offline (no API calls)
- [ ] Run `hatch run lint:black src tests`
- [ ] Run `hatch run lint:flake8`
- [ ] Commit with GPG signing
- [ ] Create PR (link to Issue #56)
- [ ] ❌ DO NOT MERGE

### Target Test Structure

```
tests/
├── unit/              # Existing unit tests (updated)
├── integration/       # NEW: Integration tests
│   ├── test_bests_integration.py
│   └── test_stats_integration.py (for later)
└── resources/
    └── test_data/
        └── competitions/
            ├── 2022/
            │   ├── competitions_2022.json
            │   └── competition_XX/
            │       ├── competition_XX.json
            │       └── competition_XX_results.json
            ├── 2023/
            ├── 2024/
            └── 2025/
```

### Integration Test Example

```python
# tests/integration/test_bests_integration.py
from pathlib import Path
import subprocess

def test_bests_command_2024():
    """Integration test: bests command with test data."""
    test_cache = Path(__file__).parent.parent / "resources" / "test_data" / "competitions"
    
    result = subprocess.run(
        ["webshooter", "--cache-dir", str(test_cache),
         "bests", "2024", "--card", "53780"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    assert "Personal Bests" in result.stdout
```

---

## Issue #54: Statistics in Bests Command

**Status:** PENDING (after #56)  
**Branch:** TBD  
**PR:** TBD

### Objectives

Add comprehensive statistics summary after each weapon class in `bests` command output.

### Statistics to Calculate

#### Overall Statistics (ALL results for weapon class/year)
- Total competitions
- Average score ± standard deviation
- Median score
- Best/Worst scores
- Average Xs (inner tens)

#### Top N Statistics (only displayed top results)
- Average score ± standard deviation
- Median score
- Average Xs

**Why both?** Gap between overall and top-N shows consistency:
- Small gap = consistent performer
- Large gap = inconsistent with occasional peaks

#### Series Analysis
- Average points per series position (1-7 for Precision, 1-12 for Military)
- Highlight strongest series (✨)
- Highlight weakest series (⚠️)

### Example Output

```
=== Precision - C3 ===
Rank  Points  Xs  Date        Competition                          Series
----  ------  --  ----------  ----------------------------------  -------------------
   1     325   8  2024-07-10  Pistol-SM 2024                      47 48 46 47 48 46 43
   ...
  10     301   3  2024-03-15  Spring Competition                  42 43 41 44 43 45 43

=== Overall Statistics: Precision - C3 (All 15 results) ===
Total Competitions: 15
Average Score:      305.2 ± 14.3 (std dev)
Median Score:       308
Best Score:         325
Worst Score:        275
Average Xs:         4.1

=== Top 10 Statistics: Precision - C3 ===
Average Score:      312.8 ± 8.5 (std dev)
Median Score:       314
Average Xs:         5.2

Series Analysis (all 15 results):
  Series 1: Avg 44.2
  Series 2: Avg 43.8
  Series 3: Avg 42.1 ⚠️ (weakest)
  Series 4: Avg 43.5
  Series 5: Avg 44.0
  Series 6: Avg 43.9 ✨ (strongest)
  Series 7: Avg 43.3
```

### Implementation Tasks

- [ ] Import statistics modules: `from statistics import mean, median, stdev`
- [ ] Implement `_calculate_statistics(personal_bests: List[PersonalBest]) -> Dict[str, Any]`
- [ ] Implement `_calculate_series_averages(personal_bests: List[PersonalBest]) -> List[float]`
- [ ] Implement `_format_statistics_section(type_class: str, all_results: List, top_results: List)`
- [ ] Update `get_personal_bests()` to call stats after each weapon class
- [ ] Handle edge cases: single result (no std dev), empty series data
- [ ] Test manually with: `webshooter --use-cache bests 2024 --card 53780`
- [ ] Test with: `webshooter --use-cache bests 2022 --card 53780`
- [ ] **Run all tests: `hatch run dev:pytest tests`**
- [ ] Run `hatch run lint:black src tests`
- [ ] Run `hatch run lint:flake8`
- [ ] Commit with GPG signing
- [ ] Create PR (link to Issue #54)
- [ ] ❌ DO NOT MERGE

### Files to Modify

- `src/webshooter_client/commands/bests.py` - Add statistics functions and formatting

---

## Issue #55: Year-by-Year Statistics Command

**Status:** PENDING (after #54)  
**Branch:** TBD  
**PR:** TBD

### Objectives

Create new `stats` command for year-by-year comparison and trend analysis.

### Command Interface

```bash
# Specific years
webshooter stats --card 53780 --years 2022,2023,2024

# Year range
webshooter stats --card 53780 --from 2022 --to 2024

# All available years
webshooter stats --card 53780 --all-years
```

### Key Features

#### Weapon Group Progression Tracking

Shooters progress through classes (C1→C2→C3) or regress (C3→C2). Track within weapon groups (A, C, R, B).

**Separate Precision and Military completely.**

#### Example Output

```
=== Precision - Weapon Group C ===
2022: C1              - Avg 280.5, 8 competitions
2023: C2              - Avg 295.2, 10 competitions (+14.7 points, +5.2%)
2024: C3              - Avg 312.4, 12 competitions (+17.2 points, +5.8%)

Overall Progression: C1→C2→C3
Total Improvement: +31.9 points over 3 years (+11.4%)
Trend: +10.6 points/year ⬆️

=== Militär snabbmatch - Weapon Group C ===
2022: C2              - Avg 520.3, 6 competitions
2023: C3              - Avg 535.8, 8 competitions (+15.5 points, +3.0%)
2024: C3              - Avg 545.2, 10 competitions (+9.4 points, +1.8%)

Overall Progression: C2→C3
Total Improvement: +24.9 points over 3 years (+4.8%)
Trend: +8.3 points/year ⬆️
```

**Note:** NO annotations like "(rookie)", "(improved)" - just show clean class names (C1, C2, C3).

### Statistics Per Year

- Total competitions
- Average score ± std dev
- Median score
- Best/worst scores
- Average Xs
- Weapon class used that year

### Trend Analysis

- Year-over-year changes (absolute + percentage)
- Overall improvement rate (points/year)
- Class progression visualization (C1→C2→C3→C2)
- Consistency trends (std dev changes)

### Implementation Tasks

- [ ] Create new file: `src/webshooter_client/commands/stats.py`
- [ ] Add `stats` subcommand to `command.py`
- [ ] Implement year selection logic (--years, --from/--to, --all-years)
- [ ] Implement weapon group detection (A, C, R, B from class like C1, C2, C3)
- [ ] Implement class progression tracking (bidirectional: up and down)
- [ ] Reuse statistics functions from bests.py
- [ ] Implement year-by-year comparison
- [ ] Implement trend calculation (points/year)
- [ ] Separate Precision and Military output
- [ ] Test manually with: `webshooter --use-cache stats --card 53780 --years 2022,2023,2024`
- [ ] **Run all tests: `hatch run dev:pytest tests`**
- [ ] Create integration test: `tests/integration/test_stats_integration.py`
- [ ] Run `hatch run lint:black src tests`
- [ ] Run `hatch run lint:flake8`
- [ ] Commit with GPG signing
- [ ] Create PR (link to Issue #55)
- [ ] ❌ DO NOT MERGE

### Files to Create/Modify

- `src/webshooter_client/commands/stats.py` - NEW file
- `src/webshooter_client/command.py` - Add stats subcommand

---

## Critical Rules ⚠️

### Before Every Commit

1. **Run tests**: `hatch run dev:pytest tests`
2. **Format code**: `hatch run lint:black src tests`
3. **Lint code**: `hatch run lint:flake8`
4. **GPG sign commit**: `git commit -S -m "message"`

### Testing Guidelines

- **Always use `--use-cache`** for manual testing (avoid API load)
- **Integration tests use `--cache-dir`** to point to test data
- **Tests must work offline** (no API calls, no token)

### PR Guidelines

- Create PR with link to issue (e.g., "Closes #56")
- ❌ **NEVER merge PRs**
- ❌ **NEVER merge to main/master**
- ✅ User will merge all PRs

---

## Commands Reference

### Testing
```bash
# Run all tests
hatch run dev:pytest tests

# Run specific test
hatch run dev:pytest tests/integration/test_bests_integration.py

# Run with coverage
hatch run dev:pytest tests -v --cov=src/webshooter_client
```

### Linting
```bash
# Format with Black
hatch run lint:black src tests

# Check formatting
hatch run lint:black --check src tests

# Lint with flake8
hatch run lint:flake8
```

### Manual Testing (with cache)
```bash
# Bests command
webshooter --use-cache bests 2024 --card 53780

# Stats command (after #55)
webshooter --use-cache stats --card 53780 --years 2022,2023,2024

# With custom cache dir (for testing)
webshooter --cache-dir tests/resources/test_data/competitions bests 2024 --card 53780
```

### Git
```bash
# Create branch
git checkout -b feature/branch-name

# Commit with GPG signing
git add .
git commit -S -m "feat(scope): message"

# Push
git push -u origin feature/branch-name
```

---

## Progress Tracking

- [x] Issue #56 - Test Data Infrastructure ✅ COMPLETE
- [ ] Issue #54 - Statistics in Bests
- [ ] Issue #55 - Year-by-Year Stats Command

Last Updated: 2026-02-14

---

## Execution Rules

### Progress Reporting
- Provide status updates periodically during long tasks
- Update PLAN.md checkboxes as tasks complete
- Keep user informed of progress

### Token Management
- Monitor token usage during implementation
- **STOP if approaching 10% remaining (900,000 tokens used)**
- Provide summary of what's done and what's next

### Working Style
- Tick off `- [ ]` → `- [x]` in PLAN.md as tasks complete
- Edit PLAN.md to reflect current status
- Report "Progress Update" messages for long-running work

---

## Branching Strategy (No Merge Conflicts)

**Key:** All branches created from current master (before any merges)

### Issue #56: `feat/test-data-infrastructure`
**Files affected:**
- `tests/` directory (new structure)
- `scripts/anonymize_test_data.py` (new)
- Delete old test data
- No src/ files modified

### Issue #54: `feat/bests-statistics`
**Files affected:**
- `src/webshooter_client/commands/bests.py` (modify)
- No test structure changes
- No other src/ files

### Issue #55: `feat/stats-command`
**Files affected:**
- `src/webshooter_client/commands/stats.py` (new file)
- `src/webshooter_client/command.py` (add stats subcommand)
- No modification to bests.py

**Result:** Zero file conflicts between branches!
- Each PR touches different files
- Can be merged in any order (though logical: 56→54→55)
- All branches from same master commit

