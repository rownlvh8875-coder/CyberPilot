"""Public synthetic integrity tests; never fetch real payloads or open private sources."""

import hashlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SPEC = importlib.util.find_spec("tools.cyberpilot.verify_full_ci_lfs")
if SPEC is not None:
  from tools.cyberpilot import verify_full_ci_lfs as v
else:
  v = None

DATA = b"synthetic original bytes\x00\x01"
OID = hashlib.sha256(DATA).hexdigest()
PATH = "openpilot/selfdrive/modeld/models/synthetic.onnx"


class TestLfsRecovery(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(v, "bounded original-byte verifier must exist")
    self.entry = {"path": PATH, "oid": OID, "size": len(DATA)}

  def test_canonical_pointer(self):
    raw = f"version https://git-lfs.github.com/spec/v1\noid sha256:{OID}\nsize {len(DATA)}\n".encode()
    self.assertEqual(v.parse_pointer(raw, PATH), self.entry)

  def test_verified_stream(self):
    with tempfile.TemporaryDirectory() as d:
      self.assertEqual(v.stage_stream(io.BytesIO(DATA), Path(d), self.entry)["sha256"], OID)
      self.assertEqual(v.verify_file(Path(d) / OID, self.entry)["bytes"], len(DATA))

  def test_wrong_sha(self):
    with tempfile.TemporaryDirectory() as d, self.assertRaises(v.IntegrityError):
      v.stage_stream(io.BytesIO(b"x" * len(DATA)), Path(d), self.entry)

  def test_truncated(self):
    with tempfile.TemporaryDirectory() as d, self.assertRaises(v.IntegrityError):
      v.stage_stream(io.BytesIO(DATA[:-1]), Path(d), self.entry)
      self.fail("truncation accepted")

  def test_oversize(self):
    with tempfile.TemporaryDirectory() as d, self.assertRaises(v.IntegrityError):
      v.stage_stream(io.BytesIO(DATA + b"x"), Path(d), self.entry)

  def test_pointer_is_not_payload(self):
    data = b"version https://git-lfs.github.com/spec/v1\noid sha256:" + b"a" * 64 + b"\nsize 1\n"
    e = {"path": PATH, "oid": hashlib.sha256(data).hexdigest(), "size": len(data)}
    with tempfile.TemporaryDirectory() as d, self.assertRaises(v.IntegrityError):
      v.stage_stream(io.BytesIO(data), Path(d), e)

  def test_no_overwrite(self):
    with tempfile.TemporaryDirectory() as d:
      v.stage_stream(io.BytesIO(DATA), Path(d), self.entry)
      with self.assertRaises(FileExistsError):
        v.stage_stream(io.BytesIO(DATA), Path(d), self.entry)

  def test_symlink_destination(self):
    with tempfile.TemporaryDirectory() as d:
      p = Path(d)
      (p / OID).symlink_to(p / "other")
      with self.assertRaises(OSError):
        v.stage_stream(io.BytesIO(DATA), p, self.entry)
      self.assertFalse((p / "other").exists())

  def test_symlink_parent(self):
    with tempfile.TemporaryDirectory() as d:
      p = Path(d)
      (p / "real").mkdir()
      (p / "alias").symlink_to(p / "real")
      with self.assertRaises(OSError):
        v.stage_stream(io.BytesIO(DATA), p / "alias", self.entry)

  def test_hardlink_rejected(self):
    with tempfile.TemporaryDirectory() as d:
      p = Path(d)
      (p / OID).write_bytes(DATA)
      os.link(p / OID, p / "alias")
      with self.assertRaises(v.IntegrityError):
        v.verify_file(p / OID, self.entry)

  def test_traversal(self):
    for name in ("../x", "/x", "a/../x", "a//x", "a\\x"):
      with self.subTest(name=name), self.assertRaises(v.IntegrityError):
        v.validate_entry({**self.entry, "path": name})

  def test_corrupt_cache(self):
    with tempfile.TemporaryDirectory() as d:
      p = Path(d) / OID
      p.write_bytes(b"x" * len(DATA))
      with self.assertRaises(v.IntegrityError):
        v.verify_file(p, self.entry)

  def test_cleanup_rejected_partial(self):
    with tempfile.TemporaryDirectory() as d:
      with self.assertRaises(v.IntegrityError):
        v.stage_stream(io.BytesIO(DATA[:-1]), Path(d), self.entry)
      self.assertEqual(list(Path(d).iterdir()), [])

  def test_error_classification(self):
    self.assertEqual(v.classify_http(403), "AUTHORIZED_CREDENTIAL_REQUIRED")
    self.assertEqual(v.classify_http(404), "NOT_FOUND_OR_NOT_AUTHORIZED")
    self.assertEqual(v.classify_http(503), "TRANSIENT_SERVICE_FAILURE")

  def test_unknown_never_optional(self):
    with self.assertRaises(v.IntegrityError):
      v.require_full_success(self.success_evidence(stages={"setup": "success"}), "a" * 40)

  def test_skipped_stage_not_full_success(self):
    stages = dict.fromkeys(v.REQUIRED_STAGES, "success")
    stages["build"] = "skipped"
    with self.assertRaises(v.IntegrityError):
      v.require_full_success(self.success_evidence(stages=stages), "a" * 40)

  @staticmethod
  def success_evidence(**changes):
    return {
      "status": "completed",
      "head_sha": "a" * 40,
      "workflow_path": ".github/workflows/cyberpilot.yaml",
      "conclusion": "success",
      "stages": dict.fromkeys(v.REQUIRED_STAGES, "success"),
      **changes,
    }

  def test_exact_success_requires_all_stages(self):
    v.require_full_success(self.success_evidence(), "a" * 40)

  def test_in_progress_is_not_completed_success(self):
    with self.assertRaises(v.IntegrityError):
      v.require_full_success(self.success_evidence(status="in_progress"), "a" * 40)

  def test_wrong_execution_commit(self):
    with self.assertRaises(v.IntegrityError):
      v.require_full_success({"head_sha": "a" * 40, "workflow_path": ".github/workflows/cyberpilot.yaml"}, "b" * 40)

  def test_offline_is_not_full_ci(self):
    with self.assertRaises(v.IntegrityError):
      v.require_full_success({"head_sha": "a" * 40, "workflow_path": ".github/workflows/cyberpilot-numerical-offline.yaml"}, "a" * 40)

  def test_malformed_pointer(self):
    for raw in (b"", b"version wrong", b"version https://git-lfs.github.com/spec/v1\r\n"):
      with self.subTest(raw=raw), self.assertRaises(v.IntegrityError):
        v.parse_pointer(raw, PATH)

  def test_invalid_descriptor(self):
    for change in ({"oid": "A" * 64}, {"size": True}, {"size": 0}, {"size": -1}):
      with self.subTest(change=change), self.assertRaises(v.IntegrityError):
        v.validate_entry({**self.entry, **change})

  def test_fifo_payload_rejected_without_blocking(self):
    with tempfile.TemporaryDirectory() as d:
      p = Path(d) / OID
      os.mkfifo(p)
      with self.assertRaises(v.IntegrityError):
        v.verify_file(p, self.entry)

  def test_permissions_are_private(self):
    with tempfile.TemporaryDirectory() as d:
      v.stage_stream(io.BytesIO(DATA), Path(d), self.entry)
      self.assertEqual((Path(d) / OID).stat().st_mode & 0o777, 0o600)

  def test_nonexclusive_directory_rejected(self):
    with tempfile.TemporaryDirectory() as d:
      Path(d).chmod(0o755)
      with self.assertRaises(v.IntegrityError):
        v.stage_stream(io.BytesIO(DATA), Path(d), self.entry)

  def test_interrupted_stream_removes_partial(self):
    class Interrupted(io.BytesIO):
      def read(self, size=-1):
        raise OSError("synthetic transport interruption")

    with tempfile.TemporaryDirectory() as d:
      with self.assertRaises(OSError):
        v.stage_stream(Interrupted(DATA), Path(d), self.entry)
      self.assertEqual(list(Path(d).iterdir()), [])

  def test_synthetic_clean_lfs_checkout(self):
    with tempfile.TemporaryDirectory() as d:
      root = Path(d)
      env = {**os.environ, "GIT_LFS_SKIP_SMUDGE": "1", "GIT_TERMINAL_PROMPT": "0"}

      def git(*args):
        return subprocess.check_output(["git", "-C", d, *args], env=env, stderr=subprocess.STDOUT)

      git("init", "-q")
      git("lfs", "install", "--local", "--skip-smudge")
      (root / ".gitattributes").write_text("*.bin filter=lfs diff=lfs merge=lfs -text\n")
      (root / "fixture.bin").write_bytes(DATA)
      git("add", ".gitattributes", "fixture.bin")
      git("-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.invalid", "commit", "-qm", "synthetic")
      (root / "fixture.bin").write_bytes(git("show", "HEAD:fixture.bin"))
      git("lfs", "checkout")
      self.assertEqual((root / "fixture.bin").read_bytes(), DATA)
      git("lfs", "fsck")


if __name__ == "__main__":
  unittest.main()
