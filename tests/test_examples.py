import subprocess
import sys
from pathlib import Path

import pytest


def run_example(name: str):
    path = Path(__file__).parents[1] / "examples" / name / "main.py"
    return subprocess.run(  # noqa: S603
        [sys.executable, str(path)], text=True, check=True, capture_output=True
    ).stdout


@pytest.mark.parametrize(
    "example",
    [
        "table",
        "props",
        "custom",
    ],
)
def test_example(request, snapshot, example):
    snapshot.snapshot_dir = Path(__file__).parent / "data"
    snapshot.assert_match(
        run_example(example), f"examples-{request.node.callspec.id}.txt"
    )
