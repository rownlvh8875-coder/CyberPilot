# Simulator selective reuse implementation plan

> Use superpowers:executing-plans for native implementation and a fresh independent final review.

Goal: audit exact simulator source and add nonexecuting CyberPilot contracts.
Spec: the user's selective reuse request; required eight JSON artifacts and feature record.
Architecture: retain CyberPilot source/data firewalls; independently implement pure contract validators.
Tech stack: existing Python standard library, SHA-256 receipts, unittest and current CI.

## Global constraints
- Audit CyberPilot 46e41ad2f2e11cd4aee926b47d037c46d226108c; preserve current 3a3bec6f07fc7c217e4c8a024217e755be065261.
- Public 50af6679956ed4ef0f13214f832b8f65e212e370; private 4c2d094f188b072172de6e8d848dfb4a31b23bd9.
- No source copy without license, private raw access, controller/candidate/plant execution, optimizer or holdout opening.
- Historical files remain byte-identical. No new UI/server, device authority or empirical-model admission.
- Explicit commit/push authorization already supplied; same feature branch, no reset or force push.

## Review focus
- Absent public files must not be silently replaced by private files.
- Unknown limit flags stay null; requested/final/raw command representations stay distinct.
- Config/epoch/sequence and consumed snapshot drift must be rejected.
- Exposure identity or model-set changes cannot reopen a closed package.
- Visual time-grid mismatch, extra fields, network hosts and privacy leaks fail closed.

## Task 1: Exact source audit
Files: four simulator audit/identity/matrix/overlap JSON artifacts.
- [x] Verify repository visibility, exact commit/branch, all selected Git blob hashes and license.
- [x] Inspect named source and dependencies without executing simulator modules or reading data.
- [x] Record per-component decision, source symbols, overlap, adaptation and rejected subfeatures.

## Task 2: Contracts and pure scaffolding
Files: simulator_reuse_contracts.py, simulator_reuse_scaffolding.py and test_simulator_reuse.py.
Interfaces: artifacts() -> dict; validate_observations(traces, configs); exposure_plan(binding, previous);
visual_plan(manifests, host); validate_claim(tier, claim).
- [x] Write failing tests for identity, drift, sequence/timing, nullable fields, authority and exact grid.
- [x] Run RED, then implement independently with existing seal/verify functions.
- [x] Run GREEN; build four nonexecuting contracts bound to source audit and historical receipts.
- [x] No actual source reader, observer, rendering, process launch, extraction, tuning or opening API.

## Task 3: Publication and independent review
Files: simulator_reuse_publication.py; feature record.
- [x] Pin eight receipts, sources and existing blockers; verify regeneration and no historical mutation.
- [x] Review diff independently; add regression tests for material findings.
- [x] Full AutoTune, controls, explicit lateral replay, Ruff, syntax, publication/privacy/authority, diff and SCons.

## Task 4: Delivery
- [ ] Commit only additive files, verify no LFS changes, push without force.
- [ ] Wait for exact new HEAD Actions completed/success, fetch, verify origin equality and clean tree.
