Agent Usage Guidelines
======================

All development and test commands in this repository MUST be run using `uv` so the project-managed environment is used.

Do not run `python`, `pip`, `pytest`, or attempt to activate a separate virtualenv directly from the command line. Running commands outside `uv` can cause inconsistent dependency resolution and may accidentally use a system Python without SSL support.

Recommended commands:
- Run tests: `uv run -- python -m pytest` or `uv run -- pytest`
- Run the CLI: `uv run -- python -m src.cli mappings.yaml`
- Run utility scripts: `uv run -- python scripts/fetch_production_fixtures.py --output ...`

If you need to target the currently-active shell virtualenv, use `uv run -- --active ...` (see `uv --help`).

CI and workflows in this repository also use `uv` where appropriate to ensure reproducible, isolated runs.

Test Coverage
- We aim for at least 90% test coverage measured over the `src/` package. Use pytest-cov via uv to run tests with coverage and fail if coverage is below the threshold:
  `uv run -- python -m pytest --cov=src --cov-fail-under=90`
