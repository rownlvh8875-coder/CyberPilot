"""Closed retained registry, not configuration or numerical/vehicle authority."""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / 'reference/r27_suite_profiles_v1.json'
REGISTRY_SHA256 = 'b51d265b8dbd01b7efb1d1bb35529a3fc080201e59bf4936842097a41168ce18'
STAGE_IDS = ('R19', 'R20', 'R21', 'R22', 'R23', 'R24', 'R25', 'R26')
MODES = (None, 'owned_boundary', 'semantic_bridge', 'model_consumption', 'model_sequence', 'fault_boundaries', 'driver_boundaries', 'negative_cycle')


@dataclass(frozen=True, slots=True)
class Profile:
    stage_id: str
    mode: str | None
    status: str
    observations_sha256: str
    case_count: int | None
    model_steps_per_worker: int
    reference_sha256: str | None
    tool_sources: tuple[str, ...]


def load_profiles() -> tuple[Profile, ...]:
    if REGISTRY_PATH.is_symlink() or not REGISTRY_PATH.is_file() or REGISTRY_PATH.stat().st_size > 32_768:
        raise ValueError('SUITE_PROFILE_IDENTITY')
    raw = REGISTRY_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != REGISTRY_SHA256:
        raise ValueError('SUITE_PROFILE_IDENTITY')
    data = json.loads(raw)
    profiles = tuple(Profile(row['stage_id'], row['mode'], row['status'], row['observations_sha256'], row['case_count'],
                             row['model_steps_per_worker'], row['reference_sha256'], tuple(row['tool_sources'])) for row in data['profiles'])
    if (tuple(p.stage_id for p in profiles) != STAGE_IDS or tuple(p.mode for p in profiles) != MODES
            or any(type(p.model_steps_per_worker) is not int or p.model_steps_per_worker < 0 for p in profiles)):
        raise ValueError('SUITE_PROFILE_IDENTITY')
    for profile in profiles:
        if not re.fullmatch('[0-9a-f]{64}', profile.observations_sha256):
            raise ValueError('SUITE_PROFILE_IDENTITY')
        for key in profile.tool_sources:
            path = PurePosixPath(key)
            if path.is_absolute() or '..' in path.parts or not (key in ('run.py', 'worker.py') or path.parts[0] in ('native_qualification', 'integration_tools')):
                raise ValueError('SUITE_PROFILE_IDENTITY')
    return profiles


def get_profile(stage_id: str) -> Profile:
    if type(stage_id) is not str or stage_id not in STAGE_IDS:
        raise ValueError('SUITE_STAGE')
    return next(profile for profile in load_profiles() if profile.stage_id == stage_id)
