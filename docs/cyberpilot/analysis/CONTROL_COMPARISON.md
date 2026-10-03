# OpenPilot / SunnyPilot / CarrotPilot 제어 경로 비교

분석 기준일: 2026-09-29. CyberPilot Step 3의 **정적 코드 조사**다.
기능 이식, 제어 코드 수정, 차량 배포 또는 실차 사용 승인이 아니다.

## 결론부터

- **A — 그대로 활용:** CyberPilot이 이미 상속한 최신 openpilot의 모델 action,
  lead MPC, 가속도 기반 LongControl, curvature 제한, 차량별 제어 변환,
  paramsd/torqued/lagd를 기준선으로 유지한다. 그대로 활용은 신규 검증 면제가 아니다.
- **B — 개념을 활용해 재구현:** Carrot의 명시적 정차 상태와 stop-distance
  추정, Sunny의 상황별 E2E 선택·jerk-aware friction·곡선 속도 후보가 연구
  가치가 있다. 최신 upstream 인터페이스와 안전 제한 안에서 각각 실험한다.
- **C — 채택하지 않음:** fork 전체 merge, 구형 LongControl/MPC 통째 교체,
  제한 확대, DM/engagement 경로 변경, 학습 승인 기준 완화, 외부 신호에만
  의존한 자동 출발, CarrotMan 서비스 전체 도입을 권고하지 않는다.
- Sunny의 NNLC는 **후순위 B 연구 후보**다. 모델/학습 데이터/차량 식별/라이선스와
  fallback 검증 전에는 코드 또는 가중치 그대로 도입하는 A가 아니다.

표의 장점은 소스 구조에서 도출한 **기대효과/가설**이고, 성능 측정 결과가 아니다.
난이도와 충돌 가능성은 CyberPilot 최신 upstream 기준의 기술적 판단이다.

## 1. 고정된 조사 기준과 재현 방법

| 프로젝트 | 실제 기본 브랜치 | fetch 후 분석 commit SHA |
| --- | --- | --- |
| OpenPilot (`O`) | `master` | `c8fb906815530460ed156f14e09e1f312bb0f851` |
| SunnyPilot (`S`) | `master` | `a5f44653d7f43ad57fef2f546f3916ec4cbf3c56` |
| CarrotPilot (`C`) | `carrot2-v6` | `c57d0ff11f766b7fd70e9a9eaec1247b623ffbea` |

각 remote의 `HEAD` symref를 live 조회했다. 브랜치 이름을 README에서 추정하지 않았다.
위 SHA는 조회/fetch 시점의 snapshot이며 이후 remote tip이 같다는 보장은 없다.
CyberPilot `develop` HEAD는 OpenPilot 기준 SHA와 같았고 Step 2의
`AGENTS.md`, `FEATURE_CHANGE_TEMPLATE.md`는 기존 미커밋 파일로 보존했다.

실행한 root Git 명령:

```powershell
git status --short --branch
git rev-parse HEAD
git remote -v
git submodule status
git ls-remote --symref openpilot HEAD
git ls-remote --symref sunnypilot HEAD
git ls-remote --symref carrotpilot HEAD
git fetch --prune openpilot
git fetch --filter=blob:none --no-tags sunnypilot master
git fetch --filter=blob:none --no-tags carrotpilot carrot2-v6
```

fetch는 세 remote에서 성공했다. Sunny/Carrot은 partial-clone 방식으로 필요한
blob을 추가 조회했다. root 저장소 history를 shallow로 바꾸지 않았다.
분석은 `git show <고정 SHA>:<실제 경로>`로 수행했다. 현재 작업 트리의 파일을
세 프로젝트 파일인 것처럼 혼용하지 않았다.

[소스 목록 JSON](CONTROL_COMPARISON_SOURCES.json)의 `O01`…`C12`는 아래 표의
관련 파일 키다. 각 키에는 저장소, 고정 SHA, 정확한 전체 파일 경로와 조사한
함수/클래스가 들어 있다. 의존성 코드에도 별도 SHA를 부여했다.
원문 링크는 `repositories[repo].url + /blob/ + commit + / + path`로 재현한다.
예: [O02 planner](https://github.com/commaai/openpilot/blob/c8fb906815530460ed156f14e09e1f312bb0f851/openpilot/selfdrive/controls/lib/longitudinal_planner.py),
[S02 extension](https://github.com/sunnypilot/sunnypilot/blob/a5f44653d7f43ad57fef2f546f3916ec4cbf3c56/openpilot/sunnypilot/selfdrive/controls/lib/longitudinal_planner.py),
[C03 CarrotPlanner](https://github.com/geniuth2/openpilot_carrot/blob/c57d0ff11f766b7fd70e9a9eaec1247b623ffbea/selfdrive/carrot/carrot_functions.py).

### 의존성과 라이선스 경계

| 대상 | snapshot의 실제 구조 | 조사 범위 / 미확인 사항 |
| --- | --- | --- |
| OpenPilot opendbc | gitlink `4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76` | 별도 읽기용 object DB에 해당 commit을 fetch; 인터페이스, Hyundai/Toyota controller 확인 |
| Sunny opendbc | gitlink `f95f996f5917dcbbf2e32fe51b606a24cf836af6` | Sunny fork의 해당 commit fetch; torque interface, Hyundai controller 및 SCC CAN 필드 확인 |
| OpenPilot panda | gitlink `92eb565169fd553f4dfaf508c1a3f8dbc14fbfbf` | pin만 기록; panda 구현 전체와 하드웨어 safety 동등성은 미검증 |
| Sunny panda | gitlink `74a0adced421e8b7acd728d0f9988ce225423f13` | pin만 기록; safety audit 아님 |
| Sunny NN data | gitlink `03cac2d30e111e0689c0429cb8c1fe6cb5a905af` | 선택/호출 코드 확인; 실제 가중치, 학습 데이터, 차량별 성능은 미검증 |
| Carrot opendbc/panda | gitlink가 아니라 vendored tree; 각각 `755cca52c9247ec0877b3fca58a9c74c3f9b2e33`, `76cb122abc0132fbae08cb3920ea53cafcf19f33` | Carrot root SHA로 코드 식별. 이 tree ID를 원본 독립 repo의 commit SHA라고 주장하지 않음. root `.gitmodules` 없음 |

CyberPilot root의 여섯 submodule은 초기화되지 않은 상태를 유지했다.
별도 reference DB는 `work/reference-opendbc-openpilot/`와
`work/reference-opendbc-sunnypilot/`에만 만들었다. 두 디렉터리는 로컬
`.git/info/exclude`로 commit 대상에서 제외했으며, 추적되는 `.gitignore`는 바꾸지 않았다.
root gitlink SHA, submodule URL, LFS pointer 및 build 구조는 변경하지 않았다.

- OpenPilot root [LICENSE](https://github.com/commaai/openpilot/blob/c8fb906815530460ed156f14e09e1f312bb0f851/LICENSE)는 MIT 내용이다. 원본 고지와 귀속을 보존한다.
- Sunny root [LICENSE.md](https://github.com/sunnypilot/sunnypilot/blob/a5f44653d7f43ad57fef2f546f3916ec4cbf3c56/LICENSE.md)는 **Custom MIT License**이며 상업/영리/closed-source 이용의 서면 허가 및 재배포·표시 조건을 명시한다. Sunny opendbc도 같은 유형의 루트 문서다. 개별 헤더의 MIT 표기만으로 무조건 재사용 가능하다고 판단하지 않는다.
- Carrot snapshot의 root 및 조사한 vendored opendbc/panda 파일 목록에서
  명시적 LICENSE/COPYING 파일을 찾지 못했다. 상속 코드의 권리와 새로 추가한
  코드의 권리를 구분해야 한다. **Carrot 신규 코드의 그대로 복사/재배포는
  라이선스 확인 전 보류**다. 이는 법률 검토를 대체하지 않는다.
- B는 코드 복사 허가를 뜻하지 않는다. 독립 구현도 실제 권리/귀속 검토가
  필요하다. 이 문서는 제3자 소스/모델 가중치를 저장소에 복제하지 않는다.

## 2. 실제 호출 경로와 데이터 흐름

### OpenPilot — 현재 CyberPilot 기준선

```text
modeld.get_action_from_model → modelV2.action {desiredAcceleration, shouldStop, desiredCurvature}
modelV2.leadsV3 + radarTracks → radard → radarState.leadOne/leadTwo
modelV2 갱신 → plannerd → LongitudinalPlanner
  radarState → lead-only MPC → delayed acceleration candidate
  vCruise → cruise acceleration candidate
  experimentalMode인 경우 model action → E2E acceleration candidate
  후보 중 최소 acceleration, shouldStop은 후보들의 OR → longitudinalPlan
carState 갱신 → controlsd → LongControl(aTarget - aEgo) → carControl.actuators.accel
model action / 유효 lateralManeuverPlan → clip_curvature → 선택된 lateral controller
  → carControl.actuators.{torque, steeringAngleDeg, curvature}
card → CI.apply → 차량 CarController → CAN message → sendcan
carOutput.actuatorsOutput → controlsd의 제한/포화 피드백
```

O01의 action은 모델에 action 출력이 있으면 이를 해석하고, 없으면 trajectory에서
지연 시점의 acceleration/curvature를 계산한다. longitudinal/lateral smoothing과
low-speed curvature 처리를 거친다. 따라서 모델 파일 하나의 label만으로 동작을
정의할 수 없다.

O02/O03에서 MPC 자체의 obstacle은 lead0/lead1이다. cruise/E2E는 **planner에서
별도 가속도 후보**로 결합된다. O02가 publish하는 `speeds/accels/jerks`는 MPC
trajectory이고 `aTarget`은 최종 선택 값이므로 두 가지가 항상 같은 후보라는
가정은 틀리다. `shouldStop` 역시 최소 가속도 후보 하나의 stop bit만이 아니다.
통합 시 테스트는 trajectory뿐 아니라 실제 actuator consumer가 읽는
`aTarget`, `shouldStop`, `allowThrottle`을 확인해야 한다.

O05는 `off → pid ↔ stopping` 상태이며 별도 `starting` phase를 쓰지 않는다.
PID는 가속도 오차에 차량별 Ki와 aTarget feedforward를 사용한다. 제한은
planner 상수, `CI.get_pid_accel_limits`, 차량 controller, hardware safety처럼
서로 다른 층에 있다. 이 문서가 마지막 층까지 안전성을 입증한 것은 아니다.

### SunnyPilot — upstream 후보 선택 + 확장 계층

```text
modeld action + radar fusion → 같은 upstream 형태의 기본 long path
LongitudinalPlannerSP.update → DEC 상태/긴급성 판단
update_targets → vision SCC / map SCC / SpeedLimitResolver / SpeedLimitAssist
  → 최저 speed 후보와 그 후보의 acceleration 선택 → 기본 planner 입력/상태
is_e2e → experimentalMode 및 DEC blended 여부 → E2E 후보 포함 여부
기본 planner 최소 acceleration arbitration → LongControl → vehicle controller

controlsd → ControlsExt.initialize_lateral_control → torque V0 또는 기본 controller
  → torque extension 기본 계산 → jerk-aware 선택 경로 → NNLC 선택 경로
  → 최종 torque-space PID output → CI.apply
```

S02의 speed 후보 선택은 마지막 actuator acceleration 후보 선택과 다르다.
S03의 `acc/blended` 이름도 Carrot의 구형 blended-MPC 의미와 같지 않다.
DEC가 E2E candidate를 참여시키는지를 결정하고 실제 acceleration arbitration은
base planner에 남는다. 판단 입력은 lead 존재, 모델 endpoint/속도, slowdown,
standstill, FCW와 필터/전환 조건이다. 성능 개선을 측정한 것은 아니다.

S06의 초기화 코드를 따라가면 torque 차량이고 `EnforceTorqueControl`이 꺼진
일반 경로는 **V0 controller를 선택**한다. 기본 upstream 파일만 diff하면
실제 실행 controller를 놓친다. V0는 지연된 요청과 미래 요청의 차이로 jerk를
구하고 다른 setpoint/이득을 쓰며, S07/S08 확장이 base output을 다시 계산할 수 있다.

S08의 NNLC는 enable toggle, 모델 유효성, 모델 존재 조건을 모두 확인한다.
차량 fingerprint/EPS firmware 문자열의 유사도와 substitute 후보로 JSON 모델을
선택하고, 과거/미래 lateral acceleration·jerk·roll 등의 입력으로 torque를
추론한다. 단순 torque feedforward 한 줄이 아니다. 입력 정규화, 모델 선택,
높은 횡가속도 blending, friction override, 최종 PID까지 한 묶음으로 검증해야 한다.
가중치와 학습 분포는 읽지 않았으므로 차종 지원 또는 우수성을 인정하지 않는다.

S11 Hyundai 경로는 controller가 5프레임마다 longitudinal tuning 상태를 갱신하고,
CAN helper가 `desired_accel`/`actual_accel`을 각각 SCC `aReqRaw`/`aReqValue`에
넣는다. predictive/dynamic flags에 따라 속도별 jerk 및 jerk-limited integration을
쓰며 radarUnavailable일 때는 다른 분기다. 일반 LongControl만 읽어서는 이 차이를
알 수 없다. `actual_accel`은 이 코드가 산출한 명령 상태 이름이지 실측 가속도가 아니다.

### CarrotPilot — 명시적 정차 상태 + 구형 trajectory/MPC 파이프라인

```text
modeld → trajectory + desired_curvature → modelV2
card.VCruiseCarrot → vCruise / softHoldActive / activateCruise / latEnabled
radard → VisionTrack / radar matching → 구형 radarState lead fields
plannerd → CarrotPlanner.update → XState / stop distance / adjusted cruise / follow policy
  → LongitudinalMpc.update(carrot, radar, cruise, x/v/a/j)
  → ACC: lead0/lead1 + cruise obstacle + virtual stop obstacle
  → blended: trajectory target + lead obstacles
  → delay sampling → longitudinalPlan {aTarget, vTarget, jTarget, shouldStop, ...}
controlsd → speed-error LongControl / optional starting / soft-hold → accel + jerk
  → HyundaiJerk + vehicle CAN helper → StopReq / aReq / jerk bounds

model position/lanes → LanePlanner → lateral MPC → lateralPlan
controlsd: lane-plan 경로 / model action 경로 / now-vs-future CarrotLatControl 경로
  → torque/PID/angle → vehicle controller
```

C03의 `red/green`은 model trajectory endpoint, 최종 속도, stop/start 누적
시간으로 만든 내부 상태다. **카메라가 신호등 색을 직접 인식했다는 증거가 아니다.**
별도로 C11 외부 입력이 만든 `carrotMan.trafficState` 전이도 C03에서 상태 변경에
참여한다. 둘을 같은 신호등 인식 기능으로 합쳐 설명하지 않는다.

C02가 experimentalMode로 MPC 기본 mode를 정하지만, ACC 진입 경로에서 C03의
`e2ePrepare`가 local blended 경로를 선택할 수도 있다. C03 state만 보고
MPC 내부의 모든 분기가 바뀐다고 단정할 수 없다. weight/source bookkeeping과
local mode의 일관성은 실제 replay가 필요한 부분이다.

C03 `x[31]` 등 직접 인덱스 접근은 C02의 parse_model 길이 fallback보다 먼저
호출된다. 짧은 모델 메시지를 C02에서 0으로 대체한다는 사실만으로 C03까지
안전하게 처리된다고 볼 수 없다. C03 comfortBrake가 stop-distance 분모에,
C02 LongActuatorDelay가 acceleration 계산 분모에 쓰이므로 0/음수/NaN/누락
파라미터 입력은 별도 rejection/fallback 테스트가 필요하다.

C07은 lane probability/std/width와 차선 변경 상태를 이용해 path를 만들고
lateral MPC를 돌린다. C06은 `useLaneLines`, speed/curve 조건과 설정에 따라
그 경로를 사용하거나 model curvature로 돌아간다. 따라서 lateralPlan이
publish되었다는 사실만으로 실제 steering이 이를 사용한다고 할 수 없다.

## 3. Longitudinal 비교표

키의 전체 파일 경로는 [소스 목록](CONTROL_COMPARISON_SOURCES.json)을 따른다.
각 행의 A/B/C는 **현재 권고**이며 개발/도로 사용 승인이 아니다.

| 기능 | OpenPilot | SunnyPilot | CarrotPilot | 관련 파일 | 핵심 차이 | 장점 (가설) | 단점/위험 | CyberPilot 채택 후보 여부 | 이식 난이도 | upstream 충돌 가능성 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Model output | action 또는 plan에서 a/curvature 생성, shouldStop와 smoothing | 기본 action 경로 유지, 확장 planner가 model bundle/trajectory 소비 | 구형 trajectory 중심, desired_curvature 출력 | O01; S01/S02; C01/C02 | action 중심 대 구형 trajectory 소비 | 최신 모델 계약 유지로 추적 간결 | 모델 시간축/weights 차이를 controller 개선으로 오인 | A upstream; fork 모델 교체 보류 | 낮음(유지)/매우 높음(교체) | 낮음/높음 |
| Longitudinal planner | lead MPC + cruise + 조건부 E2E acceleration 후보 | 최저 속도 후보(SCC/SLA) 먼저 선택 후 base a arbitration | Carrot state가 cruise/stop/follow/MPC 모드에 입력 | O02/O03; S02; C02/C03 | 후보 arbitration 대 상태+obstacle 변경 | 독립 speed/stop 후보 설계 가능 | 후보 우선순위, state reset, stop OR 의미 혼동 | A base + B 단일 후보 어댑터 | 중간~높음 | 중간~높음 |
| Lead handling | 확률 필터, radar/vision 매칭, aLeadK와 2 leads | base + 특정 Hyundai radar yRel를 vision으로 보정 | 별도 VisionTrack 추정, 넓은 매칭 범위, aLead 사용 | O04/O03; S10; C04/C02 | schema와 lead 추정치/매칭 정책 차이 | 안정적 fusion을 유지하면서 차종별 보정 평가 | 잘못된 lead association, 중복/누락, 추정 지연 | A base; B 특정 차종 보정 연구 | 높음 | 높음 |
| Stopping | candidate shouldStop OR, off/stopping/pid, stopAccel ramp | 기본 stop 경로 + Hyundai 튜닝 stop-state | e2eStop/e2eStopped, virtual stop obstacle, softHold | O02/O05; S10/S11; C03/C05/C12 | planner 상태와 actuator stopping을 분리해야 함 | 정차 이유/거리/state 관측성이 좋아질 수 있음 | 유령 정차, creeping, state stuck, invalid trajectory | B 명시적 stop estimator/state 관측 우선 | 높음 | 높음 |
| Starting | !shouldStop, !cruiseStandstill, !brake로 pid 복귀 | gas-interceptor일 때 cruiseStandstill gate가 다름 | optional starting state/startAccel, e2ePrepare, 외부 green 전이 | O05/O06; S10; C03/C05 | 출발 승인과 초기 acceleration 형성 차이 | 출발 과도응답을 분리해 평가 | 신호 오판에 의한 출발, 브레이크/standstill 계약 변경 | B 과도응답 분석; C 외부 green만으로 출발 | 높음 | 높음 |
| Cut-in 대응 | radard association → 두 lead obstacle, 최소 거리 수치 clipping | base fusion + DEC 입력으로 lead 상태 사용 | 매칭 distance .35 vs base .25, high-prob velocity tolerance 25 vs 10 m/s; side leads publish | O04/O03; S03/S10; C04/C02 | 표본 검출/융합과 제어 반응은 별개 | association/false-positive tradeoff 비교 가능 | 허용폭 확대는 잘못된 물체 추종 위험; side-lead publish가 MPC 소비 증거는 아님 | B offline 연구; 완화값 직복사 C | 높음 | 높음 |
| Cruise control | card VCruiseHelper의 버튼/PCM speed → cruise candidate | SCC/SLA speed 정책, CP_SP 및 별도 cruise/engagement 확장 | VCruiseCarrot가 softHold/activate/latEnabled까지 생산; eco overspeed 정책 | O10/O02; S02/S06/S11; C10/C03 | 속도 설정과 활성화 정책이 fork에서 결합 | speed 후보는 독립화 가능 | auto-engage/override/eco 속도 초과의 권한 변화 | A base; B speed 후보; C 전체 helper 교체 | 중간~높음 | 높음 |
| Acceleration target | min(MPC, cruise, optional action), 최종 global clip | speed 선택 및 state seed 후 같은 min a | delay에서 MPC v/a/j를 뽑아 aTarget/vTarget/jTarget 제공 | O02; S02; C02/C05 | aTarget과 trajectory의 일치 여부, 제어 오차 종류 | base 계약으로 후보 검증 쉬움 | vTarget를 신형 LoC에 붙이면 double-control/단위 mismatch | A aTarget 계약; B 후보 방식 | 중간 | 중간 |
| Acceleration limits | interface global -3.5/+2.0 m/s², 차종별 pid/CAN 제한, turn combined bound | base 제한과 추가 Hyundai clipping/integration | interface global -4.0/+2.5 m/s², cruise min -2.0, 사용자 accel/comfort 파라미터 | O02/O11; S02/S11; C02/C03/C12 | 층별/차종별 제한값이 다름 | 기존 제한 내 comfort 정책 연구 | 더 넓은 상수를 복사하면 안전/모델 전제 변경; hardware 허용성 미검증 | A upstream 제한; C fork 제한 확대 | 낮음(유지)/높음(변경) | 높음 |
| Jerk control | MPC jerk/change costs + cruise a slew; Hyundai controller에도 CAN jerk | planner 기본 + Hyundai 속도별 upper/lower jerk 및 명령 적분 | personality/change costs + jTarget → LoC → HyundaiJerk/CAN comfort band | O02/O03/O11; S11; C02/C05/C12 | optimizer jerk, target derivative, ECU jerk field는 동일하지 않음 | 차량별 명령 smoothing 개념 | cut-in/급감속 응답 지연, double smoothing, ECU 필드 의미 | B 계층별 측정 후 차량 모듈 설계 | 높음 | 중간~높음 |
| LongControl | aTarget-aEgo PI(Kp=0) + acceleration FF | 동일 기본 오차; CP_SP/gas interceptor 분기 | vTarget-vEgo PID + aTarget FF; optional starting와 manual gain Params | O05; S10; C05 | 가속도 폐루프 대 속도 폐루프 | 현재 upstream를 안정적 비교 기준으로 유지 | LoC만 교체해도 planner/vehicle compensation와 상호작용 | A base; C 구형 LoC 통째 교체 | 매우 높음 | 매우 높음 |
| Actuator delay | CP.longitudinalActuatorDelay가 model action 및 MPC sampling에 참여 | 기본 CP delay 유지 | LongActuatorDelay Params를 별도 sampling/분모에 사용 | O01/O02; S01/S02; C02 | 모델 horizon과 planner sampling의 delay 계약 차이 | delay 추정/관측을 명시화 가능 | 0 delay, 단위 .01 scaling, 이중 보상 및 stale 설정 | A base; B bounded vehicle delay 후보 | 중간~높음 | 중간 |
| Gas/brake compensation | CI/차량 controller에 분리; Toyota PCM PI/pitch/permit-braking, Hyundai accel clip | Hyundai tuning.accel/jerk → SCC aReqRaw/aReqValue | Hyundai soft-hold/StopReq/aReq/jerk 경로, custom actuator fields | O10/O11; S11; C10/C12 | planner 목표와 ECU 전달값 사이 차량 변환 차이 | 차종별 보상 분리 원칙을 그대로 활용 | 다른 차종에 일반화 불가; 명령 actual_accel을 실측으로 오인 | A 차량 분리; B 타깃 차종 한정 연구 | 높음 | 높음(opendbc) |
| Stop-and-go | planner stop bit, cruise resume, 차량 standstill handshake | interceptor/Hyundai flags에 따라 stop/resume 차이 | softHold→planner reset→LoC stopping→CAN StopReq, brake hold 분기 | O05/O06/O11; S10/S11; C03/C05/C10/C12 | planner 하나가 아니라 state/CAN handshake 문제 | 전체 전이를 묶어 검증할 수 있음 | creeping, unintended resume, takeover/stock ECU 차이 | B state evidence; C softHold 전체 이식 | 매우 높음 | 매우 높음 |
| Traffic light (별도) | 조사한 action/plan 경로에 색상 상태 machine 없음; 모델 action stopping은 존재 | DEC slowdown/E2E 선택이며 전용 색상 인식 증거 아님 | model endpoint 기반 red/green 휴리스틱 + 별도 외부 trafficState | O01/O02; S03; C03/C11 | heuristic stop intent ≠ traffic-light recognition | stop-intent 연구/설명 UI | 색/좌회전/선행차 오판, 외부 입력 stale, 자동 출발 | B stop intent shadow; C 신호 기반 자동 출발 | 매우 높음 | 높음 |
| Navigation / curve speed (별도) | 조사한 기본 long 경로에는 map-speed resolver 없음; curve combined accel 제한은 있음 | vision SCC, map target velocities, car/map speed-limit resolver + SLA | CarrotMan curve/route/speed 정보 → desiredSpeed cap와 vTurnSpeed | O02; S04/S05; C03/C07/C11 | 지도/시각/사용자 속도 후보를 제어에 결합 | 곡선 전 감속/속도 원인 관측 | 좌표·시간·provider 신뢰, 오제한, override; 외부 서비스 보안 | B vision speed 후보 우선; map 후순위; C 서비스 전체 | 높음 | 중간~높음 |

## 4. Lateral 비교표

| 기능 | OpenPilot | SunnyPilot | CarrotPilot | 관련 파일 | 핵심 차이 | 장점 (가설) | 단점/위험 | CyberPilot 채택 후보 여부 | 이식 난이도 | upstream 충돌 가능성 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Model path | model plan을 action으로 해석 또는 직접 action 사용 | 기본 action + extension용 trajectory, lane time helper | trajectory가 lane/MPC와 now/future control에 사용 | O01/O06; S01/S06/S07; C01/C06/C07 | trajectory 소비 위치와 time indices 차이 | upstream action 계약 유지 | 모델별 shape/time/좌표 mismatch | A action; B path 관측 | 중간 | 중간 |
| Desired curvature | action 또는 유효 lateralManeuverPlan, roll-aware accel/jerk/max clip | 동일 기본 curvature 경로, torque 확장 출력 | lane-plan 또는 model action, CarrotLatControl now/future lag sampling; 구형 jerk clip | O06; S06; C06 | 제한 함수 서명/의미와 now/FF 값 다름 | 현행 제한 안에서 지연/FF 평가 | Carrot clip에는 현행 roll-aware accel/max cap이 없는 형태; 전체 대체 위험 | A 현행 clip; B 분리 FF; C 구형 clip 대체 | 높음 | 높음 |
| Lateral planner | plannerd에는 별도 일반 path lateral MPC 없음; controlsd가 action 소비 | 기본 plannerd도 별도 일반 lateral MPC 없음 | plannerd가 LateralPlanner/MPC를 실행해 lateralPlan 발행 | O02/O06; S02/S06; C02/C07 | 같은 이름의 파일 유무보다 runtime caller 차이 | 별도 path 후보를 offline 비교 가능 | 추가 solver/schema/state/스케줄 coupling | B offline path candidate; C 통째 복귀 | 매우 높음 | 매우 높음 |
| Torque controller | V1: lateral-accel 공간 PID 후 CI torque 변환, delayed desired/actual 비교 | 일반 torque 초기화는 V0; optional jerk-aware/NNLC는 torque-space PID 재계산 | 저속 curvature 보정, vehicle torque callback, D/friction/manual tune | O07/O11; S06/S07/S11; C08/C12 | gain 숫자뿐 아니라 오차/FF 공간이 다름 | 소규모 friction/FF 후보 비교 | V0/V1 이득 혼용, 포화/적분 상태, 차종 converter | A V1; B 국소 후보; C controller 통째 교체 | 높음 | 높음 |
| PID | VM curvature→desired angle, 차량 FF, low-speed/driver/limit integrator freeze | 기본 계산 유사, CP_SP/calibrated_pose 인터페이스 확장 | 구형 interface, driver override 및 별도 reset 경로 | O08; S12; C08 | 입력 서명/적분 동작 차이; fork라고 새 PID 알고리즘은 아님 | 기존 차종 튜닝 유지 | torque와 angle PID를 같은 gain으로 취급 | A 기존 PID 유지 | 낮음 | 낮음(유지) |
| Angle control | VM/offset 변환, 차종별 saturation; 별도 curvature control도 지원 | angle 계산은 base 유사, 확장 인자 | 구형 angle 변환/2.5deg saturation 방식 | O08; S12; C08 | controller 종류와 차량 최종 limit 분리 | 현재 차종별 방식 활용 | angle/torque/curvature actuator 형식 mismatch | A upstream | 낮음 | 낮음 |
| Steer ratio | paramsd 추정→vehicleParameters→VM, sanity flags | 기본 live estimation 경로, controller 확장 인자 | liveParameters + SteerRatioRate/CustomSR override | O09/O06; S06; C09/C06 | learned estimate 대 수동 scaling/override | 추정 provenance 관측 | 차량식별 누락, 잘못된 ratio가 모든 curvature 변환에 영향 | A base; B bounds/confidence UI; C 무검증 override | 중간 | 중간 |
| Actuator delay | lagd cross-correlation/valid blocks, 초기 CP delay+.2 fallback; model/controller 사용 | LagdToggle 또는 fixed LagdValueCache 선택 | SteerActuatorDelay/ModelDelay 설정, now/FF sampling, torqued도 설정 lag | O09/O01/O06; S09/S06; C06/C09 | learned status/fallback 대 설정 기반 timing | delay 신뢰도와 fallback을 AutoTune에 활용 | double compensation, phase lead, 차량/로그 불일치 | A lagd; B 제약된 candidate 연구 | 높음 | 중간~높음 |
| Friction | filtered(error + jerk lookahead), roll/offset 보정 후 FF | V0 방식 + jerk-aware lookahead + NN friction override + manual params | CI friction/error 기반, manual friction/F factor | O07/O11; S07/S08; C08/C12 | friction 입력과 적용 공간/중복 여부 | 저속 이력/jerk-aware 가설 비교 | roll/offset/friction 중복, high-accel extrapolation | B 단일 friction 후보; A fallback | 높음 | 중간 |
| latAccelFactor | torqued bucket/TLS/filter/clamp → useParams로 controller 갱신 | 기본 추정 + toggles/manual + relaxed bucket/sanity 옵션 | 구형 liveTorqueParameters, manual LateralTorqueCustom이면 learning update 억제 | O09/O06; S09/S06/S07; C09/C06/C08 | estimate validity와 사용자 override 승인 경로 | 기존 학습 evidence 유지 + confidence 표시 | factor 0/음수/NaN, 마찰과 식별 상관, 완화된 sample coverage | A 기본 estimator; B confidence; C 승인 기준 완화 | 높음 | 중간 |
| NNLC | 조사한 기본 torque 경로에는 NNLC extension 없음 | fingerprint/EPS/substitute JSON 선택→normalized past/future/jerk/roll→NN FF/error→PID | 조사한 torque 경로에는 동등한 NNLC 없음 | O07; S08/S07/S11; C08 | 학습 모델이 torque error/FF 계산에도 참여 | 비선형 차량 응답 모델 연구 | fuzzy vehicle match, OOD, 모델/데이터 라이선스·버전·품질 미검증 | B 후순위 offline/shadow 연구, A 아님 | 매우 높음 | 높음 |
| Self-tune | paramsd(sr/stiffness/offset), torqued(factor/friction), lagd(delay) | base + live toggles/custom bounds/override; relaxed acceptance 옵션 | paramsd/torqued 상속 + 수동 gains/ratio/delay 설정 | O09; S09/S07; C09/C08 | 일부 추정이 있다는 것 ≠ 전 차량 자동 최적화 | AutoTune 시작점은 upstream estimator observability | manual knobs를 자동튜닝으로 오인, unsafe candidate auto-apply | A 추정기; B provenance/rollback; C safety tuning | 높음 | 중간~높음 |
| Curve handling | model curvature + roll-aware clip; long combined accel 제한 | 같은 기본 경로 + vision/map speed candidates, jerk-aware steering | lane/curve offsets, vTurnSpeed gating, now/future FF | O06/O02; S04/S06/S07; C07/C06/C11 | 감속과 steering/path 보정을 별도로 평가해야 함 | 먼저 speed 후보만으로 효과 분리 가능 | path offset가 차선 여유를 줄임, long/lat 동시 변경의 원인 불명 | B speed 우선; offset 후순위 | 높음 | 높음 |
| Lane/path handling | model path/desire와 action; lane outputs가 곧 명시적 lane centering은 아님 | 기본 action + desire/extension consumers; path MPC 중심은 아님 | line prob/std, width filter, lane-change mode/hysteresis, offsets → MPC path | O01/O06; S01/S06; C07 | probability 혼합과 plan 사용 gate 추가 | 주행 경계/차선 confidence 비교 가능 | 좁은 차로, 누락/합류/공사선, offset discontinuity | B offline candidate; C default lane-MPC 대체 | 매우 높음 | 매우 높음 |
| Steering smoothness | model smoothing + curvature slew/cap + torque PID/friction + vehicle rate limits | V0/jerk-aware/NNLC/predictive horizon이 base 응답 수정 | low-speed factor, error delta D, damping * steeringRate, path filtering | O01/O06/O07/O11; S07/S08/S11; C07/C08/C12 | smoothing은 여러 계층의 지연/피드백 조합 | 계층별 응답/phase 분석 가능 | C08 damping은 PID 이후 합산, 그 함수 내 재clip 불명; vehicle limit와 별도 확인 필요 | B 계층별 분석; C 무검증 damping 복사 | 높음 | 높음 |

## 5. 위험이 큰 차이와 아직 증명하지 못한 부분

1. **안전 제한 확대 금지.** C12 interface 상수는 O11보다 넓다. 이것은 소프트웨어
   범위 차이를 확인한 것이지 Carrot panda가 위험하다거나 안전하다를 실증한
   결론이 아니다. CyberPilot에는 upstream 범위를 유지한다.
2. **DM와 activation 변경 제외.** C06의 `forceDecel` 조건에는 `DisableDM` 설정이
   참여하고, C10이 만드는 `latEnabled`/`activateCruise`도 control path에 연결된다.
   S06은 MADS 상태를 lateral active 판단에 사용한다. 이런 권한 변경은 단순
   smoothing 기능의 부수 이식으로 들어와서는 안 된다.
3. **외부 navigation은 별도 trust boundary.** S04 map 경로는 shared Params의
   GPS/target JSON을 소비한다. S05는 map age를 검사하려 하나 inspected code의
   `time.monotonic()`과 `unixTimestampMillis`를 직접 빼는 부분은 clock-domain
   확인이 필요하다. age check의 존재만으로 stale-data rejection을 입증하지 않는다.
   S02는 일부 추가 services의 alive/frequency/valid checks를 제외하므로 후보
   제공자의 개별 유효성 검증이 중요하다.
4. **CarrotMan을 navigation library로 통째 도입하지 않는다.** C11은 네트워크
   JSON을 받아 speed/traffic 정보를 생산하며 카운터 기반 만료도 포함한다.
   하지만 같은 객체가 `tcp://*:7710` 명령 채널을 열고 `echo_cmd`를 shell로
   실행하는 경로까지 포함한다. 해당 경로에서 인증 검사를 확인하지 못했다.
   실제 배포의 network reachability/외부 방화벽은 조사하지 않았다. 통째 이식은 C,
   향후 필요하면 읽기 전용·인증·크기/시간/단위 검증된 최소 adapter를 따로 설계한다.
5. **Self-tune ≠ AutoTune 완성.** 현재 추정기의 구체적 목적은 ratio/stiffness,
   torque factor/friction, lag다. PID gain을 범용 자동 최적화하거나 실차 개선을
   보장하는 통합 시스템을 세 프로젝트에서 확인한 것은 아니다. S09 relaxed
   bucket/sanity 옵션을 채택하는 것은 사용자 요구인 검증 기준 보존과 맞지 않는다.
6. **모델/차량/상태 계약 차이.** C의 `lead.status`/`aLead`, `liveParameters`,
   `actuators.steer`와 S/O의 `present`/`aLeadK`, `vehicleParameters`, `torque`는
   이름 치환만으로 호환되는 계약이 아니다. S의 CP_SP/custom channels,
   C의 stock message 확장을 CyberPilot cereal에 무조건 합치지 않는다.
7. **NNLC 승인 보류.** helper의 유사도/substitute 매칭은 정확한 hardware/model
   binding과 다르다. 모델 provenance, finite normalization, empty/mismatch
   fallback, OOD detection, 차량 firmware와 weights hash를 검증하기 전에는
   신규 steering source로 활성화하지 않는다.
8. **동작·성능·완전한 safety audit 미실행.** CPU/GPU 모델 실행, 모든 차종
   controller, panda safety tests, replay logs, simulation, shadow 및 road data를
   전부 조사한 것이 아니다. 표의 '없음'은 명시한 조사 경로에 대한 관찰이지
   저장소 전체에 관련 기능이 절대 없다는 주장으로 읽으면 안 된다.

## 6. CyberPilot 채택 제안

### A. 그대로 활용 가능 — 현행 upstream 기준선

- O01/O02/O03/O05/O06: action/lead/cruise arbitration, accel-error LongControl,
  curvature 제한 및 기존 takeover/engagement를 유지한다.
- O09: paramsd/torqued/lagd와 유효성/fallback을 AutoTune의 기존 추정 기반으로
  활용한다. 추정 상태/근거를 관측하는 것이 먼저이며 승인 범위를 확대하지 않는다.
- O10/O11: vehicle interface/CarController가 가진 compensation·CAN 변환·제한
  소유권을 유지한다. Hyundai 사례를 다른 차종으로 일반화하지 않는다.
- 기존 process replay/longitudinal maneuver/sim test 기반을 활용한다. 이번에
  테스트 infrastructure를 새로 만들거나 실행한 것은 아니다.

### B. 개념만 활용하고 CyberPilot 방식으로 재구현

| 우선순위 | 연구 후보 | 가장 작은 계약 / 검증 대상 | 승격 전 필수 확인 |
| --- | --- | --- | --- |
| 1 | AutoTune provenance/observability | 기존 estimate + 차량/firmware/code/config/model identity + validity/fallback 사유; 아직 새 runtime hook 만들지 않음 | 캐시 불일치, invalid/stale/NaN, reset, rollback, safety authority 불변 |
| 2 | Carrot stop intent/거리 추정 | model/lead/현재 상태 → 관측용 stop 후보/사유/신뢰도; upstream aTarget 소비 계약 보존 | 짧은 trajectory, lead switch/loss, 유령 정차, brake/gas/cancel, green 오판; 자동 출발 제외 |
| 3 | Sunny jerk-aware friction 가설 | upstream torque FF 한 부분만 A/B 비교, 같은 gain/clip/estimator 유지 | step/ramp/curve reversal, phase lag, saturation, 저속/고횡가속도, driver override |
| 4 | Vision curve-speed 후보 | trajectory 유효성이 있는 경우에만 bounded speed cap; long/lat 동시 변경하지 않음 | shape/time/unit/stale 입력, 빠른 curve reversal, override, 급감속/lead 우선순위 |
| 5 | 차량별 jerk/compensation | 타깃 차종의 command→CAN 변환 안에서만 한 기법; global 알고리즘과 분리 | ECU 필드 의미, stock/OP-long/flags, delayed emergency braking, stop-go handshake, safety 회귀 |
| 후순위 | DEC, map adapter, NNLC, lane/path 후보 | 각각 독립 offline estimator/candidate로 시작 | 라이선스, weights/provenance, clock/provider trust, model/vehicle match, fallback과 closed-loop 안정성 |

### C. 채택하지 않는 것이 좋음

- Sunny/Carrot 전체 merge, 오래된 MPC/LongControl/angle helper로 upstream 회귀.
- acceleration/curvature/steer/CAN 권한 제한 확대 및 safety flag/model 변경.
- `DisableDM`, 자동 engagement 또는 MADS 활성화 경로를 제어 개선과 함께 복사.
- relaxed learning sample/sanity acceptance와 무검증 manual tuning 경로.
- 외부 trafficState/heuristic green만으로 정차 해제·자동 출발.
- CarrotMan의 remote command/기기 관리/업로드 기능을 navigation adapter와 함께 도입.
- 현재 모델/vehicle binding 근거가 없는 NNLC 가중치 활성화나 무검증 curve offset.

## 7. 다음 단계의 검증 설계 (이번에 실행하지 않음)

각 후보는 [기능 변경 기록 template](../FEATURE_CHANGE_TEMPLATE.md)을 먼저
작성한다. license/reference, 목적/수정 파일, 기대효과, regression risk,
입력/acceptance 기준을 feature별로 확정하고 한 번에 한 경로만 변경한다.

1. **Baseline 준비:** 지원 Ubuntu/WSL 환경, root submodule pin 및 LFS 모델 자산,
   모델/설정 SHA와 승인된 입력 identity를 고정한다. 동일 input에서 unmodified
   upstream 결과를 확보한다. Windows source 읽기를 runtime 검증으로 세지 않는다.
2. **Unit / contract:** finite/bounds/unit/timestamp, 초기화·캐시·reset·fallback,
   단절/누락/짧은 model array, 차량 firmware mismatch, brake/cancel/override를
   테스트한다. 테스트/기준을 삭제하거나 완화하지 않는다.
3. **Replay:** stop-go, lead jump/cut-in/out, standstill, 잘못된 stopping intent,
   sharp curve/reversal, saturation과 loss/stale 입력을 같은 dataset로 비교한다.
   acceleration/jerk, stop distance, TTC/최소거리, curve error/lat-jerk,
   override/제한 flags, source와 state transitions를 기록한다. 숫자 기준은
   승인된 baseline에서 정하고 여기서 임의로 만들어 PASS를 정하지 않는다.
4. **Closed-loop simulation:** replay는 counterfactual plant 반응을 증명하지
   못한다. 센서/actuator delay, 마찰, 차량 모델 변화, lead brake/cut-in,
   lane confidence loss를 다룬다. default unit runner의 성공으로 대체하지 않는다.
5. **Shadow:** active controller는 upstream, candidate에는 actuator authority가
   없어야 한다. code/submodule/model/config/input identity, candidate isolation,
   timestamp와 comparison data를 확보한다. 장치·차량 작업은 별도 사용자 승인 필요.

승격 순서는 **replay → simulation → shadow validation**이다. 이후 실차 적용과
release 승인은 별도 결정이다. 이 문서의 B 권고만으로 구현/차량 시험이 승인되지 않는다.

## 8. 작업 결과와 검증 범위

이번 Step 3 추가 파일:

- `docs/cyberpilot/analysis/CONTROL_COMPARISON.md` — 호출 경로, 31개 기능 비교,
  위험/제약, A/B/C 제안과 후속 검증 계획.
- `docs/cyberpilot/analysis/CONTROL_COMPARISON_SOURCES.json` — source group별
  정확한 repository/branch/commit/path와 의존성 identity.

로컬 전용 변경은 두 reference object DB와 그 경로의 `.git/info/exclude`다.
Step 2 기존 파일은 수정하지 않는다. commit/push, merge/cherry-pick,
control/config/schema/submodule/LFS 변경은 하지 않는다.

검증 결과의 상세 명령/개수와 제한은 [검증 기록](CONTROL_COMPARISON_VERIFICATION.md)에
남긴다. 문서/소스 객체 검증과 runtime 동작 검증을 분리한다.
