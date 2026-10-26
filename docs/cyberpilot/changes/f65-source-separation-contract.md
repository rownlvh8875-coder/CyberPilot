# F-65 Source separation and fail-closed result gate

## Scope and authority
Continuation of the next isolated offline task requested after F64 closure. Preserve F64_HOLDOUT_FAIL, all prior seals/source and real6000 unqualified inputs. No Controller/Plant/RLOG/candidate/device/actuation. Local preregistration/evidence commits only; no Push/manual CI/PR authority inferred.

## Root cause
F64 mapped uint64 seed to amplitude32+seed%32. Different seeds therefore produced identical actual source arrays. F64 failed on5/14 valid evaluation fixtures. That observed result is permanent exposed development evidence. New version cannot choose/retry seeds after evaluation or merely add a seed tag to change a byte hash.

## Normative scalar format and arithmetic
Reuse the unchanged F64_SYNTHETIC_SOURCE_V1 data format, exact signed-int64 ns/value validation and independent F64 Fraction-production/integer-oracle metric functions. New generator provenance is F65_SEPARATED_ACTUAL_SIGNAL_V1; no historical source labels or actual Controller qualification are changed.
Actual fingerprint includes all absolute times_ns and reduced rational sample values, and excludes filenames/case labels/provenance. Equivalent rational encodings must fingerprint equally. No time sorting or normalization. Preserve float rejection and int64 boundaries.

## Injective seed encoding and split proof
D=2^63-1 (existing positive int64 maximum).
A=2^62+(seed>>2), seed is exact uint64. Thus0.5<A/D<=1.
The first actual sample is+A/D for PUBLIC and-A/D for EVALUATION. This is a real observation value, not metadata. The first interval is10000000-(seed&3)ns; count is2..8000.
For fixed family/count, equal first rational values imply equal high62 seed bits because D is fixed; equal first intervals imply equal low2 bits. The actual value/time sequence therefore identifies the entire seed. No modulo-amplitude collapse.
Across splits first values have strictly opposite signs, so equal normalized observation arrays are impossible for every permitted seed/family/count, without evaluating/selecting seeds.
F64 exposed fixtures have abs(values)<=63/1024<0.5, so their first values cannot equal the new EVALUATION first value. Verify the actual captured sources too.
This deliberately constructed domain separation is a software-contract test distribution. It does NOT establish statistical independence, realistic driving, candidate generalization or performance improvement. Do not hide this limitation.

## Families
constant, integer-quantized linear_ramp, piecewise_constant, piecewise_linear, deterministic_pulse, bounded_noise, irregular_valid. Every first numerator is A with split sign. Remaining shape coefficients are deterministic integers bounded by A. Integer division in ramp shapes is explicit. No existing model/tuning value changes.
Noise uses SHA256(b'F65_NOISE_V1:'+uint64seed big-endian8+uint64index big-endian8), first8 bytes modulo(2*A+1)-A. No PRNG-quality claim.
All intervals are nominal-(seed&3), except subsequent even-index intervals in irregular_valid use half-nominal-(seed&3). The first interval always encodes the two low bits.

## Preregistered allocation
Public seeds0/1,7families,count17. New evaluation seeds derive ONLY after the source commit via SHA256(ASCII 'F65_HOLDOUT_V1:'+lowercase40hex PRE_HOLDOUT_COMMIT), first8 and next8 bytes big-endian uint64. Both seeds are retained; no search/retry/filter.
One adjudication cohort has two preplanned independent fresh-process/worktree passes completed before inspection. Failure means seal unchanged; new stage required for fixes. F64 old public/evaluation sources are exposed regression data only.

## Gates
Expected14 valid cases per split, all exact production/oracle metrics equal. Novelty is normalized actual signal/time equality, not filename/metadata inequality; expected overlap with PUBLIC and exposed F64 is0.
Result gate accepts ONLY F65_SOURCE_SEPARATION_PARTIAL_PASS_R_BUDGET_UNRESOLVED with verified14 case artifacts/manifest/source proof, zero overlap and no Controller/runtime/candidate authority.
Fail/blocked/unknown/missing statuses, including authentic F64_HOLDOUT_FAIL, must return nonzero even when unit tests pass. A claim boolean is insufficient: verify stored fixture hashes, regenerate from preregistered specifications, recompute canonical actual fingerprints and compare metrics.
r remains R_BUDGET_UNRESOLVED. No rate budget, vehicle threshold or candidate admissibility is defined. A Source-only partial pass never promotes full prospective evaluation.

## Preservation and CI
Work on feature/f65-source-separation-contract based04ae0f6644c7e94b8ed601c46fc45ccff03d0476. Existing files/workflows are immutable; new independent workflow only. Preserve413 sealed reference files and original worktrees.
Commit code/criteria/public evidence before deriving evaluation seeds. No source/contract/test/workflow edits after inspection. Second commit may add evidence/seal only.
New CI job must run exact new tests, retained F64 tests and the terminal result bundle gate. Remote CI remains NOT_RUN without current Push authority.
