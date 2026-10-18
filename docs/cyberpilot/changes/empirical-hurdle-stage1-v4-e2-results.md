# CyberPilot V4 E2 실제 실행 결과

최종 과학 상태는 `E2_D0_TRAIN_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED`다.
D2의 성능이 나빠서 탈락한 결과는 아니다. 실제 TRAIN 검증에서 기존 D0의 선택행 Stage2 계산과 전체행 Stage2 캐시의 같은 행 출력이 byte 단위로 일치하지 않아, 정해 둔 중지 조건이 작동했다. D2 decision과 DEV 예측은 생성하지 않았다.

사전 실행 코드 HEAD는 `d9d6843a62d3a148aadc59eea0213ad501448115`이며 [exact-head CI 39123893987](https://github.com/rownlvh8875-coder/CyberPilot/actions/runs/39123893987)가 completed/success였다. 결과 공개 commit의 최종 CI는 commit 이후 별도로 확인한다.

동결 protocol은 `V4_E2_D0_D1_D2_PROTOCOL_V1`, raw SHA256은 `177925af0d9a70fecaeb2f8d848dbdee9c620f92047a9d8320e0ed6e1e7ef7db`다. [Protocol](empirical-hurdle-stage1-v4-e2-execution-protocol.json), [실제 결과](empirical-hurdle-stage1-v4-e2-results.json), [검증 기록·22개 영역](empirical-hurdle-stage1-v4-e2-validation.json)에 연결했다.

| 단계 | 실제 결과 |
|---|---|
| 기존 B0/B1/C/E1 lineage | exact control binding·sealed lineage 검증, B1 역사적224/224 보존 |
| Host·volume·root/member | 기존 handoff의 정확한 기록 사용, 탐색·대체 root 없음 |
| 첫 TRAIN job | HRI_D00_L01 / FOLD_A: fixed512 chunk 비교 및 원래 whole-job selected-row 비교 PASS |
| 다음 TRAIN job | HRI_D00_L01 / FOLD_B: fixed512 chunk의 selected-row와 all-row cached delta byte 비교 FAIL |
| TRAIN 시도 / qualification 완료 | 2 / 1 jobs, 이후30 jobs 미진행 |
| D0 TRAIN reconstruction | 2 jobs에 새로 계산, 원래 private threshold 비열람 |
| D1 TRAIN 재현 | 첫 job의 두 context만 계산, 기존 E1 numeric result는 아직 열지 않음 |
| D2 decision / durable TRAIN seal | 0/64, 생성하지 않음 |
| DEV / one-step / recursive | 모두 미실행, DEV 접근 장벽 미해제 |
| Fresh repeats | 첫 반복 부분 실행 후 중지, 두 번째 반복 없음 |
| Verify-only | 완료 결과 resume는 해당 없음; 중단 receipt의 seal·binding·read counter만 별도 확인, source/inference/recompute0 |

TRAIN current/target·causal features·eligibility/order·saved score/label/prior·Stage2 model/normalizer·potential outcomes·private binding·D0 reference의 여덟 범주를 구분했다. 첫 job은 전체 정렬과 수치 qualification을 마쳤고 두 번째 job은 부분 실행이다. 열었던 파일의 manifest hash/schema 검사는 통과했다. 이는 나머지30 jobs의 새로운 검증 완료를 뜻하지 않는다.

원본 행을 제거하거나 재배열하지 않았다. STATIC 행도 잠재 MOVE 계산에 포함했다. 실패 후 배열을 다시 열어 차이 크기·행 위치를 분석하지 않았다. 따라서 byte 차이가 어느 물리적 원인이나 예측 오차를 뜻하는지는 이번 결과로 확정하지 않는다. 현재 부족한 것은 관측된 파일 경로가 아니라 **동결한 두 Stage2 계산 경로의 수치 동등성 증명**이다.

D0/D1/D2의 one-step RMSE/MAE/P95, exact-hit 손실/이득/net, TRUE MOVE, 네 전이 오류, harmful movement, H25/50/100/200 OVERALL·PATH_MOVED 비교는 새로 평가하지 않았다. 두 Fold의 D2 acceptance 평가 jobs는0이다. 기존32 clauses, support201, epsilon0, same-anchor HOLD_LAST, both-fold 조건은 불변이다. 미평가를32개 성능 실패 또는 통과로 표기하지 않는다. 22개 영역의 실제 실행/미식별/권한 차단 상태는 검증 JSON에 개별 기록했다.

D0 공식 실패와 D1 E 실패는 그대로다. `selected_candidate=null`, `selected_policy=null`이며 D2는 성능 미평가 상태다. 기존 TRAIN rowwise gate는 `NOT_SAVED`; 이번 D0 TRAIN gate 계산은 별도 E2 재구성이며 과거 저장 사실을 바꾸지 않는다. 원래 whole-replica equality는 `REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED`를 유지한다.

새 focused51, 관련 focused336, Full AutoTune/controls5502, lateral synthetic16이 실제로 통과했다. Ruff·compileall·SCons·공개 JSON817·사전 공개검사0 findings·diff check도 통과했다. 두 독립 reviewer가 exact protocol/source bytes를 APPROVED했다. 이는 실제 입력 또는 D2 성능의 승인과 다르다. 결과 공개 전 검증과 최종 CI는 실제 실행 후 별도로 기록한다.

원본 읽기 이벤트와 bytes, 모델·Stage2 호출 횟수 및 중단 receipt는 Git 외부의 제한된 비공개 출력에 봉인했다. 공개 결과는 상태와 공개된 job identity, 완료 job 수만 담고, 원본 paths/hashes·decision·계수·개별 행·gate 의존 telemetry·기존 억제 전이 셀은 공개하지 않는다. 원본 source writes와 금지 연산은0이며 런타임 금지 시도도0이었다. Python audit와 exact openat2 reader를 사용했으며 OS sandbox를 구현했다고 주장하지 않는다.

추가 E2 실행 전에는 이 Stage2 수치 경로의 정적 검토와, 필요하다면 정확한 범위의 추가 비공개 수치 진단/계약 개정/재실행 승인이 필요하다. 이번 결과를 근거로 batching·tolerance·목적함수·guard를 바꾸거나 재시도하지 않았다. D3도 시작하지 않았다.

HOLDOUT은 CLOSED, future untouched evidence 필요, pooled refit·composition 미승인이다. 차량은 NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED, authority NONE이다. Hugging Face는 NOT_REQUIRED / NOT_USED다. Source-grid tick은 물리 EPS 움직임의 직접 검증이 아니며 logged command는 post-CarController normalized command다. SteeringRateDeg는 SOURCE_NATIVE_RATE_CODE_ONLY / RATE_SOURCE_CONTRACT_PARTIAL이다.

- Q1 다음 tick이 더 정확해졌는가? D2 예측을 생성하지 않아 알 수 없다.
- Q2 정지할 때 불필요한 projected movement가 줄었는가? 미평가다.
- Q3 필요한 움직임과 TRUE MOVE를 보호했는가? D2 TRAIN guard 및 DEV 보호 모두 미평가다.
- Q4 H25~H200에서 개선이 유지됐는가? rollout 미실행이다.
- Q5 양 Fold의32개 기준을 모두 통과했는가? D2 gate를 평가하지 않았다.
- Q6 차량 적용이 가능한가? 아니다. 권한과 검증 상태는 계속 차단이다.

과학 실행은 동결 수치 계약 실패 시점에 중지했다. 허용된 공개 결과 검증·commit/push·최종 exact-head CI와 clean 확인만 마무리한 후 STOP한다.
