# Webshooter Client Architecture

This document describes the architecture and design decisions of the Webshooter Client.

## Overview

Webshooter Client is a Python CLI application for interacting with the webshooter.se API (Swedish shooting competition platform). The architecture follows a layered design with clear separation of concerns.

## Architecture Layers

```
┌─────────────────────────────────────────────┐
│           CLI Entry Point (command.py)       │
│              configargparse                  │
└────────────────┬─────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│        Commands Layer (commands/)            │
│   BaseCommand + Subcommand Classes           │
│   (competitions, results, signups, etc.)     │
└────────────┬──────────────┬──────────────────┘
             │              │
             ▼              ▼
    ┌────────────┐   ┌──────────────┐
    │  Services  │   │  API Layer   │
    │  Layer     │   │ (api_calls)  │
    │ (parsers,  │   │              │
    │ formatters)│   │   HTTP       │
    └─────┬──────┘   └──────┬───────┘
          │                 │
          │                 ▼
          │         ┌───────────────┐
          │         │  webshooter   │
          │         │  .se API      │
          │         │  v4.1.9       │
          │         └───────────────┘
          │
          ▼
    ┌──────────────────┐
    │  Models Layer    │
    │  (dataclasses)   │
    │  Competition     │
    │  Result          │
    │  Signup          │
    │  Patrol          │
    └──────────────────┘
```

## Layer Responsibilities

### 1. CLI Entry Point (`command.py`)

**Responsibility:** Parse command-line arguments and dispatch to appropriate subcommands.

**Key Features:**
- Uses `configargparse` for unified CLI args + config file
- Config file: `~/.webshooter.rc` (optional)
- Initializes `ApplicationConfig` singleton
- Two entry points: `wscli` and `webshooter`

**Configuration Priority:** CLI args > config file > defaults

### 2. Commands Layer (`commands/`)

**Responsibility:** Implement business logic for each CLI subcommand.

**Pattern:** Each command inherits from `BaseCommand` providing shared functionality:
- Error handling
- Output utilities (print tables, headers)
- Common filtering logic

**Subcommands:**
- `CompetitionListCommand` - List competitions by year
- `ResultsCommand` - Show competition results
- `SignupCommand` - Show signups
- `StartTimesCommand` - Show start times
- `StartsCommand` - Show start assignments
- `IcalExportCommand` - Export to iCal format
- `MedalsCommand` - Show medal statistics

### 3. Services Layer (`services/`)

**Responsibility:** Extract business logic into reusable, testable services.

#### Formatters (Strategy Pattern)

Different competition types require different formatting:

```python
# Strategy interface
class ResultFormatter:
    def format(self, results: List[Result]) -> List[List]:
        ...

# Concrete strategies
MilitaryFormatter()    # For MILITARY/PRECISION (series)
FieldFormatter()       # For FIELD/POINTFIELD (stations)
```

**Why Strategy Pattern:**
- Each competition type has unique result structure
- Easy to add new types without modifying existing code
- Encapsulates formatting logic per type
- Testable in isolation

#### Parsers (Strategy Pattern)

Different competition types return different JSON structures:

```python
# Strategy interface
class ResultParser:
    def parse(self, data: dict) -> List[Result]:
        ...

# Concrete strategies
MilitaryResultParser()
FieldResultParser()
```

**Why Strategy Pattern:**
- API returns different structures per competition type
- Validation logic varies by type
- Separates parsing from presentation
- Reusable across commands

### 4. API Layer (`api/`)

**Responsibility:** All HTTP communication with webshooter.se API.

**Key Module:** `api_calls.py`

**Design Principles:**
- Single source of truth for all API calls
- Constructs domain models from JSON responses
- Handles HTTP errors and raises custom exceptions
- No business logic - just data fetching

**Important API Patterns:**

1. **Token Authentication:**
   - Required for all API calls
   - Token stored in local storage on webshooter.se
   - Must be copied manually (no OAuth flow)

2. **Nested Data:**
   ```python
   # get_results() makes 2 fetch_data calls:
   # 1. get_competition(id) -> competition data
   # 2. results URL -> results + nested signup data
   ```

3. **Data Structure:**
   - Results include nested signup objects
   - Signups not fetched separately for results
   - Expected format: `{"signups": {"data": [...]}}`

**Exception Hierarchy:**

```python
APIError (base)
├── APIConnectionError    # Network issues
├── APITimeoutError       # Request timeout
├── APIHTTPError         # HTTP errors (4xx, 5xx)
└── DataValidationError  # Invalid API response data
```

### 5. Models Layer (`models/`)

**Responsibility:** Domain objects representing API entities.

**Pattern:** All models are dataclasses with `kw_only=True`:

```python
@dataclass(kw_only=True)
class Competition:
    id: int
    name: str
    type: CompetitionType
    date: str
    # ...
```

**Why Dataclasses:**
- Immutable by convention
- Type safety
- Automatic `__init__`, `__repr__`
- Easy serialization/deserialization

**Key Models:**
- `Competition` - Competition metadata
- `Result` - Individual shooter result
- `Signup` - Registration for competition
- `Patrol` - Start time assignment

### 6. Common Utilities (`common/`)

**Responsibility:** Shared utilities and base classes.

#### ApplicationConfig (Singleton Pattern)

```python
@dataclass(kw_only=True)
class ApplicationConfig(metaclass=SingletonMeta):
    unicode: bool = True
    verbose: bool = False
    token: Optional[str] = None
```

**Why Singleton:**
- Global configuration accessed throughout application
- Ensures consistency - one source of truth
- Initialized once from CLI args + config file
- Thread-safe via metaclass implementation

**Rationale:**
1. **Avoid parameter passing:** Config needed in many layers
2. **Consistency:** Prevents conflicting config instances
3. **Simplicity:** Cleaner than dependency injection for small CLI
4. **Performance:** One-time initialization

**Trade-offs:**
- ✅ Simple, clean access pattern
- ✅ No config parameter threading
- ❌ Global state (acceptable for CLI tool)
- ❌ Harder to test (mitigated with fixtures)

#### DisplayEnum Pattern

```python
class CompetitionType(DisplayEnum):
    MILITARY = ("MILITARY", "Militär snabbmatch")
    PRECISION = ("PRECISION", "Precision")
    FIELD = ("FIELD", "Fält")
    POINTFIELD = ("POINTFIELD", "Poängfält")
```

**Why Custom Enum:**
- Swedish display names for output
- English values for API
- Clean access: `CompetitionType.MILITARY.display_name`

## Data Flow Examples

### Example 1: List Competitions

```
User: wscli competitions --year 2026
  │
  ├─> command.py: Parse args, init ApplicationConfig
  │
  ├─> CompetitionListCommand.get_competition_list()
  │     │
  │     ├─> api_calls.get_competitions(year=2026)
  │     │     │
  │     │     └─> HTTP GET webshooter.se/api/v4.1.9/competitions
  │     │           │
  │     │           └─> Returns: List[Competition]
  │     │
  │     └─> Format as table with tabulate
  │
  └─> Output: Table of competitions
```

### Example 2: Show Results

```
User: wscli results --competition 283
  │
  ├─> command.py: Parse args
  │
  ├─> ResultsCommand.get_results_for_competition()
  │     │
  │     ├─> api_calls.get_results(comp_id=283)
  │     │     │
  │     │     ├─> get_competition(283) -> Competition object
  │     │     │     │
  │     │     │     └─> Determine type: MILITARY
  │     │     │
  │     │     └─> Fetch results with nested signups
  │     │           │
  │     │           └─> Returns: List[Result]
  │     │
  │     ├─> ResultParserFactory.get_parser(MILITARY)
  │     │     │
  │     │     └─> MilitaryResultParser()
  │     │
  │     ├─> parser.parse(results) -> validated results
  │     │
  │     ├─> ResultFormatterFactory.get_formatter(MILITARY)
  │     │     │
  │     │     └─> MilitaryFormatter()
  │     │
  │     ├─> formatter.format(results) -> table data
  │     │
  │     └─> Sort by class, then by place
  │
  └─> Output: Formatted results table
```

## Design Decisions

### 1. Why Strategy Pattern for Formatters/Parsers?

**Problem:** Four competition types with different data structures.

**Alternatives Considered:**
- ❌ If/else chains: Violates Open/Closed Principle
- ❌ Single formatter with all logic: Hard to maintain
- ✅ Strategy pattern: Easy to extend, testable

**Benefits:**
- Add new types without modifying existing code
- Each strategy is independently testable
- Clear separation of concerns
- Follows SOLID principles

### 2. Why Singleton for ApplicationConfig?

**Problem:** Config needed throughout application layers.

**Alternatives Considered:**
- ❌ Pass as parameter everywhere: Verbose, clutters signatures
- ❌ Global variable: No encapsulation, not type-safe
- ❌ Dependency injection: Overkill for small CLI
- ✅ Singleton: Clean access, guaranteed consistency

**Benefits:**
- Simple access pattern
- Initialized once from CLI args + file
- Type-safe dataclass with defaults
- Thread-safe via metaclass

### 3. Why Remove Pandas?

**Problem:** 30MB+ dependency for simple sorting.

**Analysis:**
- Only used in one place: `df.sort_values(by=["Class", "Place"])`
- Replaced with: `sorted(data, key=lambda row: (row[2], row[4]))`
- Savings: ~30MB + transitive dependencies

**Decision:** Use standard library - sufficient for CLI needs.

### 4. Why Dataclasses for Models?

**Problem:** Need typed domain objects with minimal boilerplate.

**Alternatives Considered:**
- ❌ Plain dicts: No type safety, error-prone
- ❌ Named tuples: Less flexible, harder to extend
- ✅ Dataclasses: Type-safe, clean, Pythonic

**Benefits:**
- Automatic `__init__`, `__repr__`, `__eq__`
- Type hints for IDE support
- Keyword-only args prevent mistakes
- Easy to serialize/deserialize

### 5. Why Custom Exception Hierarchy?

**Problem:** Need to distinguish API errors from data errors.

**Benefits:**
- Specific handling for network vs validation errors
- Clear error messages for users
- Easy to add retry logic for connection errors
- Better debugging and logging

## Testing Strategy

### Unit Tests
- Test individual functions/classes in isolation
- Mock external dependencies (API calls)
- Fast, deterministic

### Integration Tests
- Test with real API response data (from `tests/resources/`)
- Verify end-to-end behavior
- Catch API structure changes

### Test Data Organization
```
tests/resources/test_data/competitions/
├── 149/ (Military)
├── 152/ (Precision)
└── 157/ (Field)
    ├── competition_157.json
    ├── competition_157_results.json
    ├── competition_157_signups.json
    └── competition_157_patrols.json
```

**Philosophy:** Quality over coverage - write tests that catch real bugs.

## Dependencies

**Runtime (3 packages):**
- `requests>=2.32.0,<3.0.0` - HTTP client
- `ConfigArgParse>=1.7,<2.0` - CLI + config file
- `tabulate>=0.9.0,<1.0` - Table formatting

**Why Version Ranges:**
- Allow security patch updates
- Prevent breaking changes
- `renovate.json` configured for automated updates

## Extension Points

### Adding a New Competition Type

1. **Add enum value:**
   ```python
   # models/competition.py
   class CompetitionType(DisplayEnum):
       NEWTYPE = ("NEWTYPE", "Display Name")
   ```

2. **Create parser:**
   ```python
   # services/result_parser.py
   class NewTypeResultParser(ResultParser):
       def parse(self, data: dict) -> List[Result]:
           # Parse logic
   ```

3. **Create formatter:**
   ```python
   # services/result_formatter.py
   class NewTypeFormatter(ResultFormatter):
       def format(self, results: List[Result]) -> List[List]:
           # Format logic
   ```

4. **Register in factories:**
   ```python
   # services/result_parser.py
   ResultParserFactory.register(CompetitionType.NEWTYPE, NewTypeResultParser)
   
   # services/result_formatter.py
   ResultFormatterFactory.register(CompetitionType.NEWTYPE, NewTypeFormatter)
   ```

No existing code needs modification!

### Adding a New Command

1. **Create command class:**
   ```python
   # commands/new_command.py
   class NewCommand(BaseCommand):
       @staticmethod
       def execute(args):
           # Implementation
   ```

2. **Register in command.py:**
   ```python
   subparser = subparsers.add_parser('newcmd', help='Description')
   # Add arguments
   subparser.set_defaults(func=NewCommand.execute)
   ```

## API Version Management

Current: **v4.1.9**

If API version changes, update `BASE_URL_*` constants in `api/api_calls.py`. Consider versioning strategy if breaking changes occur.

## Performance Considerations

- **Network-bound:** CLI waits for API responses
- **No caching:** Fresh data on each request
- **Optimization:** Focus on UX (clear output) over speed

## Security

- **Token storage:** User's responsibility (config file)
- **HTTPS:** All API calls use TLS
- **Dependencies:** Automated updates via Renovate
- **No sensitive data:** Token not logged or displayed

## Future Improvements

Potential enhancements (not planned):
- Local caching for offline access
- Async API calls for multiple competitions
- Export formats (CSV, Excel)
- Interactive TUI mode
- Shell completion

## Conclusion

The architecture prioritizes:
1. **Separation of concerns** - Clear layer boundaries
2. **Extensibility** - Easy to add new competition types
3. **Testability** - Isolated components, strategy pattern
4. **Simplicity** - Appropriate patterns for CLI tool size
5. **Maintainability** - Clear structure, good documentation

The design balances flexibility with simplicity, avoiding over-engineering while remaining extensible.
