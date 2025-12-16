# Contributing

Have you found a bug or do you have an idea for a new feature? Feel free to open
an issue and/or submit a PR!

## Developing

To contribute to this project, a development environment is recommended. You'll
need Python 3.10+ and ideally [uv](https://docs.astral.sh/uv/) installed.

### Installing the project:

```sh
uv sync
```

## Running tests and linters

### Tests

To execute the tests, run:

```sh
uv run pytest
# Or with the venv activated:
pytest
```

### Linting

This project uses ruff, you can run it as:

```sh
uv run ruff check
# Or with the venv activated:
ruff check
```

### Type checking

You can also check your code with ty/mypy:

```sh
uv run ty check
uv run mypy
# Or with the venv activated:
ty check
mypy
```
