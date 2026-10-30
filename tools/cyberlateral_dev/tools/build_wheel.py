"""Local deterministic wheel build; no upload or vehicle installation."""
import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build_backend import build_wheel


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New directory only")
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError("OUTPUT_EXISTS_NO_BUILD")
    name = build_wheel(str(args.output))
    print(name)
    print(hashlib.sha256((args.output / name).read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
