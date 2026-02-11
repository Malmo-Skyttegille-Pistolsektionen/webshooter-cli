# API Documentation

This document describes how to interact with the Webshooter Client API programmatically.

## Overview

While Webshooter Client is primarily a CLI tool, its components can be used as a Python library for programmatic access to webshooter.se data.

## Installation

```bash
pip install webshooter-client
```

Or install from source:

```bash
git clone https://github.com/frazz/webshooter.git
cd webshooter
hatch build
pip install dist/webshooter_client-*.whl
```

## Configuration

Before using the API, you need a token from webshooter.se:

### Option 1: Configuration File

Create `~/.webshooter.rc`:

```ini
[global]
unicode = True
card = xx
club = aa-bbb
token = <your-token-here>
```

### Option 2: Programmatic Configuration

```python
from webshooter_client.common.application_config import ApplicationConfig

# Initialize config (singleton pattern)
config = ApplicationConfig()
config.token = "your-token-here"
config.verbose = True
```

**Getting your token:**
1. Log in to [webshooter.se](https://www.webshooter.se)
2. Open browser developer tools (F12)
3. Navigate to: Storage → Local Storage → token
4. Copy the token value

## API Reference

### Competitions

#### List All Competitions

```python
from webshooter_client.api.api_calls import get_competitions

# Get all competitions for a year
competitions = get_competitions(year=2026)

for comp in competitions:
    print(f"{comp.id}: {comp.name} - {comp.date} ({comp.type.display_name})")
```

**Output:**
```
283: Club Competition - 2026-01-15 (Militär snabbmatch)
284: Regional Precision - 2026-01-22 (Precision)
...
```

#### Get Single Competition

```python
from webshooter_client.api.api_calls import get_competition

# Get specific competition details
comp = get_competition(competition_id=283)

print(f"Name: {comp.name}")
print(f"Type: {comp.type.display_name}")
print(f"Date: {comp.date}")
print(f"Location: {comp.location}")
```

**Competition Object:**
```python
@dataclass(kw_only=True)
class Competition:
    id: int                      # Unique competition ID
    name: str                    # Competition name
    type: CompetitionType        # MILITARY, PRECISION, FIELD, or POINTFIELD
    date: str                    # ISO date format (YYYY-MM-DD)
    location: str                # Competition location
    organizer: str               # Organizing club/organization
    # ... additional fields
```

### Results

#### Get Competition Results

```python
from webshooter_client.api.api_calls import get_results

# Get all results for a competition
results = get_results(competition_id=283)

for result in results:
    print(f"{result.placement}. {result.signup.fullname} - {result.points} points")
```

**Result Types:**

Results vary by competition type:

**MILITARY/PRECISION** (series-based):
```python
from webshooter_client.models.result import MilitaryResult, PrecisionResult

# Military/Precision results have series
result: MilitaryResult = results[0]
print(f"Total points: {result.points}")
print(f"Series: {[s.points for s in result.series]}")
print(f"Inner tens: {sum(s.inner_tens for s in result.series)}")
```

**FIELD/POINTFIELD** (station-based):
```python
from webshooter_client.models.result import FieldResult

# Field results have stations
result: FieldResult = results[0]
print(f"Total points: {result.points}")
print(f"Stations: {[s.points for s in result.stations]}")
```

#### Filter Results by Club or Card

```python
from webshooter_client.api.api_calls import get_results

results = get_results(competition_id=283)

# Filter by club number
club_results = [r for r in results if r.signup.spsf_club_number == "12-239"]

# Filter by shooting card
card_results = [r for r in results if r.signup.shooting_card_number == "123456"]
```

### Signups

#### Get Competition Signups

```python
from webshooter_client.api.api_calls import get_signups

# Get all signups for a competition
signups = get_signups(competition_id=283)

for signup in signups:
    print(f"{signup.fullname} - {signup.weapon_class} ({signup.spsf_club_number})")
```

**Signup Object:**
```python
@dataclass(kw_only=True)
class Signup:
    shooting_card_number: str    # Shooter's card number
    fullname: str                # Full name
    spsf_club_number: str        # Club number (format: XX-XXX)
    weapon_class: str            # Specific weapon class
    weapon_class_general: str    # General class category
    # ... additional fields
```

### Patrols (Start Times)

#### Get Start Times

```python
from webshooter_client.api.api_calls import get_patrols

# Get all start time assignments
patrols = get_patrols(competition_id=283)

for patrol in patrols:
    print(f"Patrol {patrol.patrol_number} at {patrol.start_time}:")
    for shooter in patrol.shooters:
        print(f"  - {shooter['name']} (Lane {shooter['lane']})")
```

**Patrol Object:**
```python
@dataclass(kw_only=True)
class Patrol:
    patrol_number: int           # Patrol/relay number
    start_time: str              # Start time (HH:MM format)
    shooters: List[Dict]         # List of shooters with lane assignments
```

## Advanced Usage

### Using Formatters

Format results for display using the strategy pattern:

```python
from webshooter_client.api.api_calls import get_results, get_competition
from webshooter_client.commands.result_formatters import ResultFormatterFactory

# Get results
results = get_results(competition_id=283)
comp = get_competition(competition_id=283)

# Get appropriate formatter for competition type
formatter = ResultFormatterFactory.get_formatter(comp.type)

# Format and print results
formatter.format_and_print(results, club="12-239", card="")
```

### Using Parsers

Parse custom API data:

```python
from webshooter_client.api.result_parsers import ResultParserFactory
from webshooter_client.models.competition import CompetitionType

# Get parser for specific competition type
parser = ResultParserFactory.get_parser(CompetitionType.MILITARY)

# Parse raw API data
result_obj = parser.parse(raw_result_data, signup_obj)
```

### Custom Commands

Create custom commands by extending BaseCommand:

```python
from webshooter_client.commands.base_command import BaseCommand
from webshooter_client.api.api_calls import get_competitions
from tabulate import tabulate

class MyCustomCommand(BaseCommand):
    @staticmethod
    def execute(args):
        """Custom command implementation."""
        competitions = get_competitions(year=args.year)
        
        # Filter competitions by some criteria
        filtered = [c for c in competitions if "Regional" in c.name]
        
        # Format as table
        table_data = [[c.id, c.name, c.date] for c in filtered]
        print(tabulate(table_data, headers=["ID", "Name", "Date"]))
```

## Competition Types

The system supports four competition types:

```python
from webshooter_client.models.competition import CompetitionType

CompetitionType.MILITARY     # "Militär snabbmatch"
CompetitionType.PRECISION    # "Precision"
CompetitionType.FIELD        # "Fält"
CompetitionType.POINTFIELD   # "Poängfält"

# Access display names
print(CompetitionType.MILITARY.display_name)  # "Militär snabbmatch"
```

## Error Handling

The API uses a custom exception hierarchy:

```python
from webshooter_client.api.exceptions import (
    APIError,              # Base exception
    APIConnectionError,    # Network issues
    APITimeoutError,       # Request timeout
    APIHTTPError,         # HTTP errors (4xx, 5xx)
    DataValidationError   # Invalid API response
)

try:
    results = get_results(competition_id=283)
except APIConnectionError as e:
    print(f"Connection failed: {e}")
except APITimeoutError as e:
    print(f"Request timed out: {e}")
except DataValidationError as e:
    print(f"Invalid data received: {e}")
except APIError as e:
    print(f"API error: {e}")
```

## Practical Examples

### Example 1: Find Top Performers in a Club

```python
from webshooter_client.api.api_calls import get_results, get_competitions

def get_top_club_performers(year: int, club_number: str, top_n: int = 10):
    """Find top N performers from a club in a given year."""
    
    # Get all competitions for the year
    competitions = get_competitions(year=year)
    
    club_performances = []
    
    for comp in competitions:
        try:
            results = get_results(competition_id=comp.id)
            
            # Filter for club members
            club_results = [
                r for r in results 
                if r.signup.spsf_club_number == club_number
            ]
            
            # Collect performance data
            for result in club_results:
                club_performances.append({
                    'name': result.signup.fullname,
                    'competition': comp.name,
                    'placement': result.placement,
                    'points': result.points
                })
        except Exception as e:
            print(f"Error processing {comp.name}: {e}")
            continue
    
    # Sort by points (descending)
    top_performers = sorted(
        club_performances, 
        key=lambda x: x['points'], 
        reverse=True
    )[:top_n]
    
    return top_performers

# Usage
top_10 = get_top_club_performers(year=2026, club_number="12-239", top_n=10)
for perf in top_10:
    print(f"{perf['name']}: {perf['points']} points at {perf['competition']}")
```

### Example 2: Export Results to CSV

```python
import csv
from webshooter_client.api.api_calls import get_results

def export_results_to_csv(competition_id: int, filename: str):
    """Export competition results to CSV file."""
    
    results = get_results(competition_id=competition_id)
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            'Placement', 'Card', 'Name', 'Club', 
            'Class', 'Points', 'Medal'
        ])
        
        # Write data
        for result in results:
            writer.writerow([
                result.placement,
                result.signup.shooting_card_number,
                result.signup.fullname,
                result.signup.spsf_club_number,
                result.signup.weapon_class,
                result.points,
                result.std_medal.display_name if result.std_medal else ''
            ])
    
    print(f"Exported {len(results)} results to {filename}")

# Usage
export_results_to_csv(competition_id=283, filename="results_283.csv")
```

### Example 3: Competition Statistics

```python
from webshooter_client.api.api_calls import get_results, get_competition
from collections import Counter

def get_competition_stats(competition_id: int):
    """Get statistics for a competition."""
    
    comp = get_competition(competition_id=competition_id)
    results = get_results(competition_id=competition_id)
    
    # Count participants by class
    classes = Counter(r.signup.weapon_class for r in results)
    
    # Count participants by club
    clubs = Counter(r.signup.spsf_club_number for r in results)
    
    # Calculate average score
    avg_points = sum(r.points for r in results) / len(results)
    
    # Count medals
    medals = Counter(
        r.std_medal.display_name 
        for r in results 
        if r.std_medal
    )
    
    print(f"Competition: {comp.name}")
    print(f"Type: {comp.type.display_name}")
    print(f"Date: {comp.date}")
    print(f"\nTotal participants: {len(results)}")
    print(f"Average score: {avg_points:.1f} points")
    print(f"\nParticipants by class:")
    for cls, count in classes.most_common():
        print(f"  {cls}: {count}")
    print(f"\nTop 5 clubs by participation:")
    for club, count in clubs.most_common(5):
        print(f"  {club}: {count} shooters")
    print(f"\nMedals awarded:")
    for medal, count in medals.items():
        print(f"  {medal}: {count}")

# Usage
get_competition_stats(competition_id=283)
```

## API Limitations

- **Authentication:** Token expires periodically, must be refreshed from browser
- **Rate Limiting:** No official rate limits, but be respectful
- **API Version:** Currently supports v4.1.9 - may break if API changes
- **Data Freshness:** No caching - always fetches fresh data
- **Retry Logic:** Built-in exponential backoff for failed requests (max 5 retries)

## Best Practices

1. **Token Management:** Store token securely, don't commit to version control
2. **Error Handling:** Always catch API exceptions in production code
3. **Caching:** Consider local caching for frequently accessed data
4. **Logging:** Enable verbose mode during development: `config.verbose = True`
5. **Testing:** Use test data from `tests/resources/` for unit tests

## API Versioning

Current API version: **v4.1.9**

If the webshooter.se API version changes, update `BASE_URL_*` constants in `api/api_calls.py`:

```python
BASE_URL_COMPETITIONS = "https://webshooter.se/api/v4.1.9/competitions..."
BASE_URL_COMPETITION = "https://webshooter.se/api/v4.1.9/competitions/{competition}"
```

## Support

- **Issues:** https://github.com/frazz/webshooter/issues
- **Documentation:** See `CONTRIBUTING.md` and `ARCHITECTURE.md`
- **Examples:** Check `tests/integration/` for more usage examples

## License

See LICENSE file in the repository.
