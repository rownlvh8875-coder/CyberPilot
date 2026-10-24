"""UNAPPLIED_PROPOSAL: explicit historical archive routing; no actuation."""
import argparse
from collections import Counter
import hashlib
import io
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest
import zlib

CONTRACT_PIN = "48246918164a39411c3bec2c92377025108fc806f47866ef12e48646f3117671"
HISTORICAL = "d94c908d287d0da389dc552e1d4e26ce6dae7a78"
LIMIT = 16 * 1024**2
AUTHORITY = {
  "effective": False, "runtime_authorized": False, "diagnostic_only": True,
  "promotion_enabled": False, "performance_qualified": False, "publication_admitted": False,
  "vehicle_authority": "NONE", "selected_candidate": None, "selected_policy": None,
}


class BindingError(ValueError):
  pass


def need(condition, reason):
  if not condition:
    raise BindingError(reason)


def digest(data):
  return hashlib.sha256(data).hexdigest()


def canonical(value):
  return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def seal(row):
  unsigned = {k: v for k, v in row.items() if k != "receipt_sha256"}
  return {**unsigned, "receipt_sha256": digest(canonical(unsigned))}


def verify_receipt(row):
  need(row == seal(row), "RESULT_RECEIPT_MISMATCH")


def safe_path(path):
  path = Path(path)
  need(path.is_absolute() and ".." not in path.parts, "ABSOLUTE_SAFE_PATH_REQUIRED")
  need(not path.is_symlink() and not any(p.is_symlink() for p in path.parents), "UNSAFE_PATH")
  return path


def load_contract(path):
  path = safe_path(path)
  need(path.is_file() and path.stat().st_size < LIMIT, "CONTRACT_REQUIRED")
  data = path.read_bytes()
  need(digest(data) == CONTRACT_PIN, "CONTRACT_IDENTITY_MISMATCH")
  row = json.loads(data)
  need(row["schema"] == "CYBERPILOT_F32_HISTORICAL_SOURCE_ROUTING_V2", "CONTRACT_SCHEMA")
  need(row["historical_commit"] == HISTORICAL and set(row["capsules"]) == {"B1", "B2"}, "CONTRACT_SCHEMA")
  need(row["authority"] == AUTHORITY and row["required_checks_replaced"] is False, "AUTHORITY_ESCALATION")
  return row


def git(repo, *args):
  result = subprocess.run(
    ["git", "-C", str(safe_path(repo)), *args], capture_output=True,
    env=dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0"), timeout=30,
  )
  need(result.returncode == 0, "GIT_OBJECT_UNAVAILABLE")
  need(len(result.stdout) < LIMIT, "OBJECT_SIZE_LIMIT")
  return result.stdout


def object_bytes(repo, kind, oid):
  need(kind in ("blob", "tree", "commit") and re.fullmatch("[0-9a-f]{40}", oid), "OBJECT_ID_INVALID")
  need(git(repo, "cat-file", "-t", oid).decode().strip() == kind, "OBJECT_TYPE_MISMATCH")
  data = git(repo, "cat-file", kind, oid)
  identity = hashlib.sha1(kind.encode() + b" " + str(len(data)).encode() + b"\0" + data).hexdigest()
  need(identity == oid, "GIT_OBJECT_HASH_MISMATCH")
  return data


def source_repo(repo, record):
  need(record["repository"] in ("root", "opendbc_repo"), "SOURCE_REPOSITORY_UNSUPPORTED")
  return Path(repo) if record["repository"] == "root" else Path(repo) / "opendbc_repo"


def read_record(repo, record):
  path = record["path"]
  need(not Path(path).is_absolute() and ".." not in Path(path).parts and "\0" not in path, "UNSAFE_SOURCE_PATH")
  source = source_repo(repo, record)
  object_bytes(source, "commit", record["commit"])
  raw = git(source, "ls-tree", "-z", record["commit"], "--", ":(literal)" + path)
  need(raw.count(b"\0") == 1 and b"\t" in raw, "SOURCE_PATH_MISSING")
  header, name = raw[:-1].split(b"\t")
  need(name.decode() == path, "GIT_PATH_MISMATCH")
  need(header.decode().split() == [record["mode"], "blob", record["blob_oid"]], "GIT_BLOB_BINDING_MISMATCH")
  data = object_bytes(source, "blob", record["blob_oid"])
  need(digest(data) == record["sha256"], "GIT_FILE_SHA_MISMATCH")
  return data


def initialize_thin_git(root, head):
  meta = root / ".git"
  (meta / "objects").mkdir(parents=True, exist_ok=True)
  (meta / "refs/heads").mkdir(parents=True, exist_ok=True)
  (meta / "HEAD").write_text(head + "\n")
  (meta / "config").write_text("[core]\n\trepositoryformatversion = 0\n\tbare = false\n")


def store_object(target, kind, oid, data):
  raw = kind.encode() + b" " + str(len(data)).encode() + b"\0" + data
  need(hashlib.sha1(raw).hexdigest() == oid, "GIT_OBJECT_HASH_MISMATCH")
  path = target / ".git/objects" / oid[:2] / oid[2:]
  if not path.exists():
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(zlib.compress(raw))


def export_git_path(repo, target, rec, seen):
  source = source_repo(repo, rec)
  dest = target if rec["repository"] == "root" else target / "opendbc_repo"
  if not (dest / ".git").exists():
    initialize_thin_git(dest, HISTORICAL if rec["repository"] == "root" else rec["commit"])
  keys = [(rec["commit"], "commit"), (rec["blob_oid"], "blob")]
  parents = [""]
  parts = Path(rec["path"]).parts[:-1]
  parents.extend("/".join(parts[:n]) for n in range(1, len(parts) + 1))
  for prefix in parents:
    suffix = ":" + prefix if prefix else "^{tree}"
    keys.append((git(source, "rev-parse", rec["commit"] + suffix).decode().strip(), "tree"))
  for oid, kind in keys:
    key = (str(dest), oid)
    if key not in seen:
      store_object(dest, kind, oid, object_bytes(source, kind, oid))
      seen.add(key)


def type_fix(data):
  need(digest(data) == "e08c243b97d81928194d143f42e79886324f7de88cc7bfb903bc70a8c5ac9028", "TYPE_PARENT_MISMATCH")
  result = data.replace(
    b'    raise ValueError("FINITE_SOURCE_VALUES_REQUIRED")\n',
    b'    raise ValueError("FINITE_SOURCE_VALUES_REQUIRED")\n  native_steer, native_lateral = native_result\n',
  ).replace(b"    tuple(float(v) for v in native_result),", b"    (float(native_steer), float(native_lateral)),")
  need(digest(result) == "a13017c9a03d6075a4bd2f55c7ae0a64c483bc648b7018af238e5bbfb6cf8dde", "TYPE_PROPOSAL_MISMATCH")
  return result


def profile_identity(contract, lane):
  return digest(canonical({"lane": lane, "profile": contract["capsules"][lane], "base_commit": HISTORICAL}))


def build_capsule(repo, contract, lane, output, *, commit=HISTORICAL):
  need(commit == HISTORICAL, "HISTORICAL_COMMIT_MISMATCH")
  need(lane in ("B1", "B2"), "SOURCE_VERSION_UNKNOWN")
  repo, output = safe_path(repo), safe_path(output)
  need(not output.exists() and not output.is_relative_to(repo), "NEW_EXTERNAL_CAPSULE_REQUIRED")
  object_bytes(repo, "commit", commit)
  output.mkdir(parents=True)
  initialize_thin_git(output, commit)
  seen = set()
  for name, rec in contract["origins"].items():
    data = read_record(repo, rec)
    export_git_path(repo, output, rec, seen)
    if lane == "B2" and name == contract["anchor"]:
      data = read_record(repo, contract["source_a_anchor"])
    if lane == "B2" and name == contract["capture"]:
      data = type_fix(data)
    need(digest(data) == contract["capsules"][lane]["files_sha256"][name], "PROPOSAL_SOURCE_MISMATCH")
    target = output / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    target.chmod(0o555 if rec["mode"] == "100755" else 0o444)
  # Existing F21/F23 tests legitimately read these exact historical Git objects.
  # This is a thin local object view, never a newly created commit/history.
  for rec in contract["historical_a_objects"].values():
    export_git_path(repo, output, rec, seen)
  return inspect_capsule(output, contract, lane)


def inspect_capsule(root, contract, lane):
  need(lane in ("B1", "B2"), "SOURCE_VERSION_UNKNOWN")
  root = safe_path(root)
  need(root.is_dir(), "CAPSULE_REQUIRED")
  expected = contract["capsules"][lane]["files_sha256"]
  actual = {}
  for p in root.rglob("*"):
    need(not p.is_symlink(), "UNSAFE_PATH")
    if ".git" in p.relative_to(root).parts or p.is_dir():
      continue
    need(p.is_file(), "NON_REGULAR_SOURCE")
    actual[p.relative_to(root).as_posix()] = digest(p.read_bytes())
  need(set(actual) == set(expected), "CAPSULE_FILE_SET_MISMATCH")
  for name, wanted in expected.items():
    if actual[name] != wanted:
      if name in contract["historical_receipts"]:
        raise BindingError("HISTORICAL_RECEIPT_MISMATCH")
      if name in contract["frozen_source_sha256"]:
        raise BindingError("FROZEN_SOURCE_MISMATCH")
      if name in contract["v1_pins"]:
        raise BindingError("V1_SOURCE_OR_CONTRACT_MISMATCH")
      raise BindingError("CAPSULE_SOURCE_MISMATCH")
  for name, pin in contract["historical_receipts"].items():
    receipt = json.loads((root / name).read_bytes())
    unsigned = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    need(digest(canonical(unsigned)) == pin["receipt_sha256"] == receipt["receipt_sha256"], "HISTORICAL_RECEIPT_MISMATCH")
  object_bytes(root, "commit", HISTORICAL)
  return {
    "lane": lane, "source_version": contract["capsules"][lane]["source_version"],
    "source_identity": profile_identity(contract, lane), "base_commit": HISTORICAL,
    "files": len(actual), "file_inventory_sha256": digest(canonical(actual)),
    "anchor_sha256": actual[contract["anchor"]], "capture_sha256": actual[contract["capture"]],
    "git_view": "THIN_HISTORICAL_OBJECTS_NOT_WHOLE_WORKTREE",
    "whole_historical_A": False, **AUTHORITY,
  }


def verify_current(root, contract):
  root = safe_path(root)
  for name, wanted in current_required(contract).items():
    p = root / name
    need(p.is_file() and not p.is_symlink() and digest(p.read_bytes()) == wanted, "CURRENT_A_SOURCE_MISMATCH")
  return {
    "lane": "A", "source_version": "CURRENT_A_COMPATIBLE_CONTROLSD_NOT_WHOLE_HISTORICAL_A",
    "git_head": git(root, "rev-parse", "HEAD").decode().strip(),
    "source_identity": verify_current_identity(contract),
    "anchor_sha256": digest((root / contract["anchor"]).read_bytes()),
    "whole_historical_A": False, **AUTHORITY,
  }


def validate_records(payload, expected_ids, *, historical_rejection=False):
  need(payload.get("collected_ids") == sorted(expected_ids), "TEST_MANIFEST_MISMATCH")
  rows = payload["records"]
  ids = [r["id"] for r in rows]
  need(len(ids) == len(set(ids)), "DUPLICATE_TEST_ID")
  need(sorted(ids) == sorted(expected_ids), "MISSING_OR_UNKNOWN_TEST_ID")
  counts = dict(Counter(r["status"] for r in rows))
  raw = {"run": len(rows), **{k: counts.get(k, 0) for k in ("passed", "failed", "error", "skipped", "xfailed", "xpassed")}}
  need(payload.get("raw_unittest_counts") == raw, "RAW_RESULT_CONFLICT")
  if historical_rejection:
    need(counts == {"passed": 6, "error": 1} and payload["test_exit_code"] == 1, "HISTORICAL_RESULT_MISMATCH")
    bad = [r for r in rows if r["status"] == "error"]
    need(bad[0]["id"].endswith(".test_source_binding") and "INJECTION_SOURCE_DRIFT" in bad[0]["detail"], "HISTORICAL_REASON_MISMATCH")
  else:
    need(counts == {"passed": len(expected_ids)} and payload["test_exit_code"] == 0, "TEST_NONPASS")
  return counts


def verify_origin_paths(origins, root):
  root = safe_path(root)
  need(all(".." not in Path(p).parts and Path(p).resolve().is_relative_to(root.resolve())
           for p in origins.values()), "IMPORT_ROOT_MIXED")


def run_group(root, contract_path, contract, lane, group):
  before = verify_current(root, contract) if lane == "A" else inspect_capsule(root, contract, lane)
  command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--worker", str(root),
             "--lane", lane, "--group", group, "--contract", str(contract_path)]
  child = subprocess.run(command, capture_output=True, text=True, timeout=120)
  need(child.returncode == 0 and not child.stderr, "TEST_WORKER_EXECUTION_ERROR")
  need(len(child.stdout.encode()) < LIMIT, "RESULT_SIZE_LIMIT")
  payload = json.loads(child.stdout)
  need(payload["source_identity"] == before["source_identity"], "RESULT_SOURCE_MISMATCH")
  verify_origin_paths({k: str(Path(root) / v) for k, v in payload["module_origins"].items()}, root)
  counts = validate_records(payload, contract["test_ids"][group], historical_rejection=lane == "B1" and group == "legacy")
  after = verify_current(root, contract) if lane == "A" else inspect_capsule(root, contract, lane)
  need(before == after, "SOURCE_CHANGED_DURING_TESTS")
  return {
    **before, "group": group, "test_ids": contract["test_ids"][group], "counts": counts,
    "test_exit_code": payload["test_exit_code"], "records": payload["records"],
    "raw_unittest_counts": payload["raw_unittest_counts"],
    "module_origins": payload["module_origins"], "worker_source_sha256": digest(Path(__file__).read_bytes()),
    "actual_child_protocol_exit": child.returncode, "source_unchanged": True,
    "historical_rejection_preserved": lane == "B1" and group == "legacy",
  }


def aggregate(lanes, contract, suites=None):
  need(set(lanes) == {"A", "B1", "B2"}, "LANE_SET_MISMATCH")
  expected = {"A": verify_current_identity(contract), "B1": profile_identity(contract, "B1"), "B2": profile_identity(contract, "B2")}
  versions = {"A": "CURRENT_A_COMPATIBLE_CONTROLSD_NOT_WHOLE_HISTORICAL_A",
              **{k: contract["capsules"][k]["source_version"] for k in ("B1", "B2")}}
  for lane, row in lanes.items():
    need(row.get("lane") == lane and row.get("source_identity") == expected[lane], "LANE_RESULT_BINDING_MISMATCH")
    need(row.get("source_version") == versions[lane], "SOURCE_VERSION_METADATA_MISMATCH")
    anchor = (contract["source_a_anchor"]["sha256"] if lane == "A"
              else contract["capsules"][lane]["files_sha256"][contract["anchor"]])
    need(row.get("anchor_sha256") == anchor, "SOURCE_SHA_METADATA_MISMATCH")
    if lane != "A":
      need(row.get("capture_sha256") == contract["capsules"][lane]["files_sha256"][contract["capture"]],
           "SOURCE_SHA_METADATA_MISMATCH")
    need(all(row.get(k) == v for k, v in AUTHORITY.items()), "AUTHORITY_ESCALATION")
  need(type(suites) is list, "ACTUAL_SUITES_REQUIRED")
  pairs = [(r.get("lane"), r.get("group")) for r in suites]
  need(len(pairs) == len(set(pairs)) and set(pairs) ==
       {("A", "legacy"), ("B1", "legacy"), ("B1", "f21"), ("B1", "f23"), ("B2", "capture")}, "ACTUAL_SUITE_SET_MISMATCH")
  for row in suites:
    lane, group = row["lane"], row["group"]
    need(row["source_identity"] == expected[lane] and row["source_unchanged"] is True, "LANE_RESULT_BINDING_MISMATCH")
    need(row.get("source_version") == versions[lane], "SOURCE_VERSION_METADATA_MISMATCH")
    anchor = (contract["source_a_anchor"]["sha256"] if lane == "A"
              else contract["capsules"][lane]["files_sha256"][contract["anchor"]])
    need(row.get("anchor_sha256") == anchor, "SOURCE_SHA_METADATA_MISMATCH")
    if lane != "A":
      need(row.get("capture_sha256") == contract["capsules"][lane]["files_sha256"][contract["capture"]],
           "SOURCE_SHA_METADATA_MISMATCH")
    need(all(row.get(k) == v for k, v in AUTHORITY.items()), "AUTHORITY_ESCALATION")
    validate_records({**row, "collected_ids": row["test_ids"]}, contract["test_ids"][group],
                     historical_rejection=lane == "B1" and group == "legacy")
  return {
    "schema": "CYBERPILOT_F32_SOURCE_AWARE_AGGREGATION_V2",
    "scope": "INDEPENDENT_SOURCE_RESULTS_NOT_CURRENT_HEAD_FULL_CI",
    "lanes": lanes, "legacy_source_b": "F19_LEGACY_UNRESOLVED",
    "runtime_integration": "NO-GO", "required_checks_replaced": False, **AUTHORITY,
  }


def current_required(contract):
  return {**contract["source_a_current_required"], **contract["v1_pins"]}


def verify_current_identity(contract):
  return digest(canonical(current_required(contract)))


class RecordedResult(unittest.TestResult):
  def __init__(self):
    super().__init__()
    self.records = {}

  def record(self, test, status, detail=""):
    prior = self.records.get(test.id())
    if prior and prior["status"] != "passed":
      return
    self.records[test.id()] = {"id": test.id(), "status": status, "detail": detail}

  def addSuccess(self, test):
    super().addSuccess(test)
    self.record(test, "passed")

  def addError(self, test, err):
    super().addError(test, err)
    self.record(test, "error", self._exc_info_to_string(err, test))

  def addFailure(self, test, err):
    super().addFailure(test, err)
    self.record(test, "failed", self._exc_info_to_string(err, test))

  def addSkip(self, test, reason):
    super().addSkip(test, reason)
    self.record(test, "skipped", reason)

  def addSubTest(self, test, subtest, err):
    super().addSubTest(test, subtest, err)
    if err is not None:
      self.record(test, "failed", self._exc_info_to_string(err, test))

  def addExpectedFailure(self, test, err):
    super().addExpectedFailure(test, err)
    self.record(test, "xfailed")

  def addUnexpectedSuccess(self, test):
    super().addUnexpectedSuccess(test)
    self.record(test, "xpassed")


def flatten(suite):
  for item in suite:
    if isinstance(item, unittest.TestSuite):
      yield from flatten(item)
    else:
      yield item


def worker(root, contract, lane, group):
  root = safe_path(root)
  identity = verify_current(root, contract) if lane == "A" else inspect_capsule(root, contract, lane)
  sys.path.insert(0, str(root))
  if (root / "opendbc_repo").exists():
    sys.path.insert(0, str(root / "opendbc_repo"))
  module = contract["test_files"][group][:-3].replace("/", ".")
  spec = importlib.util.spec_from_file_location(module, root / contract["test_files"][group])
  loaded = importlib.util.module_from_spec(spec)
  sys.modules[module] = loaded
  spec.loader.exec_module(loaded)
  suite = unittest.defaultTestLoader.loadTestsFromModule(loaded)
  ids = sorted(t.id() for t in flatten(suite))
  need(ids == contract["test_ids"][group] and len(ids) == len(set(ids)), "TEST_MANIFEST_MISMATCH")
  result = RecordedResult()
  with __import__("contextlib").redirect_stdout(io.StringIO()):
    suite.run(result)
  origins = {}
  for name, value in sys.modules.copy().items():
    if name.startswith(("openpilot", "opendbc", "tools.cyberpilot.tests")):
      path = getattr(value, "__file__", None)
      if path:
        need(Path(path).is_relative_to(root), "IMPORT_ROOT_MIXED")
        origins[name] = str(Path(path).relative_to(root))
  records = []
  for row in sorted(result.records.values(), key=lambda r: r["id"]):
    records.append({**row, "detail": row["detail"].replace(str(root), "$DECLARED_SOURCE")})
  raw_counts = {
    "run": result.testsRun, "failed": len(result.failures), "error": len(result.errors),
    "skipped": len(result.skipped), "xfailed": len(result.expectedFailures), "xpassed": len(result.unexpectedSuccesses),
  }
  raw_counts["passed"] = raw_counts["run"] - sum(v for k, v in raw_counts.items() if k != "run")
  return {
    "source_identity": identity["source_identity"], "collected_ids": ids, "records": records,
    "raw_unittest_counts": raw_counts,
    "test_exit_code": 0 if result.wasSuccessful() else 1, "module_origins": origins,
  }



def audit_workflow(path):
  import yaml

  text = safe_path(path).read_text()
  row = yaml.load(text, Loader=yaml.BaseLoader)
  need(set(row["on"]) == {"workflow_dispatch"}, "WORKFLOW_AUTOMATIC_TRIGGER")
  need(row["permissions"] == {"contents": "read"}, "WORKFLOW_PERMISSION_ESCALATION")
  need(set(row["jobs"]) == {"diagnostic"}, "WORKFLOW_SCOPE_MISMATCH")
  job = row["jobs"]["diagnostic"]
  need("permissions" not in job and "secrets." not in text, "WORKFLOW_PERMISSION_ESCALATION")
  steps = job["steps"]
  uses = [step["uses"] for step in steps if "uses" in step]
  need(uses == ["actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
                "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9"], "WORKFLOW_ACTION_PIN")
  checkout = next(step["with"] for step in steps if step.get("uses", "").startswith("actions/checkout@"))
  need(checkout.get("persist-credentials") == "false" and checkout.get("fetch-depth") == "0", "WORKFLOW_CREDENTIAL_PERSISTENCE")
  upload = next(step["with"] for step in steps if step.get("uses", "").startswith("actions/upload-artifact@"))
  expected_paths = {"${{ runner.temp }}/f32-v2-run/" + name
                    for name in ("result.json", "lane_A_result.json", "lane_B1_result.json", "lane_B2_result.json")}
  need(set(upload["path"].strip().splitlines()) == expected_paths, "WORKFLOW_ARTIFACT_SCOPE")
  need(not any(word in text for word in ("git push", "gh workflow", "/dev/", "can_send", "Params(")), "WORKFLOW_RUNTIME_AUTHORITY")
  return {"events": ["workflow_dispatch"], "permissions": row["permissions"],
          "external_action_pins": uses, "secrets_access": False, "required_check_replacement": False,
          "GitHub_execution_qualified": False}

def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--contract", type=Path, required=True)
  parser.add_argument("--worker", type=Path)
  parser.add_argument("--group")
  parser.add_argument("--lane", choices=("A", "B1", "B2"))
  parser.add_argument("--repo", type=Path)
  parser.add_argument("--current-root", type=Path)
  parser.add_argument("--output", type=Path)
  args = parser.parse_args()
  contract = load_contract(args.contract)
  if args.worker:
    print(json.dumps(worker(args.worker, contract, args.lane, args.group), sort_keys=True, separators=(",", ":")))
    return 0
  need(args.repo is not None and args.current_root is not None and args.output is not None, "EXPLICIT_ROOTS_REQUIRED")
  output = safe_path(args.output)
  need(not output.exists() and not output.is_relative_to(args.repo)
       and not output.is_relative_to(args.current_root), "NEW_EXTERNAL_OUTPUT_REQUIRED")
  output.mkdir(parents=True)
  b1 = build_capsule(args.repo, contract, "B1", output / "B1")
  b2 = build_capsule(args.repo, contract, "B2", output / "B2")
  a = verify_current(args.current_root, contract)
  suites = [
    run_group(args.current_root, args.contract, contract, "A", "legacy"),
    *[run_group(output / "B1", args.contract, contract, "B1", group) for group in ("legacy", "f21", "f23")],
    run_group(output / "B2", args.contract, contract, "B2", "capture"),
  ]
  result = aggregate({"A": a, "B1": b1, "B2": b2}, contract, suites)
  result["suite_results"] = suites
  receipts = {}
  for lane in ("A", "B1", "B2"):
    selected = [row for row in suites if row["lane"] == lane]
    row = seal({"schema": "F32_SOURCE_SPECIFIC_TEST_RECEIPT_V2", **result["lanes"][lane],
                "suites": selected, "required_check_replaced": False})
    data = canonical(row) + b"\n"
    (output / ("lane_" + lane + "_result.json")).write_bytes(data)
    receipts[lane] = digest(data)
  result["lane_receipt_file_sha256"] = receipts
  result = seal(result)
  (output / "result.json").write_bytes(canonical(result) + b"\n")
  print(json.dumps({"status": "ISOLATED_MIGRATION_REHEARSAL_VALID", "legacy_source_b": "F19_LEGACY_UNRESOLVED"}))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
