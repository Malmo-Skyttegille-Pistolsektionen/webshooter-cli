# Copilot Instructions for Webshooter Client

A Python CLI client for interacting with WebShooter.se (Swedish shooting competition platform).

## Build, Test, and Lint

This project uses **Hatch** for environment management. Note: The `lint` and `test` environments are defined implicitly via the `dev` environment dependencies in `pyproject.toml`.

### Build
```bash
hatch build
```

### Testing
```bash
# Run all tests (excludes slow and integration tests by default)
hatch run test:pytest tests

# Run a specific test file
hatch run test:pytest tests/unit/webshooter_client/commands/test_competition_list.py

# Run a specific test function
hatch run test:pytest tests/unit/webshooter_client/commands/test_competition_list.py::test_function_name

# Include slow tests
hatch run test:pytest -m slow tests

# Include integration tests (requires external resources)
hatch run test:pytest -m integration tests
```

**Test markers:**
- `slow`: Long-running tests (deselected by default)
- `integration`: Tests requiring external resources (deselected by default)
- `flaky`: Tests that can randomly fail

### Linting
```bash
# Format with Black
hatch run lint:black src tests

# Lint with flake8
hatch run lint:flake8
```

**Code style:**
- Line length: 120 (Black), 125 (flake8)
- Target: Python 3.13+
- Flake8 ignores W503 (line break before binary operator)

## Architecture

### High-Level Structure
```
src/webshooter_client/
├── command.py           # CLI entry point (uses configargparse)
├── api/                 # API client layer
│   └── api_calls.py     # HTTP requests to webshooter.se API
├── commands/            # Subcommand implementations
│   ├── competitions.py
│   ├── results.py
│   ├── signups.py
│   ├── start_times.py
│   ├── starts.py
│   ├── ical_export.py
│   └── medals.py
├── models/              # Domain models (dataclasses)
│   ├── competition.py
│   ├── result.py
│   ├── signup.py
│   └── patrol.py
└── common/              # Shared utilities
    ├── application_config.py  # Singleton config
    ├── singleton_meta.py
    └── common.py
```

### Key Patterns

**API Layer:** `api/api_calls.py` contains all HTTP interactions with webshooter.se API v4.1.9. Functions fetch JSON data and construct model objects. The API requires a token copied from browser local storage.

**Configuration:** Uses `configargparse` with config file at `~/.webshooter.rc`. `ApplicationConfig` is a singleton dataclass that holds runtime config (token, unicode, verbose flags). Command line arguments override config file values.

**Commands:** Each subcommand is a class with static methods (e.g., `ResultsCommand.get_results_for_competition()`). Commands use `tabulate` and `pandas` for formatted output.

**Models:** Domain objects are dataclasses with kw_only=True. `Competition.type` uses custom Enum pattern with `display_name` attribute for Swedish labels.

**Test Structure:** Tests use pytest fixtures in `conftest.py` that provide test data from `tests/resources/` JSON files. The `fetch_data_side_effect` fixture mocks API responses.

### Competition Types
The system handles four types of shooting competitions:
- **MILITARY** (Militär snabbmatch)
- **PRECISION** (Precision)
- **FIELD** (Fält)
- **POINTFIELD** (Poängfält)

Each type has different result structures (series vs stations) reflected in the models.

## Key Conventions

1. **Hatch environments:** Unlike typical projects, lint/test commands require the `lint:` or `test:` prefix even though they use the same `dev` environment dependencies. This is a hatch convention for organizing related commands.

2. **Test data organization:** Test resources mirror the module structure under `tests/resources/`. Each test file can access its own resources via `resource_testfile_rootdir_w_path` fixture.

3. **API versioning:** The base URL includes version `v4.1.9`. If the API version changes, update `BASE_URL_*` constants in `api_calls.py`.

4. **Filtering by card/club:** Many commands accept `--card` and `--club` arguments. If only club is provided, show all members; if card is provided, it takes precedence.

5. **Entry points:** The package provides two CLI commands (`wscli` and `webshooter`) that both map to the same entry point.

## Running Without Installation

For development:
```bash
hatch run python src/webshooter_client/command.py --help
```

## Configuration File Format

`~/.webshooter.rc`:
```ini
[global]
unicode = True
card = xx
club = aa-bbb
token = <token from browser local storage>
```
