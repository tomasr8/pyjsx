import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


def run_example(name: str) -> str:
    path = Path(__file__).parents[1] / "examples" / name / "main.py"
    return subprocess.run(  # noqa: S603
        [sys.executable, str(path)], text=True, check=True, capture_output=True
    ).stdout


@pytest.mark.parametrize(
    ("example", "loader"),
    [
        ("table", "codec"),
        ("table", "import_hook"),
        ("props", "codec"),
        ("props", "import_hook"),
        ("custom_components", "codec"),
        ("custom_components", "import_hook"),
        ("custom_elements", "codec"),
        ("custom_elements", "import_hook"),
    ],
)
def test_example(snapshot: Any, example: str, loader: str) -> None:
    snapshot.snapshot_dir = Path(__file__).parent / "data"
    snapshot.assert_match(run_example(f"{example}_{loader}"), f"examples-{example}.txt")
