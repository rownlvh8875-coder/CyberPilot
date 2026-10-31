"""Development tests/runner source selectors only; never shipped in the wheel."""
import importlib
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def package_feature(name="cyberlateral_dev"):
    source = str(ROOT / "src")
    if source not in sys.path:
        sys.path.insert(0, source)
    if importlib.util.find_spec("cyberlateral_dev") is None:
        raise AssertionError("Missing planned CyberLateral package")
    if importlib.util.find_spec(name) is None:
        raise AssertionError(f"Missing planned module: {name}")
    return importlib.import_module(name)
