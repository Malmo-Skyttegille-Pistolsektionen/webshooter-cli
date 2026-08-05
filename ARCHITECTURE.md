# Webshooter Client Architecture

This document describes the architecture and design decisions of the Webshooter Client.

## Overview

Webshooter Client is a Python CLI application for interacting with the webshooter.se API (Swedish shooting competition platform). The architecture follows a layered design with clear separation of concerns.

## Architecture Layers

```
┌─────────────────────────────────────────────┐
│           CLI Entry Point (command.py)       │
│              configargparse                  │
└────────────────┬──────────────┬──────────────┘
                 │              │
                 ▼              ▼
┌─────────────────────────────┐  ┌──────────────────────────┐
│  Commands Layer (commands/)  │  │  MCP Server (mcp/)       │
│  BaseCommand + Subcommands   │  │  wscli mcp — exposes the │
│  (competitions, results,     │  │  local store to AI agents│
│   sync, store, etc.)         │  │  as MCP tools            │
└──────┬──────────┬────────────┘  └────────────┬──────────────┘
       │          │                            │
       │          ▼                            ▼
       │  ┌────────────────────────────────────────┐
       │  │  Services Layer (services/)             │
       │  │  Data-returning functions shared by     │
       │  │  the CLI and the MCP server              │
       │  │  (parsers, formatters, local_query)     │
       │  └───────┬──────────────────────┬──────────┘
       │          │                      │
       ▼          ▼                      ▼
┌────────────┐ ┌──────────────┐  ┌───────────────────┐
│  Sync       │ │  API Layer   │  │  API Layer         │
│  (sync/)    │ │ (api_calls)  │  │  local cache reads │
│  incremental│ │              │  │  (api/cache.py)     │
│  download + │ │   HTTP       │  │                     │
│  index      │ └──────┬───────┘  └──────────┬──────────┘
└─────┬───────┘        │                      │
      │                ▼                      ▼
      │        ┌───────────────┐     ┌──────────────────┐
      │        │  webshooter   │     │  Local store      │
      │        │  .se API      │     │  ~/.cache/        │
      │        │  v4.1.9       │     │  webshooter        │
      │        └───────────────┘     └──────────────────┘
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
- `--use-cache`/`--offline` (aliases for the same setting) and
  `--refresh-competitions` are global flags parsed here, ahead of the
  subcommand
- `main()` catches `WebShooterAPIError` at the top level and prints
  `Error: <message>` with exit code 1 instead of a traceback; `--verbose`
  re-raises for the full stack

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

#### Local Queries (`services/local_query.py`)

**Responsibility:** Data-returning functions answered entirely from the local
store, shared between the CLI (`commands/`) and the MCP server (`mcp/`).

Every function here (`downloaded_competitions`, `my_results`, `personal_bests`,
`competition_results`, `participation_summary`, …) reads only competitions
already present on disk and never falls back to the network — each is safe to
call with `ApplicationConfig(offline=True)`. Results are plain JSON-friendly
dicts (`competition_to_dict`, `result_to_dict`) so the same code can back a
printed table or an MCP tool response.

**The rule that keeps this shared:** presentation (printing tables, formatting
for a terminal) lives in `commands/`; anything that *returns data* belongs in
`services/` so both the CLI and the MCP server can call it. `commands/sync.py`
is the CLI's presentation layer over `sync/`, the same way `commands/*.py`
generally sit over `services/`.

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
├── DataValidationError  # Invalid API response data
└── OfflineCacheMissError # --use-cache/--offline and the data isn't local
```

**Offline guard (`fetch_data`):** when `ApplicationConfig().offline` is set,
`fetch_data` never falls back to the network — a cache miss raises
`OfflineCacheMissError` telling the caller to run `wscli sync`. The one way
past that guard is `force_refresh=True`, which is a deliberate request for
fresh data and so overrides the offline check (offline blocks the *implicit*
fallback to the API on a miss, not an explicit refresh). `get_competitions()`
passes `force_refresh=True` either when called with that argument directly
(as `sync` does) or when `ApplicationConfig().refresh_competitions` is set
(`--refresh-competitions`), so a `--use-cache` run can still opt into a fresh
competition list without giving up local-only behavior for everything else.

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

### 7. Sync Layer (`sync/`)

**Responsibility:** Incrementally download competitions into the local store
and maintain the index used by offline queries.

**Key module:** `sync/syncer.py`

The webshooter API has no "changed since" endpoint, so `sync_competitions()`
works from the competition calendar:

1. Re-fetch the competition list (bypassing any cached copy — a stale list
   can never contain competitions published after it was written).
2. Find the most recent competition whose results are already downloaded —
   the "watermark" (future-dated competitions are ignored so an empty results
   file for something not yet shot can't push the watermark forward).
3. Download every competition on or after the watermark that has already
   taken place and is not downloaded yet (`--full` drops the watermark and
   considers every past competition).
4. Record, per competition, which weapon classes the given card competed in,
   into `sync_index.json` (via `api/cache.py`'s `load_index`/`save_index`) —
   that index is what makes later offline queries cheap, since they can open
   only the files that can contain the shooter instead of scanning everything.

`reindex_local_store()` rebuilds that index from competitions already on disk,
with no network call — useful after switching cards or for a store populated
before the index existed. `get_local_store_status()` answers "what does the
store contain" (count, date range, last sync, card) without touching the
network either.

Because `sync_competitions()` downloads data by definition, it refuses to run
when `ApplicationConfig().offline` is set: it raises a `WebShooterAPIError`
telling the user to drop `--use-cache`/`--offline` or use `sync --reindex`
instead. `reindex_local_store()` is exempt from that check — it only reads
data already on disk — which is why `sync --reindex` is documented as working
with `--use-cache`.

**Why a separate layer from `api/cache.py`:** `api/cache.py` is a low-level
key/value file cache (raw API responses, keyed by URL/id). `sync/` is the
policy on top of it — deciding *what* to download and *when* a re-download is
unnecessary, and maintaining the derived index. Keeping that policy out of
`api/` keeps the cache module a dumb, reusable file store.

### 8. MCP Layer (`mcp/`)

**Responsibility:** Expose the local store to AI agents over the [Model
Context Protocol](https://modelcontextprotocol.io), via `wscli mcp`.

**Key module:** `mcp/server.py`

`start_server()` is a thin adapter over `services/local_query.py` and
`sync/` — it registers one MCP tool per local-query function
(`local_store_status`, `list_competitions`, `get_competition_results`,
`get_my_results`, `get_personal_bests`, `get_participation_summary`) plus,
only when started with `--allow-sync`, `sync_local_store` and `reindex_store`.
No statistics or filtering logic is reimplemented here — it all comes from
`services/local_query.py` and `sync/`.

The server puts `ApplicationConfig` into offline mode (`config.offline = True`)
for the lifetime of the process, flipping it off only around the body of
`sync_local_store`. This is what guarantees the read-only tools can never
silently reach the network.

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

### 6. Why an MCP Server Over the Local Store, Rather Than Letting the Agent Shell Out to the CLI?

**Problem:** Agents already know how to shell out to CLIs, so an MCP server
needs to earn its keep over just running `wscli stats` and parsing the output.

**Alternatives Considered:**
- ❌ Let the agent invoke `wscli` and parse table output: fragile (agents have
  to re-parse `tabulate` output on every call), gives the agent the token and
  full network access, and costs one round trip per question.
- ✅ MCP server over `services/local_query.py`: structured JSON in, structured
  JSON out.

**Benefits:**
- **Structured JSON instead of parsing tables** — tools return the same dicts
  `local_query.py` builds for the CLI, so an agent gets typed fields
  (`points`, `weapon_class`, `competition.id`, …) instead of scraping columns.
- **Offline by default** — the server forces `ApplicationConfig(offline=True)`
  for every tool except `sync_local_store`/`reindex_store` (and only with
  `--allow-sync`), so an agent exploring results cannot accidentally hammer
  the live API.
- **No token handling by the agent** — the token lives in `~/.webshooter.rc`
  or the server's environment; the agent never sees or passes it.
- **One round trip instead of many** — `get_personal_bests` or
  `get_participation_summary` do the aggregation server-side, instead of the
  agent shelling out repeatedly and combining CLI output itself.

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

- **Network-bound:** live commands wait for API responses
- **Local store:** `wscli sync` populates `~/.cache/webshooter`; once synced, `--offline` and the MCP server answer entirely from disk with no network round trip
- **Optimization:** Focus on UX (clear output) over speed

## Security

- **Token storage:** User's responsibility (config file)
- **HTTPS:** All API calls use TLS
- **Dependencies:** Automated updates via Renovate
- **No sensitive data:** Token not logged or displayed

## Programmatic Usage

While primarily a CLI tool, the components can be used programmatically:

```python
from webshooter_client.api.api_calls import get_competitions, get_results
from webshooter_client.common.application_config import ApplicationConfig

# Configure
config = ApplicationConfig()
config.token = "your-token-here"

# Fetch data
competitions = get_competitions(year=2026)
results = get_results(competition_id=283)

# Process
for result in results:
    print(f"{result.placement}. {result.signup.fullname} - {result.points}")
```

**Key modules:**
- `api.api_calls` - API functions (get_competitions, get_results, get_signups, get_patrols)
- `models.*` - Dataclasses (Competition, Result, Signup, Patrol)
- `commands.result_formatters` - Strategy formatters for display
- `api.exceptions` - Custom exception hierarchy
- `services.local_query` - Offline-safe, JSON-friendly queries shared by the CLI and the MCP server
- `sync.syncer` - Incremental download into the local store (`sync_competitions`, `reindex_local_store`, `get_local_store_status`)
- `mcp.server` - MCP server (`start_server`) exposing `services.local_query` and `sync` as tools

## Future Improvements

Potential enhancements (not planned):
- ~~Local caching for offline access~~ — done: see `sync/`, `--offline`, and the MCP server
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
