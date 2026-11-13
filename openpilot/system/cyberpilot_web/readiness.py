"""Static source readiness only. Never executes launchers, build or deployment."""

import re
from pathlib import Path


def inspect_readiness(root: Path) -> dict:
  root = root.resolve()
  names = ["launch_openpilot.sh", "launch_chffrplus.sh", "launch_env.sh", "openpilot/system/manager/manager.py"]
  launcher = root / "launch_chffrplus.sh"
  if launcher.resolve().is_relative_to(root) and launcher.is_file():
    source = launcher.read_text(encoding="utf-8")
    for _symbol, relative in re.findall(r'^\s*(AGNOS_PY|MANIFEST)="\$DIR/([^"\n]+)"', source, re.MULTILINE):
      if "$" in relative or ".." in Path(relative).parts or Path(relative).is_absolute():
        names.append("UNRESOLVED_LAUNCH_RESOURCE")
      else:
        names.append(relative)
    if not all(re.search(rf'^\s*{symbol}="\$DIR/', source, re.MULTILINE) for symbol in ("AGNOS_PY", "MANIFEST")):
      names.append("UNRESOLVED_LAUNCH_RESOURCE")
  resources = {name: (root / name).resolve().is_relative_to(root) and (root / name).is_file() for name in names}
  modules = ("msgq_repo", "opendbc_repo", "panda", "rednose_repo", "teleoprtc_repo", "tinygrad_repo")
  missing = [name for name in modules if not (root / name / ".git").exists()]
  return {"schema_version": 1, "source_resources": resources,
          "source_resources_complete": all(resources.values()), "uninitialized_submodules": missing,
          "inspection_scope": "STATIC_RESOURCE_EXISTENCE_ONLY_NO_BUILD_OR_DEVICE_VALIDATION",
          "device_installation_qualified": False, "control_activation_allowed": False,
          "remaining_device_checks": ["actual_target_identification", "native_build", "boot_start_update_restore",
                                      "authenticated_phone_connection", "vehicle_qualification"],
          "rate_budget": "UNRESOLVED", "static_evidence_gate": "FAIL"}
