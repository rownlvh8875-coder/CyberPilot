# Cyber Long Step 5 — 구현 및 검증 기록

작성일: 2026-09-29. 상태: **로컬 초기 구현 / native 핵심 parity 및 기본 PC runner 통과 / Phase B·차량 qualification 미완료 / 실차 적용 불가**.
승인 범위는 [Step 5 실행 계획](../../superpowers/plans/2026-09-29-cyber-long-step5.md)의
default-disabled/observation-only Phase A 및 비작동 Phase C다.
사용자의 후속 “진행해”가 직접 실행/현재 checkout의 feature/cyber-long 사용 승인을 제공했다.
이전 설계/계획 문서의 당시 승인 대기 표기는 역사적 기록으로 보존했다.
아래 1–7절은 첫 portable 검증 당시 기록이다. 사용자의 후속 환경 준비 승인에 따른
새 Ubuntu24.04 결과는 8절에 별도로 기록하며, 이전 실패/미실행 증거를 덮어쓰지 않는다.
승인된 명령별 CA bundle과 전체 runner 재실행 결과는 9절이 현재 기록이다.

## 1. 실제 구현 범위

| Phase | 구현 | 실제 검증/한계 |
| --- | --- | --- |
| A | stock 후보 관찰 연결; upstream follow/stop/start/accel/decel 유지 목적 | observer 13 + isolated boundary 5 methods 통과. 실제 planner/MPC/LongControl parity 미검증 |
| B | 구현/활성화하지 않음 | 효과 확인된 cut-in 근거, license, 차량/입력/수치 bounds gate가 미충족 |
| C | 중앙 read-only metadata와 offline proposal rejection | admission 12 methods 통과; 모든 제안 accepted=False. 튜닝 engine/apply/online writeback 없음 |

Carrot 코드를 복사하거나 longitudinal algorithm을 이식하지 않았다.
Carrot 기반 독립 진단/파라미터 소유권 분리 **개념**만 설계 reference로 사용했다.
출처: geniuth2/openpilot_carrot, 실제 분석 branch carrot2-v6,
c57d0ff11f766b7fd70e9a9eaec1247b623ffbea, Step 4의 CarrotPlanner/legacy planner/LongControl 호출 분석.
이를 “Carrot 성능 개선이 적용됐다”라고 해석하면 안 된다.

## 2. Git, source 및 환경 identity

- branch: feature/cyber-long. HEAD/baseline: c8fb906815530460ed156f14e09e1f312bb0f851.
- git ls-remote --symref openpilot HEAD로 실제 기본 branch master와 같은 SHA 확인.
- git fetch --no-tags --no-recurse-submodules openpilot master exit 0; FETCH_HEAD/openpilot master 기준 유지.
- origin/openpilot/sunnypilot/carrotpilot remote URL 변경 없음. 새 영구 branch 없음.
- commit/push/merge/deploy, 장치/차량/Params/CAN writes 없음. index에 코드 stage도 하지 않았다.
- Ubuntu WSL2: **Ubuntu26.04 LTS**, uv CPython **3.12.14**.
  Python 범위는 만족하지만 tools/README.md의 Ubuntu24.04 native 지원 환경과 다르다.
- Windows Ruff **0.16.5**는 보조 lint 환경. 런타임 검증은 Windows Python3.14로 대체하지 않았다.
- root MIT LICENSE 유지. Carrot 파일별 license 허가 gate는 여전히 열려 있다.
- model/firmware/input driving-log identity: **미확보**. synthetic fixture 식별만 가능.
- LFS/native assets 준비/빌드 없음; gitlinks 초기화/변경 없음.

| Gitlink | Pin (전후 동일, 모두 미초기화) |
| --- | --- |
| msgq_repo | 0e266c1dbcf7328beee3e57b4a8688555387c877 |
| opendbc_repo | 4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76 |
| panda | 92eb565169fd553f4dfaf508c1a3f8dbc14fbfbf |
| rednose_repo | 8671c17c3a4cdc4be5df07a068039e2da5b94eaa |
| teleoprtc_repo | 1aa8fc433bef1519a95c0700c96258c3be6dfb34 |
| tinygrad_repo | 9d0446a4ba8a532c8b674fb6ad795af015cd9dcf |

## 3. 수정/신규 파일과 인터페이스

기존 tracked product 파일 수정은 openpilot/selfdrive/controls/lib/longitudinal_planner.py **한 개**다.
35 insertions / 1 deletion (constructor signature 변경 포함).
키워드 전용 cyber_long_config=None을 추가해 기존 positional 호출을 보존한다.
default disabled는 update에서 추가 SM input 읽기/context allocation을 하지 않는다.
OBSERVE_ONLY도 actuator candidate를 생성하거나 return하지 않는다.

신규:

- openpilot/selfdrive/controls/lib/cyber_long/types.py: frozen config/context/binding/diagnostic/metadata/proposal/assessment.
- policy.py: 관찰/입력 검증과 세션 identity. 호출자는 sm/CP/Params를 넘기지 않는다.
- params.py: immutable registry, user/safety/vehicle/controller namespace 분리, fail-closed admission.
- openpilot/selfdrive/controls/tests/test_cyber_long.py: 실제 pure observer 계약 테스트.
- test_cyber_long_boundary.py: AST로 실제 observer method를 추출해 실행. native imports를 피할 뿐 native 행동을 대체하지 않는다.
- test_cyber_long_params.py: 실제 admission 함수 및 owned registry 검사.
- test_cyber_long_integration.py: 실제 native dependencies 사용, Git object에서 frozen planner와 LongControl 로드.
- docs/cyberpilot/changes/cyber-long-phase-a.md 및 cyber-long-autotune-admission.md: 기능별 기록.
- 이 검증 문서. 로컬 outputs/STEP5_REPORT.md는 Git 제외 사용자 handoff.

관련 upstream 경로: stock model/MPC/cruise candidates → 원래 min 및 전체 shouldStop OR → clipping/feedback
→ 기존 publish → 기존 LongControl/controlsd/card/CI/CAN/panda. observer 결과는 이 경로에 사용하지 않는다.
publish의 MPC trajectories를 최종 aTarget으로 재정의하지 않는다.

Session timestamp는 monotonic ns. model은 strict increase, carState/radar는 nondecreasing;
upstream all_checks가 유효할 때 같은 radar/carState sample 재사용은 허용한다.
invalid/driver/reset/binding/clock/fault는 last_observation을 버린다.
반복 프레임이 재승인되지 않도록 input high-watermark는 rejection/fault 뒤에도 유지하며,
관찰 예외를 일으킨 frame identity가 알려져 있으면 소비한다. 명시적 new-session reset만 모든 identity를 지운다.
누락 firmware/model은 None이며 qualification을 주장하지 않는다. provenance_complete는 필드 형식 완전성일 뿐 증거 검증이 아니다.
Hot path에 network/file/Params IO 없음. 실제 비용/주기 지연은 native 환경에서 별도 측정 필요.

delay(s)/현재 acceleration-error integral gain(1/s)은 research metadata일 뿐 적용 값이 아니다.
vehicle defaults와 bounds/rate/confidence는 None: 미검토/사용 금지다.
confidence [0,1]은 dimensionless 입력 형식이고 채택 기준이 아니다.
안전 모델/flags/CAN/DM/takeover/engagement/headway는 이 API로 변경할 수 없다.

## 4. 실행한 검증 — PASS와 BLOCKED를 분리

아래 검증은 project Python 3.12 interpreter를 사용하고 repository root에서 PYTHONPATH=.를 지정했다. -j 1은 deterministic 단일 worker 선택이며 acceptance 완화가 아니다.

| Check / 실제 명령 | Exit / counts | 상태와 한계 |
| --- | --- | --- |
| python tools/test_runner.py openpilot/selfdrive/controls/tests/test_cyber_long.py openpilot/selfdrive/controls/tests/test_cyber_long_boundary.py openpilot/selfdrive/controls/tests/test_cyber_long_params.py -j 1 -v | 0; 30 passed | PASS, synthetic/portable 한정. 13+5+12 test methods; table/subtest 반복은 별도 test 수로 부풀리지 않음 |
| python tools/test_runner.py openpilot/selfdrive/controls/tests/test_cyber_long_integration.py -j 1 | 1; 0 tests, 1 collection error | BLOCKED: numpy 없음. native parity PASS 아님 |
| python tools/test_runner.py openpilot/selfdrive/controls/tests -j 1 | 1; 30 passed, 7 collection errors | 전체 controls suite PASS 아님; numpy/capnp 누락 |
| python tools/test_runner.py openpilot/selfdrive/test/longitudinal_maneuvers/test_longitudinal.py -j 1 | 1; 0 tests, 1 collection error | BLOCKED: capnp 없음 |
| python tools/test_runner.py -j 1 | 1; 30 passed, 66 collection errors | 전체 suite 실패/미완료. Crypto/capnp/jeepney/numpy/opendbc/requests/tqdm 누락 |
| scons -u | 프로세스 시작 불가; numeric exit 없음 | NOT RUN/BLOCKED: scons executable 없음 |
| python openpilot/selfdrive/test/process_replay/test_processes.py --whitelist-procs plannerd controlsd radard | 1; process replay 0건 | BLOCKED: tqdm import 실패. model/logs/native 검증 단계까지 도달하지 못함 |
| Windows ruff check (위 8개 Python 파일) | 0; All checks passed | PASS, repository config 사용. lint ignore/threshold 변경 없음 |
| git diff --check; 8개 new/modified Python의 UTF8/LF/trailing whitespace/3.12 compile | 0 | PASS, untracked 파일도 별도 byte 검사 |
| 원본 Git AST와 비교 | 검사 정상 종료 | 추가 observer if만 제거하면 stock update AST 동일; publish AST 동일. native parity 대체 아님 |
| 변경 범위/기존 문서 hash/gitlinks | 검사 정상 종료 | 모든 다른 tracked content unchanged; prior 9개 핵심 docs/plan hash 동일, gitlinks 동일 |
| Closed-loop simulation / live-device shadow | 실행 안 함 | NOT RUN: replay 선행 evidence/지원 환경/approved identities 부족. device 작업 승인 없음 |

도구 runner 최초 실행은 PYTHONPATH 누락으로 openpilot package import 오류였다.
PYTHONPATH=.로 수정 후 기능 미구현 module/API 실패를 확인했다. 환경 오류를 기능 RED라고 기록하지 않았다.
TDD: observer 신규 module missing → 13 GREEN; seam missing → 4 실패 → GREEN;
admission ParameterProposal missing → 11 GREEN.
리뷰 회귀 재현은 1 failure/3 errors를 확인한 뒤 수정했으며 최종 30 GREEN이다.

로컬 excluded evidence: work/step5/evidence.json 및 portable/native/controls/longitudinal_maneuvers/full_runner/build/replay/diff_check.log.
manifest는 각 command/exit/count/log SHA256와 input test-file SHA256를 보관한다. 생성기 work/step5/verify.py는 local-only다.
logs/private data를 repository에 추가하지 않았다. outputs 및 work/step5는 .git/info/exclude로만 제외했다.

### Collection 오류 목록 (누락/무시하지 않음)

controls 7개: test_cyber_long_integration, test_following_distance, test_latcontrol,
test_latcontrol_torque_buffer, test_leads, test_longcontrol, test_torqued_lat_accel_offset.
longitudinal_maneuvers 1개: test_longitudinal.
full runner 66개는 실제 collection 순서의 loader labels다. 중복 package label도 별도 오류이며
전체 traceback/정확한 source path는 local full_runner.log에 있다. 테스트 삭제/skip으로 해결하지 않았다.

```text
01 cereal                     02 cereal                      03 cereal
04 hardware                   05 hardware                    06 test_file_helpers
07 test_markdown              08 test_params                 09 test_qrcode
10 test_simple_kalman         11 test_coordinates            12 test_orientation
13 test_car_interfaces        14 test_cruise_speed           15 test_docs
16 test_cyber_long_integration 17 test_following_distance     18 test_latcontrol
19 test_latcontrol_torque_buffer 20 test_leads                21 test_longcontrol
22 test_torqued_lat_accel_offset 23 test_calibrationd         24 test_lagd
25 test_locationd_scenarios   26 test_paramsd                27 test_torqued
28 test_monitoring            29 pandad                      30 pandad
31 pandad                     32 test_alertmanager           33 test_alerts
34 test_state_machine         35 test_longitudinal           36 process_replay
37 test_onroad                38 test_power_draw             39 test_widget_leaks
40 test_raylib_ui             41 test_soundd                 42 test_translations
43 test_athenad               44 test_athenad_ping            45 test_registration
46 test_camerad               47 test_fan_controller         48 test_power_monitoring
49 test_deleter               50 test_encoder                51 test_loggerd
52 test_uploader              53 test_manager                54 test_sensord
55 test_logmessaged           56 test_pigeond                57 test_handle_state_change
58 test_stream_session        59 test_native                 60 test_cabana_ui
61 test_jotpluggler            62 test_caching                63 test_comma_car_segments
64 test_logreader             65 test_route_library          66 test_plotjuggler
```

## 5. Independent review와 수정

실행 스킬의 요구로 fresh read-only reviewer 1회 수행. initial verdict: not ready to merge,
Critical 없음 / Important 2 / Minor 2. 자동 re-review나 commit은 하지 않았다.

1. 예외 후 policy 교체가 watermark를 지워 같은 frame을 다시 관찰한 오류:
   accepted → exception → repeated/reversed rejection → newer accepted 회귀 테스트 RED 확인.
   policy.invalidate(reason, context)로 진단만 지우고 known frame watermark를 유지하도록 수정, GREEN.
2. native nonwinning-stop fixture의 vEgo=0 때문에 winner stop도 True였던 오류:
   vEgo=10 m/s로 synthetic fixture를 수정하고 실제 should_stop winner=False를 명시 검사.
   native execution은 BLOCKED이므로 이 회귀 수정의 runtime PASS를 주장하지 않는다.
3. oversized integer / unhashable name admission exception:
   RED의 OverflowError/TypeError 재현 후 invalid_value/invalid_confidence/unknown_parameter rejection으로 수정, GREEN.
4. LongControl baseline도 실제 pinned Git object에서 로드하도록 수정.
   native 환경에서 함께 실행해야 하며 static 수정 자체는 parity PASS가 아니다.

Reviewer가 판단하지 않은 항목과 실행자 판단:
native/replay/closed-loop/empirical/shadow/road readiness는 미검증으로 유지;
B/accepted tuning은 승인 범위 밖이라 미구현 유지;
CAN/safety 구현 전체 runtime은 미초기화 unchanged pins라 감사 완료를 주장하지 않음;
hostile Python arbitrary monkeypatch bypass는 보안 isolation 목표 밖;
최종 문서 당시 작성 중 지적은 이 handoff에 실제 결과를 채워 해소했다.
수정 뒤 source-level 재리뷰 완료라고 주장하지 않는다. 실 통합 promotion은 여전히 보류다.

## 6. Candidate identity와 보존 검증

Uncommitted tracked diff SHA256: a9780ee4e8d1eeb754b5d17f4a19de071ff9d8f7042c0d4340dc11060283a5fa.
이 patch hash만으로 untracked package/tests가 포함되지 않으므로 다음 file hashes와 묶어 식별한다.

| File (repository root relative) | SHA256 |
| --- | --- |
| openpilot/selfdrive/controls/lib/longitudinal_planner.py | 9e155c5a38d4c383a8f49827cbbc52e89dd87abf6ca9b911e842e1862ff1c959 |
| openpilot/selfdrive/controls/lib/cyber_long/types.py | a77cc933665cee2f2ad1f7a1ff25e71bf2b429e46c3d7860d6d5501a20bcc7cb |
| openpilot/selfdrive/controls/lib/cyber_long/policy.py | 439488d03407917b4d7831589250273ca94d3a77c08409a7cd8fc03ed1fe79a0 |
| openpilot/selfdrive/controls/lib/cyber_long/params.py | fd5ab8e683b03e4405f9d5628274c1ea661fd4ccbb74d51206cbf1e80a63b09c |
| openpilot/selfdrive/controls/tests/test_cyber_long.py | fef23eae0462eae0619f085a431bbe8bf3123b7e0e8c8aeacd6fc516cd38a4d2 |
| openpilot/selfdrive/controls/tests/test_cyber_long_boundary.py | f2be0d14303bd695f15b761f5aac1cfc11215d186a15f9e72ba4985d83c00ac6 |
| openpilot/selfdrive/controls/tests/test_cyber_long_params.py | b697a55b09b367a4dde493e4868bf05cddcacf12c44843b2263e740c26ed6061 |
| openpilot/selfdrive/controls/tests/test_cyber_long_integration.py | c03b209c3d285a98254d3f6820ebcee0fefac11ece31283cdd8c567ef616f72d |

기존 AGENTS/Step3 비교·sources·verification/Step4 설계·parameter catalog·inventory·verification/approved plan의
9개 주요 파일을 시작 hash와 비교해 동일 확인. 모든 이전 문서 파일은 수정 대상에 포함하지 않았다.
long_mpc.py, longcontrol.py, controlsd.py, card.py, cruise.py, modeld, cereal, safety와 build/test 설정도 수정하지 않았다.

환경 diagnostic 중 Linux Git로 Windows checkout을 scan했을 때 LFS/emulated symlink stat-cache 차이로
asset modified 표기가 나타났다. comma-logo.png working bytes와 원본 Git symlink payload는 67 bytes로 정확히 동일.
Windows native Git의 core.checkStat=minimal read-only 검사로 product diff가 planner 한 개임을 재확인했다.
asset 교체, git reset/checkout, LFS 업로드, safety/test 완화로 처리하지 않았다.
초기 hash-audit 실패 하나는 catalog digest 옮겨 적기 오타였고 시작 Get-FileHash 증거와 대조해 수정했다.

## 7. 남은 gate / 다음 권고

1. 별도 선택/승인으로 Ubuntu24.04 native 환경, 현재 exact gitlinks/dependencies/LFS를 준비한다.
   이번 PC 코드 작업으로 OS/distro 설치·device flashing을 자동 승인하지 않았다.
2. 위 native parity + 기존 controls/longitudinal maneuvers + build/full runner를 재실행한다.
   새 API가 stock 출력/state를 정확히 보존하는지 먼저 증명해야 한다.
3. approved 차량/firmware/model/log/holdout/metric thresholds를 고정해 replay → closed-loop simulation → shadow 순으로 진행한다.
4. comfort 가설은 단일 기능으로 근거/범위/수치 gates를 새로 심사한다. 현재 cut-in 개선 효과는 확인되지 않았다.

**현재 결론:** 검토 가능한 로컬 구현과 제한된 portable evidence는 준비됐다.
Phase A 전체 검증, Phase B 구현, 실차/안전/성능 승인 또는 전체 Step 5 완료는 아니다.

## 8. 승인된 native 환경 준비 및 후속 검증

사용자의 “그래 그렇게 진행해”는 제안한 별도 Ubuntu24.04 환경 준비와 PC 검증을 승인했다.
기존 Ubuntu26.04 및 기본 distro는 유지했다. device/CAN/실차/배포/commit/push 권한 확장은 없다.

- 별도 WSL distro: Ubuntu-24.04, /etc/os-release의 Ubuntu24.04.5 LTS 확인.
- native 검증 replica: /opt/cyberpilot-step5/repo (ext4). 실제 Git clone, detached c8fb906 baseline.
  Git object alternates는 원본을 읽기만 하며, 별도 .git/index/working tree를 사용한다.
- managed source reference worktree: cyber-long-native, 동일 baseline detached HEAD.
  이 checkout은 source/patch reference이며 Windows gitdir를 Linux Git에 억지로 사용하지 않았다.
- 원본/managed reference/native replica의 후보 Python 8개 SHA256가 6절과 모두 동일하다.
  이번 환경 준비에서 제품 코드나 테스트를 수정하지 않았다.
- native replica에서만 2절의 exact submodule 6개를 초기화했다. gitlink SHA 변경 없음.
  초기화 후 tinygrad_repo/AGENTS.md를 읽었으며 submodule source 수정 없음.
- Python3.12.14, uv0.12.20, GCC13.3.0, SCons4.11.1, NumPy2.5.3, pycapnp2.1.0.
  uv sync --frozen --all-extras --python 3.12.14 종료 0, 65 packages installed.
  uv.lock/pyproject/SConstruct/테스트 acceptance/ignore는 변경하지 않았다.
- 기준 LFS 자산 252개, 총 895134701 bytes: 기존 원본 LFS cache에서 command-scoped read-only
  storage로 native working tree에 checkout했다. 외부 upload/fetch 및 원본 cache 쓰기 없음.
  각 working file의 SHA256와 size를 inventory OID/size와 비교, 252개 모두 일치.
  inventory SHA256: 552a0bb97835a1a97c053d3b1f04d442556314ddde493b66fdcd3d05ba8112d2.
- upstream setup의 udev/device permission/shell-profile/pre-push 변경 부분은 실행하지 않았다.
  apt 다운로드 일부 재시도 후 설치 완료, dpkg --audit 출력 없음.

명령은 native root에서 .venv 활성화, PYTHONPATH=$PWD, -j 1 단일 worker로 실행했다.
전체 build에는 --minimal/경고 완화/파일 삭제를 사용하지 않았다.

| Check | 실제 결과 | 의미 |
| --- | --- | --- |
| scons -u -j 4 | exit0, done building targets | 전체 기본 native build 통과 |
| portable 계약 3개 파일 | exit0, 30 passed in 0.12s | observer13/boundary5/admission12, synthetic 계약 |
| test_cyber_long_integration.py | exit0, 5 passed in 1.49s | 실제 native MPC 및 frozen planner/LongControl scalar/state/trajectory parity; 1 method는 명시적 isolated arbitration fixture |
| controls/tests | exit0, 63 passed in 39.33s | 위 Cyber 테스트 포함, affected upstream suite 통과 |
| longitudinal_maneuvers/test_longitudinal.py | exit0, 4 passed in 39.48s | upstream synthetic planner/plant 회귀, qualification simulation 아님 |
| native Ruff0.16.7, 후보 8개 Python | exit0, All checks passed | 고정 upstream lint 설정 유지 |
| 전체 tools/test_runner.py -j 1 | exit2, 1029 collected, interrupted | TLS 입력 의존성 때문에 중단. 출력된 partial records: 511 passed / 1 failed / 1 error / 1 skipped. 전체 결과 아님 |
| 원래 runner 앞 2 batches 진단 재실행 | exit1, 511 passed / 1 failed / 1 error / 1 skipped, 79.66s | 명시적 partial diagnostic만 실행; coverage/ignore/threshold 변경 없음 |
| messaging/test_services.py (Clang 준비 후) | exit0, 71 passed in 1.11s | 누락 clang++ 문제 해소. 전체 suite 재통과 의미 아님 |
| process replay --help | exit0, replay 0 segments | native imports/CLI 확인만 실행 |

63 controls tests에는 위 30+5 Cyber tests가 포함된다. 중복 실행 횟수를 독립 coverage로 합산하지 않는다.
Maneuver plant는 기본 disabled planner output을 단순 운동 모델로 적분하며 실제 차량/actuator 모델을
검증하지 않는다. 이것을 Carrot comfort/cut-in 개선 또는 replay 이후의 Cyber closed-loop 승인으로 간주하지 않는다.
관찰 fault/stop-OR fixture와 frozen LongControl oracle도 이제 실제 native 실행에서 통과했지만
source-level 재리뷰 완료, 성능 개선, road readiness를 의미하지 않는다.

로컬 raw logs: /opt/cyberpilot-step5/logs, 준비 logs/scripts: work/step5-native (Git 제외).
원본 work/step5/evidence.json과 이전 로그는 보존한다. 새로운 manifest와 사용자 결과 보고는 별도 파일이다.
Phase B/accepted tuning/qualified replay/closed-loop/shadow/실차 승인은 여전히 없다.

### 전체 runner 중단 원인과 남은 권한

1. 초기 FAILED: TestServices.test_generated_header, /bin/sh: clang++ not found.
   기존 테스트가 명시적으로 clang++를 호출한다. 별도 distro에 Ubuntu clang18.1.3을 준비해
   test_services.py 전체71 methods를 다시 실행, exit0으로 확인했다. 소스/테스트 수정 없음.
2. 초기 ERROR: TestAgnosUpdater.test_manifest, requests.head의 SSLCertVerificationError
   (commadist.azureedge.net). manifest URL read만 실행하며 updater/device write는 실행하지 않았다.
3. 이후 TestLocationdScenarios.setup_class가 TEST_ROUTE 로그를 준비하는 동안 원격 재시도로 지연됐다.
   py-spy0.4.2를 isolated bootstrap에 준비하고 읽기 전용 stack dump로 CommaApi/URLFile
   재시도 경로를 확인했다. curl에서도 certificate chain 검증 오류60을 재현했다.
   중단은 해당 native runner PID에 SIGINT를 보내 실제 exit2를 확인한 것이며, 실패를 PASS로 바꾸지 않았다.
4. Windows 기본 TLS 검증은 해당 public rlog.bz2 URL에서 HTTP200, 새 WSL은 기업 프록시 CA
   chain 검증 실패다. Windows SslStream callback은 SslPolicyErrors.None만 허용해 chain을 확인했다.
   공개 CA subject/thumbprint는 로컬 제외 보고에만 보관하고 Git 문서에 기업 식별정보를 넣지 않는다.
5. 인증서 검증 비활성화, curl -k, verify=False, CA 자동 추가, credentials/개인키 export는 하지 않았다.
   Windows가 이미 신뢰하는 특정 CA의 공개 인증서를 검증 명령 전용 bundle로 사용하려면 별도 승인이 필요하다.
   원본/새 distro 전체 trust store 변경을 자동 승인으로 추정하지 않는다.

TLS 해결 이후에도 원격 입력/접근/기준 문제나 다른 suite failure가 더 나올 수 있다.
이번 partial 결과로 미실행 1,029개 전체를 통과했다고 추론하거나 A/B road promotion을 하지 않는다.
순서상 qualified replay를 완료하기 전 차량별 closed-loop/shadow qualification을 시작하지 않는다.
전체 native runner와 diagnostic은 종료됐으며 테스트를 남겨 둔 채 PASS로 handoff하지 않았다.
새 로컬 manifest: work/step5-native/evidence.json. 후보8개 hash 및 원본/reference/native 일치,
이전9개 docs hash 보존, native logs12개 hash, commands/exits/counts, 환경/qualifications를 기록했다.
원본9개 docs와 이전 portable manifest를 재검사해 동일 확인했다. 현재 stage/index는 비어 있고
원본 tracked diff는 여전히 planner35 insertions/1 deletion 하나뿐이다.

## 9. 승인된 command-scoped TLS 해결 및 전체 PC runner 재검증

사용자의 후속 “그래 진행해”는 Windows에서 이미 신뢰하는 특정 기업 CA의 공개 인증서만
검증 명령 전용 bundle에 사용하는 제안을 승인했다. 개인키, 영구 trust-store 변경,
TLS 검증 우회, 전역 환경 설정, 차량/device/배포/commit/push는 승인 범위에 포함하지 않는다.
이번 절은 8절의 TLS blocker를 해소한 새 snapshot이며 과거 실패를 지우지 않는다.

### 범위와 보안 확인

- Windows 기본 chain 검증이 성공한 exact CA의 identity/유효기간/BasicConstraints CA를 확인했다.
  X509ContentType.Cert로 공개 DER만 읽었고 private key export는 없다.
- Ubuntu 시스템 CA bundle의 읽기 전용 복사본에 해당 공개 CA만 추가했다.
  로컬 work/step5-native/tls 파일은 Git 제외이며 기업 식별정보/인증서를 Git 문서에 추가하지 않는다.
- SSL_CERT_FILE/REQUESTS_CA_BUNDLE/CURL_CA_BUNDLE은 검증 wrapper process와 child에만 적용했다.
  shell profile, Windows/WSL trust store, 원본 bundle과 전역 환경은 수정하지 않았다.
- 기존 기본 curl은 동일 public fixture URL에서 TLS exit60으로 실패(negative control),
  별도 bundle을 지정한 curl 및 requests.head는 HTTP200, exit0이었다.
  Python 기본 SSL context는 CERT_REQUIRED 및 check_hostname=True를 유지했다.
- 검증 bundle SHA256: e75b68f976dea70dc68393c01acab474cf695bb29cb752a70ed90fb0cbb4d19b.
  Ubuntu 시스템 bundle은 전후 SHA256
  ecd9dc38bc3efb7dbd6431f57e29d2f8d6a0f0d211e1464b3fef2cbfe266fcd2로 동일하다.

### 새 실행 결과 (Ubuntu24.04.5 / Python3.12.14 / 동일 candidate)

| Check / command | 실제 결과 | 범위 |
| --- | --- | --- |
| 기본 python tools/test_runner.py -j 1 | exit0; collected1029; 954 passed / 42 skipped / 1 xfailed; 307.62s | 전체 기본 PC discovery 실행 완료. failed/error/collection error 없음. skip/xfailed를 PASS로 합산하지 않음 |
| python tools/test_runner.py openpilot/selfdrive/controls/tests -j 1 -v | exit0; 63 passed; 28.10s | 실제 native MPC/frozen planner/LongControl parity5와 portable30 포함. 앞 실행과 중복 coverage임 |
| PC hardware skip subset, original collect/make_batches/run_batch 재사용 | exit0; hardware methods43 → skip records11; delta32 | hardware methods는 실행하지 않음. PC의 원래 setUpClass SkipTest 기록 방식을 설명하는 진단 |
| candidate8 / prior docs9 / old native logs12 hash audit | 정상 종료, 모두 동일 | 원본/reference/native source 동일, 이전 증거 보존 |

수집1029개 대비 최종997 records의 차이32는 PC hardware class fixture skip 때문이다.
43개 하드웨어 methods가11개 fixture skip records로 묶이는 것을 원래 runner의 같은 batch 순서에서
hardware subset만 재실행해 확인했다. 새 skip/ignore/threshold 변경은 없다.
기존 expected failure도 유지했다. 전체 tests가 실제 하드웨어에서 실행됐거나1029개가 PASS라는 뜻이 아니다.

8절의 누락 clang++/TLS 문제가 해소돼 전체 runner는 정상 종료했다.
기본 discovery에 포함되는 locationd scenario의 내부 process replay도 실행됐으나,
별도 process_replay/test_processes.py 및 simulator는 원래 default discovery에서 제외된다.
위 locationd 회귀를 Cyber Long의 qualified plannerd/controlsd/radard replay, 차량별 closed-loop 또는
비작동 shadow 증거로 간주하지 않는다. 외부 fixture/model/firmware/holdout을 고정한 Cyber 평가도 아직 없다.

### 변경·보존 및 현재 결론

제품/테스트 source8개, upstream limits/safety/driver override, submodule gitlinks, build/lockfile,
테스트 acceptance/ignore/replay references는 이번에 변경하지 않았다. 원본 index는 비어 있다.
후보 identity는 6절의 hashes 및 c8fb906815530460ed156f14e09e1f312bb0f851 baseline 그대로다.
Git에 포함할 변경은 이 기록과 Phase A/C 기능 기록의 후속 문서 수정뿐이다.
로컬 wrapper/CA/진단 스크립트/보고서 및 raw logs는 .git/info/exclude 대상이다.

새 raw logs: /opt/cyberpilot-step5/logs-tls-20260929 (이전 /logs와 별개).
새 manifest: work/step5-native/tls-evidence.json. 실제 command/exit/count/time, candidate/source hashes,
로그 및 bundle hashes, 이전 docs/logs 보존, qualification=false를 기록한다.
이전 portable/native manifests와 실패 로그는 보존했다. full runner 및 controls 재실행은 종료했다.

승인된 default-disabled/observation-only Phase A 및 fail-closed Phase C의 초기 PC 구현/회귀 검증은 통과했다.
이는 Carrot control 이식/comfort 개선을 적용한 버전이나 Step5 전체 완료가 아니다.
Phase B cut-in/comfort는 미구현이고 모든 tuning proposal은 accepted=False다.
다음 gate는 target vehicle/firmware/model/log/holdout/metric 기준 고정, qualified replay,
그 다음 차량별 closed-loop 및 non-actuating shadow다. Phase B는 효과/license/bounds 검토 후 별도 구현한다.
실차 적용, safety 승인, commit/push/deploy 및 Step6/7로의 전환은 수행하지 않았다.

## 10. 명시적으로 승인된 feature branch 게시 전 재검증 — 2026-09-29

이후 사용자가 GitHub commit/push를 명시적으로 요청했다. 게시 범위는 기존 개발 규칙,
비교/설계 문서 및 default-disabled/observe-only Phase A와 fail-closed Phase C 후보를
feature/cyber-long에 기록하는 것이다. develop/main 병합, PR 생성, Phase B 활성화,
실차/장치 쓰기, safety 승인 또는 Step5 전체 완료는 포함하지 않는다.

같은 Ubuntu24.04.5/Python3.12.14 native replica와 기존 명령별 TLS bundle을 사용했다.
native HEAD는 위 c8fb baseline이며, 원본과 native의 candidate8 SHA-256이 이전 기록과
동일함을 재확인했다. 제품 source/limits/lockfile/submodule pins는 추가 변경하지 않았다.

| 이번 게시 전 검사 | 실제 결과 | 범위 |
| --- | --- | --- |
| affected Python8 Ruff check | exit0, All checks passed | 기존 configured rules 유지 |
| python tools/test_runner.py openpilot/selfdrive/controls/tests -j 1 -v | exit0, 63 passed, 29.17s | portable30/native parity5 포함 |
| 공개 후보 파일 LF/whitespace/local links/private-pattern 검사 | 22 files 정상 | 비공개 simulator/Drive/인계 파일은 제외 |
| origin/feature/cyber-long fetch 및 divergence 검사 | baseline과 0 ahead / 0 behind | 게시 전 공유 branch 충돌 없음 |

이번에는 full runner/build/process replay/simulator/shadow를 다시 실행하지 않았다.
9절의 full runner954/42/1 결과는 이전 실행 기록 그대로이며 새 controls 결과와 합산하지 않는다.
새 실행 로그는 로컬 제외 경로 work/github-publish-20260929에 별도로 보존한다.
비공개 분석, 인계 ZIP, raw logs, 인증자료와 CA bundle은 공개 Git에 넣지 않는다.
게시 결과의 commit SHA와 실제 원격 일치는 Git history 및 별도 로컬/Drive 인계 기록으로 확인한다.
