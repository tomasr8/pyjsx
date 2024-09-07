# Contributing

Have you found a bug or do you have an idea for a new feature? Feel free to open
an issue and/or submit a PR!

## Developing

To contribute to this project, a development environment is recommended. You'll
need Python >= 3.12.

```sh
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"  # Install the project, including the 'dev' extra
```

## Running tests and linters

To execute the tests, run:

```sh
pytest --no-cov
```

This project uses ruff, you can run it as:

```
ruff check pyjsx/ tests/
```

You can also check your code with pyright:

```sh
pyright
```

