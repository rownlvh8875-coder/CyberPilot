# Cyber AutoTune v2 offline contract boundary

## Identity and purpose

- Area: AutoTune / Validation. Status: implemented; synthetic/affected checks passed; broad regression BLOCKED by timeout.
- Baseline: 1ee1eb07f6cc48526f4d61265abe317fe67cc23b; branch feature/cyber-autotune; uncommitted.
- Scope: pure Python unit and metric contracts and preflight checks. No search,
  runtime profile, controller, Params, device, CAN, data loader or plant changes.
- Vehicle applicability: vehicle-independent input validation, not a vehicle calibration.

## Original references

- CyberPilot https://github.com/rownlvh8875-coder/CyberPilot at the baseline above,
  inherited MIT licensing; no new fork code copied.
- Reuse controls/lib/cyber_lateral/command_domain.py:OfflineTorqueCommandContract
  and metrics.py:compute_lateral_metrics. Preserve their existing calculation.
- Caller-supplied immutable metric input -> existing public metrics -> v2 naming
  adapter -> strict local non-regression report. No production controller callers.
- opendbc 4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76 unchanged.
- No model/firmware/data identity is fabricated: supplied digests are bindings,
  not proof of their authenticity. Evidence verification is a separate next stage.

## Changes and expected effect

- Add openpilot/tools/cyber_autotune/contracts.py, preflight.py, synthetic tests.
- Add this record. No upstream integration points.
- Explicit command rate/units, fixed alignment/deadband and input/config bindings;
  reject missing required metrics/coverage and unknown/unreviewed search parameters.
- Normalized friction and acceleration-factor units are separate from Nm. No
  device-specific values are defaults and no Mazda constants are imported.
- No state evolution/reset: pure functions. Reset policy is externally frozen and bound.
- Reversal events/s and equivalent cycle proxy are not PSD oscillation frequency.
- Existing safety, override, longitudinal and runtime admission remain untouched.
- Maintenance: small isolated tools package; v1 receipts and evaluator unchanged.

## Regression risk and acceptance

- Risks: malformed numeric records, dimension confusion, missing primary truth,
  empty strata passing vacuously, candidate-specific lag, forged/self-declared hashes.
- Predeclared acceptance: every required local metric must be valid and no worse
  (strict ratio 1.0; edge margin higher is better); no smoothness/error tradeoff.
- A local metric pass is not development qualification or permission to generate
  candidates. Evidence, repeated A/A, uncertainty and reviewed improvement gates remain required.
- Input: synthetic fixtures only. No holdout, private logs or simulator opened.
- Rollback: package has no runtime importer; removing only its new files removes
  this experiment without reverting existing user edits.
- Promotion authority: no runtime approval. Independent review before future integration.

## Validation method and actual results

| Check | Planned method | Actual status |
| --- | --- | --- |
| Contract tests | tools/test_runner.py openpilot/tools/cyber_autotune/tests -j 2, Ubuntu 24.04/Python 3.12.13 | PASS: 32 tests, exit 0; missing APIs and seven review regressions reproduced RED first |
| Existing admission | lateral + long unit suite | baseline 20 passed, exit 0 |
| Affected regression | tools/test_runner.py openpilot/selfdrive/controls/tests openpilot/tools/cyber_autotune/tests -j 2 | PASS: 164 tests, exit 0, also rerun with venv bin on PATH |
| Lint / whitespace / preservation | Ruff, git diff --check, git diff --exit-code HEAD on selfdrive/opendbc/panda/runner | PASS; no runtime source changes |
| Default PC runner | tools/test_runner.py -j 4 -v, process-local venv PATH, diagnostic start/end tracing, bounded 300 seconds | BLOCKED: 1146 collected, no final summary; still awaiting upstream LogReader fixture in TestLagd.test_read_invalid_saved_params; wrapper forcibly ended after grace (host exit 1). Not a full-suite PASS |
| Initial audio test failure | test_loggerd.TestLoggerd.test_record_audio_0 | reproduced without venv bin on PATH; existing ffprobe present in venv; both record_audio cases PASS (2, exit 0) with process-local PATH corrected, no code edits |
| Replay / closed loop / shadow | separate later qualification | NOT RUN |

## Handoff

Independent review identified phase-local regression masking, malformed metric
records, oversized-integer overflow and nonfinite derived command rates. Seven
new tests reproduced all findings; all 32 passed after the bounded fix pass.
Full manifest authenticity, coverage derivation, A/A, uncertainty and minimum
primary improvement remain explicitly deferred, not silently accepted. PSD peak
frequency remains diagnostic rather than a monotonic loss. No commit/push/merge
or road-use decision. Existing v1 metrics and frozen receipts remain unchanged.

Default tests may create synthetic logs and read upstream public test fixtures;
no personal development corpus or holdout has been opened for this feature.
Next stage: explicit allowlisted evidence manifests, authentic source/configuration
binding, coverage provenance, independent center truth and reviewed search bounds.
