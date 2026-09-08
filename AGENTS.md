Agent Usage Guidelines
======================

All development and test commands in this repository MUST be run using `uv` so the project-managed environment is used.

Do not run `python`, `pip`, `pytest`, or attempt to activate a separate virtualenv directly from the command line. Running commands outside `uv` can cause inconsistent dependency resolution and may accidentally use a system Python without SSL support.

This requirement applies to every ad-hoc or temporary Python invocation as well — for example, one-off scripts, quick repls, or temporary helper commands that you or an agent runs during development or CI debugging. Always prefix Python commands with `uv run --` (for example: `uv run -- python scripts/some_temp_script.py`) so the project's controlled environment is used.

Recommended commands:
- Run tests: `uv run -- python -m pytest` or `uv run -- pytest`
- Run the CLI: `uv run -- python -m src.cli mappings.yaml`
- Run utility scripts: `uv run -- python scripts/fetch_production_fixtures.py --output ...`

If you need to target the currently-active shell virtualenv, use `uv run -- --active ...` (see `uv --help`).

CI and workflows in this repository also use `uv` where appropriate to ensure reproducible, isolated runs.

Test Coverage
- We aim for at least 90% test coverage measured over the `src/` package. Use pytest-cov via uv to run tests with coverage and fail if coverage is below the threshold:
  `uv run -- python -m pytest --cov=src --cov-fail-under=90`
