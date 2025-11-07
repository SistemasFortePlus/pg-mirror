# pg-mirror - AI Coding Agent Instructions

## Architecture Overview

**pg-mirror** is a PostgreSQL database mirroring tool with a clean, modular architecture:

- **CLI layer** (`cli.py`): Click-based commands orchestrating the backup→restore workflow
- **Core operations**: Isolated modules for `backup.py`, `restore.py`, `database.py`
- **External dependencies**: Wraps PostgreSQL client tools (`pg_dump`, `pg_restore`, `psql`) via subprocess
- **Config-driven**: JSON files define source/target servers and options

**Critical flow**: `mirror` command → load config → verify system → backup (with custom format `-Fc`) → check/create target DB → parallel restore (`-j`) → cleanup temp file

## Key Architectural Decisions

1. **Custom format backups** (`-Fc` flag): Enables both compression AND parallel restore - never use plain SQL dumps
2. **Temporary file handling**: Uses `tempfile.NamedTemporaryFile` with explicit cleanup in finally blocks
3. **Environment-based auth**: Passes `PGPASSWORD` via `env` dict to subprocess, never in command args
4. **Intelligent DB management**: Always checks if DB exists before deciding to create/drop/reuse

## Development Workflow

### Running tests
```bash
# Full test suite with coverage
pytest tests/ --cov=pg_mirror --cov-report=term-missing

# Generate HTML coverage report (opens htmlcov/index.html)
pytest tests/ --cov=pg_mirror --cov-report=html

# Run specific test file
pytest tests/test_backup.py -v
```

### Code quality
```bash
# Format code (Black, 100 char line length)
black pg_mirror/ tests/

# Sort imports
isort pg_mirror/ tests/

# Lint (allows C0103, C0114, R0913)
pylint pg_mirror/
```

### Testing the CLI locally
```bash
# Install in editable mode
pip install -e .

# Test with example config
pg-mirror mirror --config examples/config.localhost.json

# System checks (verify pg_dump/pg_restore/psql available)
pg-mirror check
```

## Project-Specific Patterns

### Subprocess calls pattern
All PostgreSQL commands follow this structure:
```python
env = os.environ.copy()
env['PGPASSWORD'] = password
subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
```

### Logger usage
Always pass logger as parameter (dependency injection), never create in modules:
```python
logger.info("User-facing message")
logger.debug("Developer debugging info")  # Only with --verbose
logger.warning("Non-fatal issues")
logger.error("Fatal errors before sys.exit(1)")
```

### Error handling philosophy
- `subprocess.CalledProcessError`: Catch and exit with `sys.exit(1)` after logging
- `pg_restore` returns 1 even on success with warnings: Check stderr for "ERROR" string
- Config validation: Fail fast with descriptive errors in `load_config()`

### Test fixtures (`tests/conftest.py`)
- `mock_logger`: Mocked logger for all tests
- `valid_config`, `minimal_config`: Complete config dicts
- `temp_config_file`: Creates real JSON file, auto-cleanup with yield

Mock subprocess calls in tests:
```python
@patch('subprocess.run')
def test_something(mock_run, mock_logger):
    mock_run.return_value = MagicMock(returncode=0)
    # test implementation
    call_args = mock_run.call_args[0][0]  # Get command list
    assert 'pg_dump' in call_args
```

## Configuration Schema

Required fields (enforced in `config.py`):
- `source`: host, database, user, password (port defaults to 5432)
- `target`: host, user, password (port defaults to 5432)
- `options`: drop_existing (bool, default false), parallel_jobs (int, default 4)

Target database name always matches source database name (by design).

## External Dependencies

PostgreSQL client tools MUST be installed:
- **pg_dump**: Backup creation (custom format with compression)
- **pg_restore**: Multi-threaded restore
- **psql**: Database existence checks and creation

System checks (`system_checks.py`) verify these with `shutil.which()` and provide OS-specific installation instructions.

## CI/CD Notes

GitHub Actions matrix tests across:
- **Python**: 3.8, 3.9, 3.10, 3.11, 3.12
- **OS**: Ubuntu, macOS, Windows

PostgreSQL client installation varies by OS:
- Ubuntu: `apt-get install postgresql-client`
- macOS: `brew install postgresql`
- Windows: Choco with PATH append required

## Common Pitfalls

1. **Don't use plain SQL dumps**: Always use `-Fc` (custom format) for pg_dump to enable parallel restore
2. **Handle restore exit codes carefully**: `pg_restore` returns 1 on warnings; check stderr for "ERROR" string
3. **Never hardcode /tmp paths**: Use `tempfile` module for cross-platform compatibility
4. **Cleanup temp files**: Always cleanup in `finally` block, even on errors
5. **Respect the 100-char line limit**: Enforced by Black formatter in pyproject.toml

## File References

- **Entry point**: `pg_mirror/cli.py` - All commands defined here
- **Backup logic**: `pg_mirror/backup.py` - Single responsibility: create compressed backup
- **Restore logic**: `pg_mirror/restore.py` - Parallel restore with job count
- **DB operations**: `pg_mirror/database.py` - Check/create/drop databases
- **Config schema**: See `examples/config.example.json` for complete structure
- **Test patterns**: `tests/conftest.py` for shared fixtures and mocking patterns
