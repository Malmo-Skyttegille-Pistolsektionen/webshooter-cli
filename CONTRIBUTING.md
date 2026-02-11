# Contributing to Webshooter Client

Thank you for your interest in contributing to Webshooter Client! This document provides guidelines and instructions for development.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- [Hatch](https://hatch.pypa.io/) for environment management
- Git

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/frazz/webshooter.git
   cd webshooter
   ```

2. **Install Hatch (if not already installed):**
   ```bash
   pip install hatch
   ```

3. **Verify setup:**
   ```bash
   hatch run dev:pytest tests
   ```

### Configuration

Create a configuration file at `~/.webshooter.rc`:

```ini
[global]
unicode = True
card = xx
club = aa-bbb
token = <your-token-here>
```

**Getting your API token:**
1. Log in to [webshooter.se](https://www.webshooter.se)
2. Open browser developer tools (F12)
3. Navigate to: Storage → Local Storage → token
4. Copy the token value to your config file

All configuration values are optional and can be overridden via command-line arguments.

## Development Workflow

### Running the Application

**From source (during development):**
```bash
hatch run python src/webshooter_client/command.py --help
```

**After building:**
```bash
hatch build
pip install dist/webshooter_client-*.whl
wscli --help
```

### Code Quality

We maintain high code quality standards. Before submitting changes:

#### 1. Format code with Black
```bash
hatch run dev:black src tests
```

#### 2. Lint with flake8
```bash
hatch run dev:flake8
```

#### 3. Run all tests
```bash
# Run all tests (excludes slow and integration by default)
hatch run dev:pytest tests

# Run with coverage report
hatch run dev:pytest --cov=src/webshooter_client --cov-report=html tests

# Run including slow tests
hatch run dev:pytest -m slow tests

# Run including integration tests (requires API access)
hatch run dev:pytest -m integration tests
```

#### 4. Run specific tests
```bash
# Single test file
hatch run dev:pytest tests/unit/webshooter_client/commands/test_competition_list.py

# Single test function
hatch run dev:pytest tests/unit/webshooter_client/commands/test_competition_list.py::test_function_name
```

### Code Style Guidelines

- **Line length:** 120 characters (Black), 125 (flake8)
- **Target:** Python 3.10+
- **Type hints:** Use type hints for function signatures
- **Docstrings:** Add docstrings for public modules, classes, and functions
- **Comments:** Only comment complex logic that needs clarification

### Testing Philosophy

**Quality over coverage** - We prioritize meaningful tests that catch real bugs over achieving high coverage percentages.

Good tests:
- ✅ Use real API response data from `tests/resources/`
- ✅ Verify actual production behavior
- ✅ Cover edge cases (empty data, missing fields, errors)
- ✅ Test integration points between layers

Avoid:
- ❌ Tests that just exercise code without assertions
- ❌ Overly mocked tests that don't reflect reality
- ❌ Redundant tests that verify the same behavior

**Test markers:**
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.integration` - Tests requiring external resources
- `@pytest.mark.flaky` - Tests that can randomly fail

## Architecture

### High-Level Structure

```
src/webshooter_client/
├── command.py              # CLI entry point (configargparse)
├── api/                    # API client layer
│   ├── api_calls.py        # HTTP requests to webshooter.se
│   └── exceptions.py       # Custom exceptions
├── commands/               # Subcommand implementations
│   ├── base_command.py     # Shared command functionality
│   ├── competitions.py     # List competitions
│   ├── results.py          # Show competition results
│   ├── signups.py          # Show signups
│   ├── start_times.py      # Show start times
│   ├── starts.py           # Show start assignments
│   ├── ical_export.py      # Export to iCal
│   └── medals.py           # Show medal statistics
├── services/               # Business logic layer
│   ├── result_formatter.py    # Format results for display
│   ├── result_parser.py       # Parse API results
│   └── signup_formatter.py    # Format signups for display
├── models/                 # Domain models (dataclasses)
│   ├── competition.py
│   ├── result.py
│   ├── signup.py
│   └── patrol.py
└── common/                 # Shared utilities
    ├── application_config.py  # Singleton config
    ├── singleton_meta.py      # Singleton metaclass
    ├── enums.py              # DisplayEnum base class
    └── common.py             # Output utilities
```

### Key Patterns

#### API Layer
All HTTP interactions with the webshooter.se API v4.1.9 are in `api/api_calls.py`. Functions fetch JSON data and construct model objects.

**Important:** The API requires a token from browser local storage.

#### Configuration Management
- Uses `configargparse` with config file at `~/.webshooter.rc`
- `ApplicationConfig` is a singleton dataclass holding runtime config
- Command-line arguments override config file values

#### Command Pattern
Each subcommand is a class inheriting from `BaseCommand` with static methods. Commands use `tabulate` for formatted output.

#### Service Layer
Business logic is extracted into services:
- **Formatters:** Convert models to display tables (Strategy pattern)
- **Parsers:** Parse API responses into models (Strategy pattern)

#### Models
Domain objects are dataclasses with `kw_only=True`. See `Competition.type` for custom Enum pattern with `display_name` attribute.

### Competition Types

The system handles four types of shooting competitions:
- **MILITARY** (Militär snabbmatch)
- **PRECISION** (Precision)
- **FIELD** (Fält)
- **POINTFIELD** (Poängfält)

Each type has different result structures reflected in the models.

## Making Changes

### Before You Start

1. Check existing issues/PRs to avoid duplicate work
2. For significant changes, open an issue first to discuss
3. Create a feature branch from `main`

### Commit Guidelines

- Use clear, descriptive commit messages
- Reference issue numbers when applicable
- Keep commits focused and atomic

### Pull Request Process

1. Ensure all tests pass
2. Ensure code is formatted (Black) and linted (flake8)
3. Update documentation if needed
4. Add tests for new functionality
5. Submit PR with clear description of changes

## API Version

The client currently supports webshooter.se API **v4.1.9**. If the API version changes, update `BASE_URL_*` constants in `api/api_calls.py`.

## Getting Help

- Open an issue for bugs or feature requests
- Check existing documentation in the codebase
- Review test files for usage examples
- See [ARCHITECTURE.md](ARCHITECTURE.md) for programmatic usage

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
