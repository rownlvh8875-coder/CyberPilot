"""Owned bounded batch preflight. No model imports, execution or publication."""

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from .scenario_input import MAX_BYTES, ScenarioError, ScenarioSpec, parse_scenario

ROOT = Path(__file__).resolve().parents[1]


class BatchError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class BatchInput:
    source_path: Path
    label: str
    raw: bytes | None
    digest: str | None
    spec: ScenarioSpec | None
    rejection_code: str | None


def _read(path: Path) -> bytes:
    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        with os.fdopen(os.open(path, flags), 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ScenarioError('SCENARIO_INPUT_FILE')
            raw = stream.read(MAX_BYTES + 1)
    except (OSError, AttributeError) as error:
        raise ScenarioError('SCENARIO_INPUT_FILE') from error
    if len(raw) > MAX_BYTES:
        raise ScenarioError('SCENARIO_SIZE')
    return raw


def prepare_batch(inputs: list[Path], output: Path) -> list[BatchInput]:
    if output.exists() or output.is_symlink():
        raise BatchError('BATCH_OUTPUT_EXISTS')
    if not output.parent.is_dir():
        raise BatchError('BATCH_OUTPUT_PARENT')
    try:
        destination = output.resolve()
        if destination.is_relative_to(ROOT):
            raise BatchError('BATCH_OUTPUT_LOCATION')
    except (OSError, RuntimeError) as error:
        raise BatchError('BATCH_OUTPUT_LOCATION') from error
    if not 1 <= len(inputs) <= 32:
        raise BatchError('BATCH_INPUT_COUNT')
    resolved = []
    for path in inputs:
        try:
            path.name.encode('utf-8', errors='strict')
            # Do not follow the final component: a rejected symlink must not
            # suppress a separately supplied valid file as a duplicate.
            resolved.append(path.parent.resolve() / path.name)
        except (OSError, RuntimeError, UnicodeError) as error:
            raise BatchError('BATCH_INPUT_LOCATION') from error
        if resolved[-1].is_relative_to(destination):
            raise BatchError('BATCH_OUTPUT_LOCATION')
    if len(set(resolved)) != len(resolved):
        raise BatchError('BATCH_DUPLICATE_INPUT')
    items = []
    for path in inputs:
        raw, digest, spec, rejection = None, None, None, None
        try:
            raw = _read(path)
            digest = hashlib.sha256(raw).hexdigest()
            spec = parse_scenario(raw)
        except ScenarioError as error:
            rejection = error.code
        items.append(BatchInput(path, path.name, raw, digest, spec, rejection))
    if sum(len(item.spec.samples) for item in items if item.spec is not None) > 8192:
        raise BatchError('BATCH_SAMPLE_COUNT')
    return items
