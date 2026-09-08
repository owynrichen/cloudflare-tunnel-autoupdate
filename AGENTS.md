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

YAML Validation
- Validate any YAML files you change before committing or pushing. CI and workflows are sensitive to YAML indentation and syntax; a small mistake can break runs.
- Quick syntax check (uses PyYAML which is already listed as a dependency in CI):
  `uv run -- python -c "import sys, yaml; yaml.safe_load(open(sys.argv[1])); print(sys.argv[1]+': OK')" path/to/file.yaml`
- Lint with yamllint (recommended for style and stricter checks):
  1. Install locally into the uv-managed env: `uv run -- pip install yamllint`
 2. Run: `uv run -- yamllint path/to/file.yaml`
- Validate only staged YAML files before committing (example):
  `git diff --name-only --staged -- '*.yaml' | xargs -r -n1 uv run -- python -c "import sys,yaml; yaml.safe_load(open(sys.argv[1])); print(sys.argv[1]+': OK')"`
- Consider adding a pre-commit hook that runs `yamllint` (or the Python syntax check) so YAML mistakes are caught locally before commits are made.
