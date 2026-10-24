# Track E-1: HTTP callback and test isolation contract repair

## Identity and purpose

- Area: UI / Validation. Status: implemented; final regression and hosted CI pending.
- Purpose: two silent logging overrides reject the base class valid `format=`
  keyword with TypeError. Preserve all existing zero-argument and positional
  calls while accepting that documented base-method keyword.
- Scope: two HTTP callbacks, one logger deletion test fixture cleanup,
  additive regression tests and this record. No vehicle applicability or authority.
- Branch: feature/cyber-autotune. Baseline source:
  9a3dbb693d3574abc7d177bf3923e1dcd654c676. Candidate identity is the reviewed
  minimal diff; the eventual commit and hosted run IDs are recorded externally.

## Original references

- Repository: https://github.com/rownlvh8875-coder/CyberPilot, verified feature
  baseline above, under its existing MIT license and attribution.
- Source symbols: make_server.Handler.log_message in
  openpilot/tools/cyber_autotune/approximate_geometry_visualizer.py;
  server.Handler.log_message in
  openpilot/tools/cyber_autotune/private_pixel_review.py.
- Reference: Python3.12 BaseHTTPRequestHandler.log_message(self, format, *args).
  Installed log_request/log_error forward positionally. This repairs a proven
  substitutability defect, not a demonstrated routine HTTP-request crash.
- Existing toolchain: Python3.12.13, ty0.0.80, Ruff0.16.7, codespell2.4.3.
  No dependencies, submodule pins, model identity, or Native configuration change.

## Changes and expected effect

- Add typing.override and annotate the exact optional format keyword and
  variadic arguments with object. Keep the original pass bodies.
- The optional default preserves existing no-argument no-op behavior. It is
  an API compatibility default, not a numeric or controller parameter.
- @override expresses actual inheritance and is recognized by the existing
  Ruff builtin-shadowing rule. No rule, ignore, cast, or Any is added.
- Register restoration of the original os.statvfs before installing the existing
  logger deletion test double. Normal/error exits now restore the exact original
  function through unittest.addCleanup. Existing assertions and fake values stay.
- Original responses, Host/Origin checks, authorization gates, routes,
  serialization, state transitions, calculations and PID/planner logic remain.
- Existing unknown-keyword and duplicate-format calls still reject with
  TypeError. Base-valid format-keyword calls intentionally stop raising.
- The two production callbacks contain no logging or state writes.

## Source identity and preserved contracts

- approximate_geometry_visualizer hashes its executing source at import.
  Its new process source identity legitimately changes; the running-source
  and asset-drift guards remain unchanged. No old SHA is reused or rewritten.
- private_pixel_review is not a member of private_pixel_execution.identity's
  source set. Persisted execution receipts and their validators are unchanged.
- CyberH1 remains untouched: its published server contract enforces a fixed
  source identity. Five other callbacks remain untouched because their bytes
  bind persisted stores or authorizations and need separate version planning.
- Frozen Permit.roots and paired optional inputs are unchanged. Original
  TestCase.run-shadowing fixtures and the original HTTP helper are unchanged;
  the current Full CI V2 contract forbids original-test source changes.
- All historical receipts and scientific source pins remain byte-identical.

## Regression risk and acceptance

- Accept only the two callback fixes, the confirmed nonFrozen logger test
  cleanup, additive regression tests and this record. No workflow, protected
  AutoTune/controls test source, reference or policy edits.
- Existing positional domain and silence must remain identical. Reject unknown
  and duplicate keywords; preserve normal server results and source drift guards.
- New tests live in existing openpilot/tools/lib/tests. The original default
  Unit discovery includes them. Two additional test-isolation cases exercise
  successful and failed original deletion test lifecycles and verify restoration. Existing AutoTune/controls target paths and all
  5,960 contracted IDs remain unchanged, including 5,927 baseline IDs.
- The new source-only tests execute only the exact no-op callback declarations;
  they do not import private tools, start servers or open datasets. Existing
  original viewer tests use generated TEST_ONLY inputs and loopback only.
- No actual private TRAIN/DEV/model/HOLDOUT or vehicle inputs are used.
- Rollback: separately approved normal revert of this focused commit, followed
  by targeted tests and exact-HEAD CI. Never rewrite history or old receipts.
- Independent reviewer must approve contract integrity and final diff before push.

## Validation method and actual results

| Check | Method | Result and limits |
| --- | --- | --- |
| Baseline Static | pinned ty check openpilot, GitLab JSON | 1,151 errors +5 warnings; raw1156 |
| RED | additive callback regression tests on original source | format keyword and signature binding fail for both callbacks |
| Targeted GREEN | new tests plus original approximate/private-pixel/coarse/declared viewer tests | 24 passed,20 subtests passed before final whole-suite run |
| Fixture isolation RED/GREEN | original deletion unittest success/error lifecycle | both leak before repair; exact original statvfs and disk_usage restoration required |
| Protected fixtures/importlib | unchanged original archive/storage/comfort tests | 48 passed,57 subtests passed; existing run shadowing remains approval-only |
| Static delta | identical pinned ty/config, mapped old/new fingerprints | final result recorded externally; raw remaining diagnostics are not suppressed |
| Full Unit / V2 / Shadow / Numerical / Native | unchanged commands and GitHub workflows | pending at record creation; exact new SHA and actual evidence required |
| Replay | no local replay or reference changes | automatically triggered hosted observation remains independent |
| Source integrity/publication |231 Frozen,252 LFS pointers,6 gitlinks, original-test guard | mandatory before commit; final proof recorded externally |

## Handoff

- The intended changes are accepting the base-valid format keyword and
  restoring os.statvfs after the existing logger test fixture completes.
- Numerical equivalence, vehicle performance or full Static restoration is not
  inferred from this callback fix. Static and Replay may remain independently red.
- Scientific/authority state remains D2 PERFORMANCE_NOT_EVALUATED,
  Private E2 NOT_AUTHORIZED, HOLDOUT CLOSED, Vehicle authority NONE,
  selected_candidate=null and selected_policy=null.
- Legacy V1/V2 activation, Required Checks, branch protection and PR Draft state
  are not changed by this patch. PR1 remains open, draft and unmerged.
