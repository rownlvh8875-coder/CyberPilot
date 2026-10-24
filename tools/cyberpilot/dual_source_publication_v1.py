"""UNAPPLIED_REVIEW_ONLY: explicit-source diagnostic publication rehearsal."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PIN = "3c0584fcb25829caaedf6f1213baec2c982299a44377f23bc21d628620602a30"
INVENTORY = None
A_ID = B_ID = None
TRUSTED_B = None


def configure(evidence_root):
  global INVENTORY, A_ID, B_ID, TRUSTED_B
  data = (ROOT / "docs/cyberpilot/changes/dual-source-publication-v1.json").read_bytes()
  if hashlib.sha256(data).hexdigest() != CONTRACT_PIN:
    raise ValueError("PUBLICATION_CONTRACT_IDENTITY_MISMATCH")
  INVENTORY = json.loads(data)
  if any(INVENTORY.get(k) is not False for k in ("effective", "runtime_authorized", "promotion_enabled", "performance_qualified", "publication_admitted")):
    raise ValueError("AUTHORITY_ESCALATION")
  A_ID = INVENTORY["lanes"]["A"]["capsule_identity_sha256"]
  B_ID = INVENTORY["lanes"]["B"]["capsule_identity_sha256"]
  TRUSTED_B = Path(evidence_root) / "B"


CONTRACT = "docs/cyberpilot/changes/capture-only-source-version-v1.json"
VALIDATOR = "tools/cyberpilot/source_version_contract_v1.py"
LEGACY_ERROR = "F-19 Legacy Source Publication: UNRESOLVED ERROR"
AUTHORITY = {
  "effective": False,
  "promotion_enabled": False,
  "runtime_authorized": False,
  "performance_qualified": False,
  "vehicle_authority": "NONE",
  "selected_candidate": None,
  "selected_policy": None,
}
MAX_CHILD_OUTPUT_BYTES = 1024 * 1024
CHILD_TIMEOUT_SECONDS = 30


class AdmissionError(ValueError):
  pass


def need(ok, reason):
  if not ok:
    raise AdmissionError(reason)


def canonical(row):
  return json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(data):
  return hashlib.sha256(data).hexdigest()


def inspect_capsule(root, lane, claimed_identity=None):
  need(lane in ("A", "B"), "UNKNOWN_LANE")
  root = Path(root)
  need(root.is_absolute() and root.is_dir() and not root.is_symlink(), "CAPSULE_UNSAFE_PATH")
  need(not any(p.is_symlink() for p in root.parents), "CAPSULE_UNSAFE_PATH")
  files = {}
  for p in root.rglob("*"):
    need(not p.is_symlink(), "CAPSULE_UNSAFE_PATH")
    if p.is_dir():
      continue
    need(p.is_file(), "CAPSULE_UNSAFE_PATH")
    files[p.relative_to(root).as_posix()] = digest(p.read_bytes())
  expected = INVENTORY["lanes"][lane]
  need(set(files) == set(expected["files_sha256"]), "CAPSULE_FILE_SET_MISMATCH")
  need(files == expected["files_sha256"], "CAPSULE_SOURCE_MISMATCH")
  identity = digest(canonical({"lane": lane, "head": INVENTORY["head"], "files_sha256": files}))
  need(identity == expected["capsule_identity_sha256"], "CAPSULE_IDENTITY_MISMATCH")
  if claimed_identity is not None:
    need(claimed_identity == identity, "CLAIMED_SOURCE_IDENTITY_MISMATCH")
  return identity


def child(command, lane):
  with tempfile.TemporaryDirectory(prefix="f22-" + lane + "-process-") as directory:
    cache = Path(directory) / "cache"
    cache.mkdir()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TMPDIR=directory, XDG_CACHE_HOME=str(cache), GIT_OPTIONAL_LOCKS="0")
    result = subprocess.run(command, cwd=directory, env=env, capture_output=True, timeout=CHILD_TIMEOUT_SECONDS)
    need(len(result.stdout) + len(result.stderr) <= MAX_CHILD_OUTPUT_BYTES, "CHILD_OUTPUT_LIMIT")
    return result


def probe_candidate(root, contract=None):
  # Execute only the authenticated F21 implementation; candidate data is read, never imported.
  inspect_capsule(TRUSTED_B, "B")
  path = TRUSTED_B / VALIDATOR
  cmd = [
    sys.executable,
    "-I",
    "-B",
    str(path),
    "--source-root",
    str(Path(root).absolute()),
    "--contract",
    str(contract or (TRUSTED_B / CONTRACT)),
    "--source-version",
    "SOURCE_B_F19_CAPTURE_ONLY_LOCAL_V1",
  ]
  result = child(cmd, "B-validator")
  need(result.returncode in (0, 2) and not result.stderr, "CANDIDATE_CHILD_EXECUTION_FAILURE")
  row = json.loads(result.stdout)
  need((result.returncode == 0) == (row.get("status") == "STRUCTURALLY_VALID"), "CANDIDATE_CHILD_STATUS_MISMATCH")
  need(all(row.get(k) == v for k, v in AUTHORITY.items()), "AUTHORITY_ESCALATION")
  return row


def run_lane(root, lane):
  identity = inspect_capsule(root, lane)
  result = child([sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--legacy-worker", str(root)], lane + "-legacy")
  need(result.returncode == 0 and not result.stderr, "LEGACY_CHILD_EXECUTION_FAILURE")
  legacy = json.loads(result.stdout)
  records = legacy["records"]
  counts = {status: sum(row["status"] == status for row in records) for status in ("passed", "error")}
  need(len(records) == 7 and sum(counts.values()) == 7, "LEGACY_RESULT_CONTRACT_MISMATCH")
  expected = {"passed": 7, "error": 0} if lane == "A" else {"passed": 6, "error": 1}
  need(counts == expected, "LEGACY_RESULT_CONTRACT_MISMATCH")
  if lane == "B":
    errors = [row for row in records if row["status"] == "error"]
    need(
      len(errors) == 1 and errors[0]["id"].endswith(".test_source_binding") and "INJECTION_SOURCE_DRIFT" in errors[0]["detail"],
      "LEGACY_REJECTION_REASON_MISMATCH",
    )
  candidate = probe_candidate(root) if lane == "B" else None
  inspect_capsule(root, lane, identity)
  return {
    "lane": lane,
    "source_identity": identity,
    "source_anchor_sha256": INVENTORY["lanes"][lane]["source_anchor_sha256"],
    "legacy_counts": counts,
    "legacy_records": records,
    "module_origins": legacy["module_origins"],
    "legacy_observation": "PASS" if lane == "A" else "EXPECTED_REJECTION",
    "candidate_status": candidate["status"] if candidate else "NOT_APPLICABLE",
    "candidate_result_sha256": digest(canonical({k: v for k, v in candidate.items() if k != "source_root"})) if candidate else None,
    "candidate_contract_sha256": candidate["contract_sha256"] if candidate else None,
    "native_updates": legacy["native_updates"],
    **AUTHORITY,
  }


def admit(a, b):
  need(a.get("lane") == "A" and b.get("lane") == "B" and a.get("source_identity") == A_ID and b.get("source_identity") == B_ID, "LANE_RESULT_BINDING_MISMATCH")
  need(all(row.get(k) == v for row in (a, b) for k, v in AUTHORITY.items()), "AUTHORITY_ESCALATION")
  need(a.get("legacy_counts") == {"passed": 7, "error": 0} and b.get("legacy_counts") == {"passed": 6, "error": 1}, "LEGACY_RESULT_CONTRACT_MISMATCH")
  need(b.get("candidate_status") == "STRUCTURALLY_VALID", "CANDIDATE_RESULT_NOT_VALID")
  return {
    "schema": "CYBERPILOT_F22_DUAL_SOURCE_REHEARSAL_V1",
    "status": "DUAL_SOURCE_REHEARSAL_VERIFIED",
    "lane_a": a,
    "lane_b": b,
    "publication_admitted": False,
    "admission_scope": "ISOLATED_REHEARSAL_ONLY",
    "runtime_integration": "NO-GO",
    "legacy_source_publication": LEGACY_ERROR,
    "source_b_contract": "VERIFIED",
    **AUTHORITY,
  }


def rehearse(a_root, b_root, claimed_b_identity=None):
  a, b = Path(a_root), Path(b_root)
  need(a.resolve() != b.resolve() and not a.resolve().is_relative_to(b.resolve()) and not b.resolve().is_relative_to(a.resolve()), "SOURCE_ROOTS_NOT_SEPARATE")
  inspect_capsule(a, "A")
  inspect_capsule(b, "B", claimed_b_identity)
  return admit(run_lane(a, "A"), run_lane(b, "B"))


def legacy_worker(source_root):
  import importlib.util

  root = Path(source_root).absolute()
  sys.path.insert(0, str(root))
  spec = importlib.util.spec_from_file_location("f22_exact_project_runner", root / "tools/test_runner.py")
  runner = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(runner)
  assert runner.ROOT == root
  tests, errors = runner.collect([str(root / "openpilot/tools/cyber_autotune/tests/test_candidate_architecture_publication.py")], None)
  assert not errors and len(tests) == 7, (errors, len(tests))
  records = []
  for batch in runner.make_batches(tests, 1):
    records.extend(runner.run_batch(batch, True))
  from openpilot.tools.cyber_autotune import candidate_architecture as a
  from openpilot.tools.cyber_autotune import candidate_architecture_publication as p

  assert a.ROOT == root and Path(p.__file__).is_relative_to(root)
  origins = {}
  for name, module in sys.modules.copy().items():
    if name.startswith("openpilot"):
      path = getattr(module, "__file__", None)
      if path:
        assert Path(path).is_relative_to(root), (name, path)
        origins[name] = str(Path(path).relative_to(root))
  assert not any(name.startswith("openpilot.selfdrive") for name in sys.modules)
  stable = [{k: v.replace(str(root), "$DECLARED_SOURCE") if isinstance(v, str) else v for k, v in row.items() if k != "time"} for row in records]
  print(json.dumps({"records": sorted(stable, key=lambda row: row["id"]), "module_origins": origins, "native_updates": 0}, sort_keys=True))


def prepare(source_root, evidence_root):
  source, output = Path(source_root), Path(evidence_root)
  need(source.is_absolute() and source.is_dir(), "SOURCE_ROOT_REQUIRED")
  need(output.is_absolute() and not output.exists(), "NEW_EVIDENCE_ROOT_REQUIRED")
  need(not output.resolve().is_relative_to(source.resolve()) and not output.resolve().is_relative_to(ROOT), "OUTPUT_INSIDE_SOURCE")
  prerequisites = INVENTORY["required_source_b_delivery"]
  need(len(prerequisites) == 7, "SOURCE_B_DELIVERY_CONTRACT_REQUIRED")
  need(all((source / name).is_file() for name in prerequisites), "SOURCE_B_DELIVERY_PREREQUISITES_MISSING")
  for name, expected in prerequisites.items():
    path = source / name
    need(not path.is_symlink() and not any(p.is_symlink() for p in path.parents), "SOURCE_B_DELIVERY_UNSAFE_PATH")
    need(digest(path.read_bytes()) == expected, "SOURCE_B_DELIVERY_IDENTITY_MISMATCH")
  output.mkdir(parents=True)
  env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
  for lane, row in INVENTORY["lanes"].items():
    root = output / lane
    root.mkdir()
    for name, expected in sorted(row["files_sha256"].items()):
      if lane == "A":
        origin = row["origins"][name]
        revision = origin.split(":", 1)[1]
        first, _, rest = name.partition("/")
        submodule = origin.startswith("SUBMODULE_GIT_OBJECT:")
        command = ["git", "show", revision + ":" + (rest if submodule else name)]
        data = subprocess.check_output(command, cwd=source / first if submodule else source, env=env)
      else:
        data = (source / name).read_bytes()
      need(digest(data) == expected, "PREPARED_SOURCE_IDENTITY_MISMATCH")
      target = root / name
      target.parent.mkdir(parents=True, exist_ok=True)
      with target.open("xb") as stream:
        stream.write(data)
    inspect_capsule(root, lane)
    for path in sorted(root.rglob("*"), reverse=True):
      path.chmod(0o555 if path.is_dir() else 0o444)
    root.chmod(0o555)


def main():
  import argparse

  parser = argparse.ArgumentParser(description=__doc__)
  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument("--prepare", action="store_true")
  group.add_argument("--run", action="store_true")
  group.add_argument("--legacy-worker")
  parser.add_argument("--source-root", type=Path)
  parser.add_argument("--evidence-root", type=Path)
  parser.add_argument("--output", type=Path)
  args = parser.parse_args()
  if args.legacy_worker:
    legacy_worker(args.legacy_worker)
    return 0
  need(args.evidence_root is not None and args.evidence_root.is_absolute(), "EVIDENCE_ROOT_REQUIRED")
  configure(args.evidence_root)
  if args.prepare:
    need(args.source_root is not None, "SOURCE_ROOT_REQUIRED")
    prepare(args.source_root, args.evidence_root)
    print(json.dumps({"status": "CAPSULES_PREPARED_NOT_ADMITTED"}))
  else:
    need(args.output is not None and args.output.is_absolute() and not args.output.exists(), "NEW_OUTPUT_REQUIRED")
    need(not args.output.resolve().is_relative_to(ROOT) and not args.output.resolve().is_relative_to(args.evidence_root), "OUTPUT_INSIDE_SOURCE")
    result = rehearse(args.evidence_root / "A", args.evidence_root / "B")
    result["driver_sha256"] = digest(Path(__file__).read_bytes())
    with args.output.open("xb") as stream:
      stream.write(canonical(result) + b"\n")
    print(json.dumps({"status": result["status"], "publication_admitted": False}))
  return 0


if __name__ == "__main__":
  sys.exit(main())
