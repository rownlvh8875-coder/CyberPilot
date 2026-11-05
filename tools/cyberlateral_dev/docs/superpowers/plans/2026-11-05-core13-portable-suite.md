# CORE13 implementation plan

Spec: ../specs/2026-11-05-core13-portable-suite.md
Base: 1716e1c1a9cd0c31b894f296b7c370674a775f55
Execution: inline, continuous; one fresh whole-branch reviewer at end.

## Global constraints

Follow the spec. Preserve prior evidence and worktrees. No vehicle, F61, r, dt,
Controller or Runtime execution; no publication or main integration. Use existing
venv, standard library ZIP and isolated external test/evidence output only.

## Task1: deterministic saved-suite custody boundary

Interfaces: CORE9 capture/decode -> CORE11 report -> CORE12 summary -> pure bundle
builder/verifier -> guarded file API -> CLI. Existing public loaders stay unchanged.

1. Run archived baseline dev.py verify. Expected1212 tests,265 own compiles, static
   checks PASS, frozen wheel3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.
2. Commit this spec/plan. Write failing behavioral tests in
   project/test_core_sequence_portable.py. Expected missing-feature assertions RED.
3. Extract private CORE9 _decode; implement integration_tools/core_sequence_bundle.py,
   integration_tools/core_sequence_portable.py and tools/core_sequence_portable.py.
   Tests cover exact original bytes/metadata/manifests; deterministic outputs;
   explicit SHA before access; bounded malformed ZIP/member/CRC/name handling;
   corrupt report/source/gates/case ID; output/input guards; partial publication
   and readback; CLI failure boundaries; zero execution and old-loader parity.
   Expected focused new tests and CORE9/CORE12 compatibility PASS.
4. Add docs/CORE_SEQUENCE_PORTABLE_CORE13_KO.md, README and backlog links. Run Ruff,
   Ty, Codespell, full dev.py verify. Expected1212+actual new tests,269 own compiles,
   static PASS, frozen wheel unchanged. Commit implementation with test evidence.
5. Fresh full-branch review. Re-grade findings. ONE TDD Important/Critical fix pass
   and full gate if needed; defer minors with record, no rereview.
6. Independently export historical CORE12 saved bytes via API/CLI twice, verify
   explicit SHA and stdlib CRC/manifests; compare bytes and original file hashes.
   Expected identical ZIPs and zero new synthetic steps, saved M/D/R1 each.
7. Record registered source custody, local refs, actual tests/compiles, tool results,
   archive SHA and limitations. Retain local branch and evidence; no push/CI.

## Review focus

Deliberately inspect attacker-controlled ZIP parser allocations and central-dir
boundaries; whole-SHA validation ordering; member identity/CRC/canonical encoding;
source data/report coupling; output overlap and symlink/FIFO guards; write/close/
readback failure receipts; CLI cleanup-before-stdout; accidental execution imports;
compatibility of CORE9 loader extraction; cooperative filesystem race limitations.
