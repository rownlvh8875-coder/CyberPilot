# Signal Provenance Implementation Plan

> For agentic workers: use superpowers:executing-plans task-by-task.

Goal: bind raw/normalized command and discrete yaw/device-gyro correspondence.
Architecture: frozen policy/source -> whitelisted numeric extraction ->
TRAIN/DEVELOPMENT selection -> immutable freeze -> new EMBARGO-yaw holdout ->
optional yaw-only fit/evaluation -> strict aggregate publication.
Spec: docs/cyberpilot/changes/empirical-signal-provenance-completion.md.
Stack: existing Python/NumPy/pycapnp/zstandard, single-thread deterministic.

Global constraints: old empirical modules/receipts unchanged; no Stage A refit,
TA/SG execution, images, GPS/model payloads, production or vehicle writes.
Review focus: CustomSteerMax runtime override; request/output time mismatch;
gyro sensor vs publish time; old holdout reuse; masked history discontinuity.

1. Policy/source: empirical_signal_policy.py + tests. Test missing policy RED;
   freeze four yaw hypotheses, six axis/sign options, lag0/1/2/5/10/20, no
   continuous scale/bias fit, source exact blobs, split reuse/new embargo role,
   no false frame/clean-mask admission. Commit policy before numeric access.
2. Reader: empirical_signal_reader.py + tests. Test field whitelist, same-message
   Float32 command relation, direct gyro-only, no future/gap/duplicate, limits
   unknown; implement source-verified private extraction, repeats/cache pins.
3. Crosscheck: empirical_signal_crosscheck.py + tests. Test discrete unit/sign
   recovery, shared support, no holdout selection, device-frame restriction,
   kinematic support only, yaw-fitting gates, no Stage C. Freeze metric policy.
4. Runner/publication: empirical_signal_run.py + tests. Test exact freeze/open/
   resume, private data rejection, executor/historical pins. Fit optional yaw
   grid only if development gates pass; holdout never reselects. Add aggregate
   receipts/doc results; independent review, full checks, commit/push/CI.
