# Stage1 저장 증거 접근 승인 요청 검토

이번 검토는 비공개 데이터를 읽을 권한을 부여하지 않는다. 어떤 저장 증거를 왜 읽어야 하는지, 어디까지 허용하고 무엇을 금지할지 정한 요청서를 만드는 작업이다.

CyberPilot V4의 학습은 정상적으로 끝났지만 움직임 시작·종료 판단과 정지 상태의 불필요한 tick 변화가 확인됐다. 다른 판단 기준으로 개선되는지는 아직 알 수 없다. 이제 필요한 증거를 더 읽으려면 먼저 정확한 위치·무결성·읽기 범위를 사용자가 결정해야 한다.

현재 공개 hash와 storage receipt는 있지만, 정확한 private host/root/manifest 경로는 확인되지 않았다. 따라서 이번 결론은 **ACCESS_DEFERRED_CANONICAL_ROOT_UNRESOLVED**다. 승인 요청 검토는 완료할 수 있으나 실제 B0/B1 접근은 미승인이다. Private existence check나 E 드라이브 탐색도 하지 않았다.


## 1. Executive summary / 결론

상태: STAGE1_DECISION_EVIDENCE_ACCESS_AUTHORIZATION_REVIEW_COMPLETE / REVIEW_COMPLETE_ACCESS_DEFERRED / B_ACCESS_NOT_GRANTED. **ACCESS_READY=false, B_GRANTED=false, PRIVATE_DATA_OPENED=false**.

최소 다음 요청은 B0의 지정 metadata4개에 대한 identity 검토다. B1은 별도 후보·Fold·role·field·file·integrity 권한이 있어야 하며, 현재 실제 subset은 비어 있다. C집계/D정책/E실험/F독립 HOLDOUT·vehicle은 승인하지 않는다. [요청서](empirical-hurdle-stage1-v4-evidence-access-scope-request.json), [판정](empirical-hurdle-stage1-v4-evidence-access-review-decision.json).

이번 increment는 **NO_E_OUTPUTS**다. 신규 public docs/schema와 공개 검토 helper·로그만 E 밖에 작성한다. 기존 evidence·두 replica·V1 reference·모델·normalizer는 보전한다.


## 2. Baseline / public evidence lock

| 항목 | 검증된 identity |
| --- | --- |
| Repository/branch | rownlvh8875-coder/CyberPilot / feature/cyber-autotune |
| Baseline HEAD | 6b8af85aecc99ad9529e6efa93c3f9b49370284f |
| Original execution HEAD | bd8045ef2a0da62a92603439f38e7740f5923622 |
| Baseline exact-head CI | 39014481034 attempt1 completed/SUCCESS |
| 직전 lock | 55 public /51 seals /17 static sources + workflow |
| 이번 확장 lock | 76 public /71 seals /21 static sources + same workflow |
| Requirements policy receipt | 8d7be8540516f4a10b47fe1a33ab41c36853abbd879e0a3e85b63a527dd4f3e1 |
| 현재 review policy receipt | 24e25e60d307133fc020f229b212a1446360ee179fb5324a534ebabceea20423 |

최신 requirements10JSON+MD와 필요한 공개 actual job/auth/repeatability/readiness·storage receipts, 추가 saved-format/reference source를 별도로 pin했다. 기존 입력 lock은 변경하지 않았다. 모든 공개 bytes를 고정 Git SHA와 SHA256에 대조했고 canonical seal도 검증했다. 원 실행과 동일한 scientific source7개 및 workflow identity도 보전했다. [empirical-hurdle-stage1-v4-decision-policy-requirements-policy.json](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/docs/cyberpilot/changes/empirical-hurdle-stage1-v4-decision-policy-requirements-policy.json) `/input_lock`

Storage migration/amendment receipts 및 source/causal/derived root hash가 과거 V4 authorization과 일치한다. 이는 **공개 기록의 정합성**이며 현재 canonical path나 live E identity를 증명하지 않는다. Legacy D 계약과 amended E_EXTERNAL_SSD 계약도 역사적 선언으로 분리한다. [empirical-hurdle-stage1-v3-storage-migration-verification.json](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/docs/cyberpilot/changes/empirical-hurdle-stage1-v3-storage-migration-verification.json) `/`; [empirical-hurdle-stage1-v3-external-storage-amendment.json](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/docs/cyberpilot/changes/empirical-hurdle-stage1-v3-external-storage-amendment.json) `/`; [empirical-hurdle-stage1-v3-storage-contract.json](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/docs/cyberpilot/changes/empirical-hurdle-stage1-v3-storage-contract.json) `/`; [empirical-hurdle-stage1-v4-executor-storage-policy.json](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/docs/cyberpilot/changes/empirical-hurdle-stage1-v4-executor-storage-policy.json) `/`

전체 SHA·경로·symbol·원본 pointer는 [public input lock](empirical-hurdle-stage1-v4-evidence-access-public-input-lock.json)에 있다.Containing publication commit은 최종 Git HEAD로 해석하며, 자기 SHA를 파일에 넣는 순환 없이 exact-head CI/clean proof를 커밋 뒤 별도 확인한다.


## 3. 기존 과학적 사실과 한계

기존 STATIC_HIT_LOSS571,317 / MOVE_HIT_GAIN228,164 / NET−343,153과 Gate FP1,662,235 = projected HOLD1,090,918 + harmful571,317을 보전한다.32/32job에서 STATIC loss가 gain보다 컸다. Onset recall A40.195%/B2.147%, termination FP100%bothfolds도 바꾸지 않았다. [empirical-hurdle-stage1-v4-decision-policy-requirements-policy.json](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/docs/cyberpilot/changes/empirical-hurdle-stage1-v4-decision-policy-requirements-policy.json) `/frozen_facts`

Historical ranking improved/equal/worse는 overall32/0/0,PREV_STATIC13/0/19,PREV_MOVE32/0/0이다. Job 평균 AUC와 overlapping count 합계는 구분하며 새 threshold/후보 평가에 사용하지 않는다. Fit support/rank/convergence가 정상인 과거 결과는 이번 review에서 다시 실행하지 않았다. [empirical-hurdle-stage1-v4-decision-policy-requirements-policy.json](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/docs/cyberpilot/changes/empirical-hurdle-stage1-v4-decision-policy-requirements-policy.json) `/frozen_facts`; [empirical-hurdle-stage1-v4-causal-rollout-error-attribution.md](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/docs/cyberpilot/changes/empirical-hurdle-stage1-v4-causal-rollout-error-attribution.md)

원 selection은 HURDLE_STAGE1_V4_NO_ADMISSIBLE_CANDIDATE / MODEL_SELECTION_FAILED_CLOSED / selected=null이다. 추가 factual saved evidence만으로 대체 정책의 Stage2 branch·전체 recursive state·독립 generalization 효과를 입증할 수 없다. [empirical-hurdle-stage1-v4-decision-policy-review-decision.json](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/docs/cyberpilot/changes/empirical-hurdle-stage1-v4-decision-policy-review-decision.json) `/policy_effect_identified`


## 4. Canonical root / manifest 식별 계약

| Identity 구분 | 현재 상태 |
| --- | --- |
| HOST_IDENTITY | UNRESOLVED_HUMAN_PRIVATE_REFERENCE_REQUIRED |
| STORAGE_VOLUME_IDENTITY | HISTORICAL_PUBLIC_HASH_ONLY_LIVE_NOT_VERIFIED |
| EXACT_CANONICAL_ROOT | CANONICAL_ROOT_UNRESOLVED |
| EXACT_MANIFEST_PATH | UNRESOLVED_NO_EXISTENCE_CHECK |
| ORIGINAL_MANIFEST_SHA | PUBLIC_EXPECTED_CANONICAL_IDENTITY_AVAILABLE_NOT_PATH |
| MIGRATION_AMENDMENT | PUBLIC_RECEIPT_LINEAGE_CONSISTENT |
| RUN1_RUN2 | PUBLIC_PAST_REPEATABILITY_PASS_LIVE_CONTENT_NOT_REVERIFIED |
| V1_REFERENCE | PUBLIC_EXPECTED_IDENTITY_AVAILABLE_LIVE_PATH_UNRESOLVED |
| CANDIDATE_FOLD_ROLE | PUBLIC32JOB_CATALOG_VERIFIED_B1_SUBSET_UNSPECIFIED |
| FILE_FIELD_SCOPE | B0_FOUR_NAMED_RECORD_PROPOSAL_B1_SEVEN_ROLE_FIELD_PROPOSAL_NO_GRANT |

공개 SHA는 exact manifest content의 기대 identity를 제공한다. Root hash·volume hash·drive label·mount 선언은 exact private absolute path와 다르다. 현재 host나 root를 확인하려고 hostname/private mount inventory/parent scan/stat를 실행하지 않았다. Missing input을 채우기 위해 E에서 비슷한 manifest를 찾지 않는다.

사용자가 향후 **별도 비공개 승인 기록**에 host와 exact canonical root, 네 metadata의 개별 canonical reference와 기대 identity를 제공해야 한다. Public에는 REDACTED_PRIVATE_REFERENCE만 남긴다. Path fragment를 이어붙여 private path를 복원하는 우회도 금지한다. [empirical-hurdle-stage1-v4-decision-policy-approval-matrix.json](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/docs/cyberpilot/changes/empirical-hurdle-stage1-v4-decision-policy-approval-matrix.json) `/reviewable_package`

| B0 named record ID | 공개 expected canonical receipt SHA256 | 현재 경로 |
| --- | --- | --- |
| V4_REPEAT_1_RUN_MANIFEST | fd3639f93944edecfdfa573818d29fbc8a91ab23208e2d561f8a69726eb0dc64 | REDACTED_PRIVATE_REFERENCE /UNRESOLVED |
| V4_REPEAT_2_RUN_MANIFEST | fd3639f93944edecfdfa573818d29fbc8a91ab23208e2d561f8a69726eb0dc64 | REDACTED_PRIVATE_REFERENCE /UNRESOLVED |
| V1_REFERENCE_REPEAT_1_MANIFEST | c4de3955c12cd0d9721d4c7c1519da53b4d80f80be0c05e142047853a7b217a6 | REDACTED_PRIVATE_REFERENCE /UNRESOLVED |
| V1_REFERENCE_REPEATABILITY_RECEIPT | 3b9e8e1f562972268a7a0543f72d3f98fe237a9f3e1c5e045b69e19f9c69949b | REDACTED_PRIVATE_REFERENCE /UNRESOLVED |

이 표의 canonical receipt digest는 raw file digest가 아니다. 네 metadata 파일을 실제로 열거나 private manifest contents를 복제한 것이 아니다. [empirical-hurdle-stage1-v4-retrospective-execution-authorization.json](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/docs/cyberpilot/changes/empirical-hurdle-stage1-v4-retrospective-execution-authorization.json) `/private_manifest_sha256`; [empirical-hurdle-stage1-v4-retrospective-execution-authorization.json](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/docs/cyberpilot/changes/empirical-hurdle-stage1-v4-retrospective-execution-authorization.json) `/v1_manifest_sha256`; [empirical-hurdle-stage1-v4-retrospective-execution-authorization.json](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/docs/cyberpilot/changes/empirical-hurdle-stage1-v4-retrospective-execution-authorization.json) `/v1_repeatability_sha256`


## 5. B0 — Metadata-only 요청

B0도 현재 NOT_GRANTED다. 향후 exact reference와 별도 human grant가 있을 때만 지정된 네 metadata record의 schema, seal/raw hash/size와 선언된 member identity를 비교하도록 제안한다. Manifest가 나열한 모든 member를 stat/open하는 fanout 권한은 없다. [empirical_hurdle_v4_attribution.py:434 admitted_read_files](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/openpilot/tools/cyber_autotune/empirical_hurdle_v4_attribution.py#L434); [empirical_hurdle_attribution_io.py:166 admit](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/openpilot/tools/cyber_autotune/empirical_hurdle_attribution_io.py#L166)

Array shape/dtype/hash의 **선언값**과 실제 header/payload 검증을 구분한다. 초기 B0에서는 array file existence/header/decompression/digest/숫자값을 확인하지 않는다. 따라서 shape/dtype/live alignment/current payload integrity는 NOT_REVERIFIED이며 whole-source byte immutability도 주장하지 않는다. 네 named metadata 자체의 digest 읽기와 array file digest 읽기는 다른 권한이다.

V4 TRAIN receipt는 B0에서 제외한다. Combined score descriptor와 coefficients descriptor뿐 아니라 private decision도 같은 JSON에 들어 있다. JSON 전체를 parse한 뒤 일부 field를 필터링해도 이미 읽은 sensitive value가 사라지지는 않는다. [empirical_hurdle_v4_execution.py:247 save_train](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/openpilot/tools/cyber_autotune/empirical_hurdle_v4_execution.py#L247)


## 6. B1 — Restricted saved-array 초안

B1은 B0로 자동 부여되지 않는다. 현재 candidate/fold/role subset=[]이며 **HUMAN_NAMED_EXACT_SUBSET_REQUIRED_NO_PERFORMANCE_SELECTION**이다.32job catalog는 상한 identity 목록일 뿐 모든 array/receipt를 읽을 허가가 아니다.

| Role | Owner | Field | 필요한 이유 |
| --- | --- | --- | --- |
| TRAIN | V4 | `combined_probability` | Saved combined original-row-order Stage1 score; not recomputed. |
| TRAIN | V1_REFERENCE | `move_label` | Saved frozen next-change truth label; no target/source reconstruction. |
| TRAIN | V1_REFERENCE | `prior_delta_tick` | Saved prior source-grid increment; converting to nonzero context requires C scope. |
| DEV | V4 | `p_move` | Saved one-step Stage1 score; no inference. |
| DEV | V4 | `predicted_gate` | Saved frozen one-step gate; not projected movement. |
| DEV | V1_REFERENCE | `true_move` | Saved one-step truth label; no need to open target/current ticks in initial B1. |
| DEV | V1_REFERENCE | `prior_delta_tick` | Saved observed prior increment; no actual source-route loading. |

초기 제안은7개 role-field binding이다. TRAIN의 saved move_label, DEV의 saved true_move를 재사용하므로 current/target/actual ticks를 열어 label을 다시 만들 필요가 없다. Original label 대 target/source 의미 검증은 **NOT_REVERIFIED**로 남긴다. Prior delta를 nonzero context로 바꾸는 계산이나 group별 confusion도 B1 identity read가 아니라 별도 C 처리다. [empirical_hurdle_fit_cv_execution.py:127 execute_job](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_execution.py#L127); [empirical_hurdle_fit_cv_data.py:94 one_step](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_data.py#L94); [empirical_s2_ri_reconstruction_math.py:52 context](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/openpilot/tools/cyber_autotune/empirical_s2_ri_reconstruction_math.py#L52)

B1 전에 exact file allowlist, byte/header/decode limits, 모든field의 shape/dtype/hash와 trusted lineage, replica integrity-read permission을 명시해야 한다. Mixed TRAIN carrier는 별도 명시적 carrier-read 권한 또는 신뢰 가능한 minimized descriptor가 필요하다. 후자는 현재 존재·검증하지 않았고, 기존 seal만으로 가공 projection의 신뢰성을 증명할 수 없다. 새로운 reader나 우회 protocol을 이번에 구현하지 않았다.

Private threshold와 coefficient/normalizer/tick/path/command 값은 초기 B1 fields에 없다. M5/M7는 이 최소 fields만으로 완결되지 않는다. Frozen decision value 접근과 적용이 필요하다면 별도의 sensitive input 권한 및 C protocol을 명시하거나 INPUT_INSUFFICIENT로 남겨야 한다.


## 7. 32-job candidate/fold/role catalog

공개 actual job manifest에서16candidate×2fold=32개의 실제 ID와 순서를 확인했다. 새 candidate를 추가하거나 성능순으로 정렬·선택하지 않았다. Public catalog digest와 historical full private job identity는 다른 객체다. [empirical-hurdle-stage1-v4-job-manifest.json](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/docs/cyberpilot/changes/empirical-hurdle-stage1-v4-job-manifest.json) `/jobs`; [empirical-hurdle-stage1-v4-retrospective-execution-authorization.json](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/docs/cyberpilot/changes/empirical-hurdle-stage1-v4-retrospective-execution-authorization.json) `/job_identity_set_sha256`

| Candidate | d | L | Folds / roles |
| --- | --- | --- | --- |
| HRI_D00_L01 | 0 | 1 | FOLD_A/FOLD_B; TRAIN/DEV별 분리 |
| HRI_D00_L05 | 0 | 5 | FOLD_A/FOLD_B; TRAIN/DEV별 분리 |
| HRI_D00_L15 | 0 | 15 | FOLD_A/FOLD_B; TRAIN/DEV별 분리 |
| HRI_D00_L45 | 0 | 45 | FOLD_A/FOLD_B; TRAIN/DEV별 분리 |
| HRI_D05_L01 | 5 | 1 | FOLD_A/FOLD_B; TRAIN/DEV별 분리 |
| HRI_D05_L05 | 5 | 5 | FOLD_A/FOLD_B; TRAIN/DEV별 분리 |
| HRI_D05_L15 | 5 | 15 | FOLD_A/FOLD_B; TRAIN/DEV별 분리 |
| HRI_D05_L45 | 5 | 45 | FOLD_A/FOLD_B; TRAIN/DEV별 분리 |
| HRI_D10_L01 | 10 | 1 | FOLD_A/FOLD_B; TRAIN/DEV별 분리 |
| HRI_D10_L05 | 10 | 5 | FOLD_A/FOLD_B; TRAIN/DEV별 분리 |
| HRI_D10_L15 | 10 | 15 | FOLD_A/FOLD_B; TRAIN/DEV별 분리 |
| HRI_D10_L45 | 10 | 45 | FOLD_A/FOLD_B; TRAIN/DEV별 분리 |
| HRI_D20_L01 | 20 | 1 | FOLD_A/FOLD_B; TRAIN/DEV별 분리 |
| HRI_D20_L05 | 20 | 5 | FOLD_A/FOLD_B; TRAIN/DEV별 분리 |
| HRI_D20_L15 | 20 | 15 | FOLD_A/FOLD_B; TRAIN/DEV별 분리 |
| HRI_D20_L45 | 20 | 45 | FOLD_A/FOLD_B; TRAIN/DEV별 분리 |

각 B1 grant는 이 catalog에서 필요한 정확한 subset을 사람이 명시해야 한다. TRAIN과 DEV는 같은 semantics를 사용하더라도 다른 population이며 서로의 rows를 같은 것으로 취급하지 않는다. Initial one-step scope는 horizon1이며 rollout arrays는 포함하지 않는다.


## 8. Alignment / hash domains / immutable reference

각 field는 trusted run manifest→candidate/fold parent→role population→ordered anchor/count→exact field의 chain으로 연결한다. DEV receipt에는 candidate/fold가 직접 없으므로 parent manifest와 TRAIN_FINALIZED chain까지 확인해야 하며 anchor 하나만으로 job identity를 증명하지 않는다. [empirical_hurdle_v4_execution.py:267 execute_job](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/openpilot/tools/cyber_autotune/empirical_hurdle_v4_execution.py#L267); [empirical_hurdle_v4_attribution.py:478 population](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/openpilot/tools/cyber_autotune/empirical_hurdle_v4_attribution.py#L478)

모든 허용 field의 **전체 shape가[N]**인지 확인해야 한다. Leading dimension만 비교하거나 count가 같다고 alignment를 승인하지 않는다. Ordered anchor는 segment identity/count/index-byte hash의 순서에 묶인다. Reorder/truncate/zip-min-length/reconstruct/impute/conflict를 숨기는cast는 금지한다. 기존matching 함수의 검사보다 엄격한 향후 요구사항이며 이번에 실행하지 않았다. [empirical_hurdle_fit_cv_data.py:61 binding](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_data.py#L61); [empirical_hurdle_v4_attribution.py:532 matching](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/openpilot/tools/cyber_autotune/empirical_hurdle_v4_attribution.py#L532)

| Hash | 대상 |
| --- | --- |
| array_sha256 | SHA256 of contiguous raw element bytes under declared dtype/order; neither file nor receipt hash. |
| file_sha256 | SHA256 of exact stored file bytes, including gzip bytes when compressed. |
| npy_sha256 | SHA256 of decompressed NPY header+payload bytes. |
| receipt_sha256 | SHA256 of canonical receipt body excluding its receipt field. |

Self-consistent seal은 body 무결성을 확인하지만 trusted provenance 자체를 만들지는 않는다. 기대 digest를 고정 public/historical chain에 연결해야 한다. Source에서 보이는 gzip/NPY/raw-array hash를 서로 바꿔 비교해서는 안 된다. [empirical_plant_policy.py:32 canonical](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/openpilot/tools/cyber_autotune/empirical_plant_policy.py#L32); [empirical_hurdle_v4_store.py:92 array_write](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/openpilot/tools/cyber_autotune/empirical_hurdle_v4_store.py#L92); [empirical_hurdle_fit_cv_store.py:66 compressed_array_write](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_store.py#L66)


## 9. RUN1/RUN2 replica 계약

순서는 trusted manifest identity→명시적으로 승인된 byte/content equality→repeat-1 사용 가능 여부→repeat-2 보존이다. 두 replica를 독립 표본으로 합산·평균하지 않는다. Historical public exact repeatability PASS와 replicas retained는 보전하지만 이번에 private replica를 다시 열어 확인한 것은 아니다. [empirical-hurdle-stage1-v4-repeatability-actual.json](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/docs/cyberpilot/changes/empirical-hurdle-stage1-v4-repeatability-actual.json) `/`

Manifest 선언 equality는 현재 payload equality가 아니다. Full authoritative equality를 새로 증명하려면 minimal science fields 밖의 정확한 manifest-listed files를 opaque hash로 읽어야 할 수도 있다. 그 integrity scope가 별도 명시·승인되지 않으면 B1 analysis eligibility를 보류한다. 이를 이유로 coefficient/decision을 decode하거나 모든 디렉터리를 탐색할 권한이 생기지 않는다. Matching replica만으로 independent execution이나 source correctness가 증명되지도 않는다.

기존 source/모델/normalizer/V1 reference와 두 actual replica는 삭제·이동·수정하지 않는다. Before/after verification은 실제 승인된 object 범위를 명시하고, metadata만 검사한 뒤 전체 source bytes가 unchanged라고 과장하지 않는다. Integrity conflict는 access abort이며 과학적 NO_ADMISSIBLE로 바꾸지 않는다.


## 10. M1–M9 및 Approval A–F

| M | 현재 상태 | 처리 경계 |
| --- | --- | --- |
| M1 | PUBLIC_ONLY_AVAILABLE | 실행 미승인; missing이면 insufficient/미식별 유지 |
| M2 | PUBLIC_ONLY_AVAILABLE | 실행 미승인; missing이면 insufficient/미식별 유지 |
| M3 | PUBLIC_ONLY_AVAILABLE | 실행 미승인; missing이면 insufficient/미식별 유지 |
| M4 | SAVED_CONTRACT_NOT_LIVE_VERIFIED | 실행 미승인; missing이면 insufficient/미식별 유지 |
| M5 | TRAIN_GATE_NOT_SAVED_C_AND_EXPLICIT_SENSITIVE_ACCESS_REQUIRED | 실행 미승인; missing이면 insufficient/미식별 유지 |
| M6 | RELIABILITY_PROTOCOL_C_NOT_APPROVED | 실행 미승인; missing이면 insufficient/미식별 유지 |
| M7 | PRIVATE_BOUNDARY_NOT_IN_INITIAL_B1_SCOPE_C_AND_SEPARATE_ACCESS_REQUIRED | 실행 미승인; missing이면 insufficient/미식별 유지 |
| M8 | ALTERNATIVE_EFFECT_REQUIRES_D_E | 실행 미승인; missing이면 insufficient/미식별 유지 |
| M9 | INDEPENDENT_VALIDATION_AND_AUTHORITY_REQUIRED | 실행 미승인; missing이면 insufficient/미식별 유지 |

M1–M3의 기존 overall/state/job/fold 집계는 이미 공개되어 private input이 불필요하다. M4의 source-contract saved 사실은 live storage existence/alignment와 다르다. M5 TRAIN rowwise gate는 **NOT_SAVED**다. Frozen decision application, TRAIN gate reconstruction, new confusion도 별도C 승인 대상이다. M6 bins/구간/suppression과 M7 boundary protocol은 결과를 보기 전에 별도 승인해야 한다. [empirical-hurdle-stage1-v4-decision-policy-evidence-gate.json](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/docs/cyberpilot/changes/empirical-hurdle-stage1-v4-decision-policy-evidence-gate.json) `/requirements`

| Approval | 목적 | 현재 grant |
| --- | --- | --- |
| A | Current public-only authorization-scope review | 이번 public review만 |
| B | Private metadata or saved-array access with separate B0/B1 grants | NOT_GRANTED |
| C | New private processing/aggregate generation, even frozen decision application | NOT_GRANTED |
| D | Policy specification/adoption/change | NOT_GRANTED |
| E | Scientific model/policy execution and validation | NOT_GRANTED |
| F | Independent HOLDOUT and vehicle subauthorities | NOT_GRANTED |

B0≠B1이고 B≠C/D/E/F다. Request review 완료·schema PASS·CI SUCCESS·과거 authorization 어느 것도 실제 B grant가 아니다. F의 HOLDOUT admission과 vehicle activation도 서로 독립 권한이다. M8/M9의 대체 정책 downstream/독립 효과는 factual saved arrays만으로 식별할 수 없다. [empirical-hurdle-stage1-v4-decision-policy-approval-matrix.json](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/docs/cyberpilot/changes/empirical-hurdle-stage1-v4-decision-policy-approval-matrix.json) `/approvals`


## 11. Read-only firewall와 도구 한계

| 기존 함수 | 최소 B0로 재사용 불가 이유 |
| --- | --- |
| empirical_hurdle_v4_store.py verify | Enumerates private tree, hashes all files and decodes all arrays including coefficients. |
| empirical_hurdle_v4_execution.py repeatability | Calls broad saved-store verification; not a minimal metadata comparator. |
| empirical_hurdle_v4_attribution.py admit | Calls repeatability/snapshots, reads result/parent graphs and broad stores. |
| empirical_hurdle_v4_attribution.py admitted_read_files | Expands all manifest members plus causal/derived/source private authorization files. |
| empirical_hurdle_attribution_io.py admit | Verifies whole historical file set and models/populations, beyond minimal access. |
| empirical_hurdle_v4_attribution.py analyze_job | Computes rankings/confusion/context, i.e. C processing and wider saved fields. |

store.verify는 private tree를rglob하고 모든 파일을hash하며 JSON/arrays를 decode한다. Existing repeatability/resume/admit 경로도 별도의 더 넓은 과거 권한을 전제로 한다. 현재 metadata-only 권한으로 호출할 수 없다. [empirical_hurdle_v4_store.py:130 verify](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/openpilot/tools/cyber_autotune/empirical_hurdle_v4_store.py#L130); [empirical_hurdle_v4_execution.py:463 repeatability](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/openpilot/tools/cyber_autotune/empirical_hurdle_v4_execution.py#L463); [empirical_hurdle_v4_attribution.py:453 admit](https://github.com/rownlvh8875-coder/CyberPilot/blob/6b8af85aecc99ad9529e6efa93c3f9b49370284f/openpilot/tools/cyber_autotune/empirical_hurdle_v4_attribution.py#L453)

현재 도구 환경은 unrestricted이며 미래 B OS-level sandbox가 구현됐다고 주장하지 않는다. Current public helper는 명시적 read/write allowlist·stdlib-only·pinned Git read를 사용한다. 이는 process-local 제한과 작업 경로 통제이며 OS전체 격리나 미래 B reader의 보안 증명이 아니다. 새 access reader는 구현하지 않았다. 향후 exact-file/no-traversal/no-alias/read-only enforcement를 독립 검토해야 한다.


## 12. Privacy / storage safety

Public에는 status/공개SHA·receipt/candidate-fold-role/field schema/missing states/승인 경계·protocol만 게시한다. 실제private canonical path·manifest contents·scores/gates/ticks/paths·threshold·coefficients·commands/GPS/timestamps/witness indices·credentials는 게시하지 않는다. Schema field 이름은 payload가 아니다. Sensitive reference는 별도 private 승인 기록에서만 관리하고 public에는 REDACTED_PRIVATE_REFERENCE를 쓴다.

현재 E private source read/discovery/existence/mount inventory와 E new output은 모두 금지한다. **NO_E_OUTPUTS**. 향후 B/C에 output이 필요하면 source/replicas와 disjoint한 exact destination, capacity/reserve, fresh free-space proof를 해당 미래 승인 안에서 따로 지정해야 한다. 이번에는 storage space/live volume을 측정하지 않았고 원본 삭제·이동·정리도 하지 않았다.


## 13. 사용자 판단을 위한 구체적 B0 요청서

**REQUEST_ID=V4_STAGE1_SAVED_EVIDENCE_B0_IDENTITY_REQUEST_V1**. 현재 선택 권고는 **DEFER**다. 다음 표는 요청 범위이며 access grant나 사용자 서명을 대신하지 않는다. [전체 요청 JSON](empirical-hurdle-stage1-v4-evidence-access-scope-request.json).

| 필수 요청 field | 초안 값 / 경계 |
| --- | --- |
| PURPOSE /APPROVAL_LAYER | User decision on a minimal metadata-only identity request; establish whether later saved-field access can be specified without private discovery. /B0_REQUEST_ONLY_B1_SEPARATE |
| CURRENT_GRANT_STATUS | NOT_GRANTED |
| EXACT_HOST_IDENTITY | UNRESOLVED_REDACTED_PRIVATE_REFERENCE |
| EXACT_CANONICAL_ROOT_STATUS | CANONICAL_ROOT_UNRESOLVED |
| EXACT_MANIFEST_REFERENCE_STATUS | PUBLIC_EXPECTED_IDENTITIES_AVAILABLE_EXACT_PRIVATE_PATHS_UNRESOLVED |
| ALLOWED_CANDIDATES/FOLDS/ROLES | 공개16candidate/두fold/TRAIN·DEV catalog identity ceiling; blanket payload권한 아님 |
| ALLOWED_FIELDS | 지정 metadata4개의 schema/seal/rawhash/size/declared identity links만 |
| METADATA_ONLY_SCOPE | B0 proposal only; no array/member stat fanout, header, payload or digest |
| ARRAY_READ_SCOPE | B1 separate request; exact subset=[], current NOT_GRANTED |
| SOURCE_IMMUTABILITY | Zero writes/deletes/moves to all existing V4 replicas, V1 references, models, normalizers, policies and results; hash/stat before/after only within explicitly granted objects. Never claim whole-store proof from metadata-only checks. |
| REPLICA_EQUALITY_REQUIREMENT | Trusted identity -> separately approved byte/content verification -> decide repeat-1 use eligibility -> retain repeat-2; replicas are not samples and are never averaged. |
| ALLOWED_OPERATIONS | 별도 B0 grant 뒤 exact named metadata read/hash/stat와 trusted identity 비교만 |
| FORBIDDEN_OPERATIONS | PRIVATE_DISCOVERY_OR_GLOB_OR_PARENT_SCAN; UNNAMED_MANIFEST_EXISTENCE_CHECK; PRIVATE_MOUNT_ENUMERATION; MODEL_LOADING_FOR_INFERENCE; STAGE1_OR_STAGE2_EXECUTION; REFIT_OR_NORMALIZER_CHANGE; THRESHOLD_READ_OR_APPLICATION_OR_RESELECTION; TRAIN_GATE_RECONSTRUCTION; CALIBRATION_FIT; CONFUSION_OR_RELIABILITY_OR_BOUNDARY_AGGREGATION; NEW_PREDICTION_OR_ROLLOUT; CANDIDATE_SEARCH_OR_SELECTION; RAW_LOG_OR_QLOG; HOLDOUT_OR_DISCOVERY; SOURCE_WRITE_OR_DELETE_OR_MOVE; VEHICLE_OR_CONTROLLER; HUGGING_FACE; AUTOMATIC_B1_C_D_E_F_ADVANCE |
| EXPECTED_OUTPUT | Future private bounded identity receipt at explicitly approved destination; public projection only grant/status/identity/support/missing states, no private manifest contents. No current private output generated. |
| PRIVACY_RESTRICTIONS | Exact paths/host identifiers/credentials stay in a separately supplied private grant record; public uses REDACTED_PRIVATE_REFERENCE. Do not reconstruct paths from fragments or hashes. |
| STOP_CONDITIONS | No explicit B0 human grant.; Unresolved exact host/root/manifest record.; Any identity/hash/schema conflict.; Symlink/junction/alias, traversal, unnamed reference or discovery required.; Sensitive TRAIN model receipt or any array/header/payload operation requested under B0.; Output location/capacity/read-only guarantees not explicitly authorized.; Any C/D/E/F or scientific operation requested.; Missing evidence: report insufficient, never widen scope. |
| HUMAN_INPUT_REQUIRED | Exact evidence host identity and approved execution context in a private record.; Exact canonical V4 actual and V1 reference roots; no drive-only or directory-name hints.; Four individually named manifest/receipt canonical references, trusted expected identities and known size bounds; raw file hashes when independently available.; Explicit B0-only operations, reader/protocol identity, no member dereference and bounded output/privacy destination.; Any future B1 candidate/fold/role/field and integrity/carrier permissions in a separate request; not needed to grant B0.; Fresh explicit human grant tied to this request and supplied private reference version; historical execution receipt is insufficient. |
| EXPLICIT_HUMAN_GRANT_REQUIRED | true |
| C_AUTHORIZED/D_AUTHORIZED/E_AUTHORIZED/F_AUTHORIZED | false/false/false/false |

사람이 제공해야 할 최소 정보는 exact host/execution context, V4 actual/V1 reference canonical roots, 네 metadata의 개별 canonical reference와 기대 identity/크기 한계, B0-only reader·operation·output/privacy 범위, 해당 요청에 대한 새 명시적 grant다. Public handoff에 private 경로를 붙이지 않는다. References가 해결되기 전에는 ACCESS_READY나 GRANTED라고 선언하지 않는다. B1과 C/D/E/F를 묶은 포괄 승인은 요청하지 않는다.


## 14. Tests / validation

신규 테스트는 stdlib/public schema와 synthetic authority 사례만 사용한다. 실제 private manifest·array·mount를 확인하거나 scientific source를 import해 실행하지 않는다. 기존 regression의 synthetic model execution은 실제 scientific input counter와 별도다.

Local validation: **PASS**. 아래 PASS는 실제 metadata가 확인된 검사에만 붙인다. Final exact-head CI/local-origin/clean verification은 containing commit의 publication gate이며 커밋 뒤 확인한다.

| 검사 | 실제 결과 / count | log/driver SHA256 |
| --- | --- | --- |
| access_focused | PASS /31 | b872cbe9baa5f1af98064f75fe05246d31b8967edcf9c82f2a2b3916bf854af7 |
| attribution | PASS /95 | 58b56f5b08c5ddc672af7d7cc618b6cfb01e53f4719f7f7c2a1b610bb751f321 |
| combined | PASS /2402 | 0bcba33ddaf3a1e362f46bdf34abaee039f11365734c69055df490dd98af4d47 |
| compileall | PASS /- | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| diff-check | PASS /- | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| final_public_source_workflow_scope | PASS /- | metadata |
| full | PASS /5166 | 0fe85f07f8780dfb695e697a9babd234249c3fda153bf67e7125b78c6bd841e9 |
| json | PASS /808 | metadata |
| lateral | PASS /16 | 34e68d63e45324bbc4ffb3f2d5257eba246c93f6fe464cb72da9181fd62dae21 |
| previous_feasibility | PASS /31 | 0a7bd1f73669cda241ea474a0b411a00847d12f44481220744e372226963a461 |
| previous_mixed | PASS /24 | daaa55b2de28bf3d427f9bf5dbca45d3cfc431246153d59d2c43929f6b1ce1f3 |
| previous_requirements | PASS /34 | 97b08bee652a02251f889cae66f62be37c598099d94653a9ab168909821fc208 |
| previous_transition | PASS /28 | b2f287e6d095e41edfed907d07b1509bb6d278a953df72d0c112927dc87b27f1 |
| public_report_links | PASS /38 | metadata |
| public_source_workflow_integrity_and_scope | PASS /- | metadata |
| publication | PASS /- | 37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570 |
| ruff | PASS /- | 82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18 |
| scons | PASS /- | 870f4ab033b2c85dbd11bd689b1dedd563221b66b4fdd762fa7cd9a0cf82f056 |
| validation_driver | PASS /- | 43024002f7224d216c2ae7929b6e97451049d7f9d4af9fb877a6a15365a6c892 |


## 15. Independent reviews / fail-closed 판정

| Review | 실제 상태 | report SHA256 |
| --- | --- | --- |
| authority | APPROVED | c264332d2eadd8020d6734321bb1f50753d919e378e29b1fa3bdb0d135b2c77b |
| integrity | APPROVED | 41ff7e9c40a5316b0ab82137ab28125a887bf72b7e2e6dc730bf1142958e7df1 |

독립 검토는 두 별도 reviewer가 public/static contracts와 신규 stdlib tests만 확인한다. 실제 승인 전에는 APPROVED로 기록하지 않는다. Review 내용 승인은 B grant나 과학적 효과의 승인이 아니다.

Public identity 충돌이면 V4_EVIDENCE_ACCESS_REVIEW_INPUT_CONFLICT로 중지한다. 현재 그런 충돌은 없고 host/root/manifest path가 미해결이므로 **REVIEW_COMPLETE_ACCESS_DEFERRED**다. 이는 정상적인 검토 완료 결론이며 실제 접근 완료를 의미하지 않는다. 접근이 안전하지 않다고 확정된 범위를 임의로 승인하거나 사람이 부여한 것처럼 receipt를 mint하지 않았다.


## 16. Authority / counters / stop

| Actual private/scientific operation | Counter |
| --- | --- |
| calibration_fit_calls | 0 |
| candidate_search_calls | 0 |
| holdout_discovery | 0 |
| holdout_openings | 0 |
| model_refit_calls | 0 |
| normalizer_refit_calls | 0 |
| prediction_replay_calls | 0 |
| private_aggregate_generation_calls | 0 |
| private_array_openings | 0 |
| private_directory_discovery_calls | 0 |
| private_manifest_openings | 0 |
| qlog_openings | 0 |
| raw_log_openings | 0 |
| rollout_regeneration_calls | 0 |
| selection_calls | 0 |
| source_write_count | 0 |
| stage2_refit_calls | 0 |
| threshold_reselection_calls | 0 |
| vehicle_activation_calls | 0 |

19개 counter는 declared public/helper read paths, stdlib-only schema, 실행 command scope, before/after 공개76/source21/workflow SHA와 정확한11개 신규파일 diff로 검증한다. Source write는 원 sealed scientific source/evidence에 대한 쓰기이며 허용된 신규 문서·테스트 작성과 다르다. Helper·로그도 E 밖에 두며 현재 private data access·new private aggregate는 없다.

HURDLE_STAGE1_V4_NO_ADMISSIBLE_CANDIDATE / MODEL_SELECTION_FAILED_CLOSED / selected_candidate=null. HOLDOUT=CLOSED,opening_count=0,holdout_discovery=0,FUTURE_UNTOUCHED_HOLDOUT_REQUIRED,NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT,FINAL_POOLED_REFIT_NOT_AUTHORIZED,COMPOSITION_NOT_AUTHORIZED. Vehicle=NOT_READY /REAL_VEHICLE_UNVERIFIED /VEHICLE_ACTIVATION_BLOCKED /authority=NONE. Hugging Face=NOT_REQUIRED /NOT_USED.

delta_tick=SOURCE_GRID_TICK_INCREMENT_CHANGE, logged_command=POST_CARCONTROLLER_NORMALIZED_COMMAND, steeringRateDeg=SOURCE_NATIVE_RATE_CODE_ONLY /RATE_SOURCE_CONTRACT_PARTIAL. 물리 EPS movement/applied torque/signed physical steering rate 또는 실차 closed-loop 성능으로 입증되지 않았다.

실제 개선 분석에는 저장 score, frozen truth label, prior context와 saved DEV gate의 정확한 identity·정렬이 필요하다. 현재 준비된 것은 공개 catalog, 과거 identity/receipt, 최소 field 초안과 승인 경계다. 부족한 exact private reference와 human B0 grant를 먼저 받아야 하며 B1·집계C·정책D·실험E는 다시 분리한다. 최종 GitHub exact-head CI SUCCESS와 clean 상태 확인 뒤 중지하고 private 접근/processing/V5/refit/threshold/calibration/inference/rollout/selection/HOLDOUT/controller/vehicle로 자동 진행하지 않는다.
