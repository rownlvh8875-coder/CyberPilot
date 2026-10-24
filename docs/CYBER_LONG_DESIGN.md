# Cyber Long 설계 — Step 4

상태: **설계 제안 / 승인 대기 / 미구현**. 작성일: 2026-09-29.
이 문서는 Step 5 구현 승인이나 실차 적용 승인이 아니다.

## 1. 목적, 근거와 범위

Carrot의 longitudinal 아이디어를 최신 openpilot 구조에 맞게 선별 평가한다.
전체 Carrot planner/MPC/LongControl/CAN 코드를 복제하지 않는다. 이번 단계는
읽기 전용 소스 분석과 문서 작성이며 control/config/schema/gitlink는 바꾸지 않는다.

출발점은 [Step 3 비교](cyberpilot/analysis/CONTROL_COMPARISON.md)와
[고정 소스 목록](cyberpilot/analysis/CONTROL_COMPARISON_SOURCES.json)이다.

| 코드베이스 | 실제 확인된 기본 브랜치 | 분석 commit |
| --- | --- | --- |
| commaai/openpilot (O) | master | c8fb906815530460ed156f14e09e1f312bb0f851 |
| sunnypilot (Step 3 비교 참고) | master | a5f44653d7f43ad57fef2f546f3916ec4cbf3c56 |
| geniuth2/openpilot_carrot (C) | carrot2-v6 | c57d0ff11f766b7fd70e9a9eaec1247b623ffbea |

Step 3에서 fetch한 객체를 그대로 고정해 사용한다. Step 4에서 새로 전체 remote를
fetch하지 않았으므로 위 SHA를 이 문서를 읽는 시점의 최신 remote HEAD로 주장하지
않는다. 구현 직전 upstream을 다시 fetch하고 설계 차이를 재검토해야 한다.

O opendbc gitlink: 4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76.
O panda gitlink: 92eb565169fd553f4dfaf508c1a3f8dbc14fbfbf.
C opendbc는 vendored tree 755cca52c9247ec0877b3fca58a9c74c3f9b2e33,
panda는 vendored tree 76cb122abc0132fbae08cb3920ea53cafcf19f33이다.
tree ID는 독립 저장소 commit이 아니다. root submodule은 초기화하지 않았다.
OP opendbc는 Step 3의 별도 reference object DB에서 읽었다.

Carrot 저장소 root와 vendored opendbc root에서 LICENSE/ LICENSE.md entry가
확인되지 않았다. 이것만으로 모든 파일의 license가 없다고 단정하지 않는다.
특정 코드를 이식하려면 파일별 upstream 유래, 저작권과 이용 허락을 확인해야 한다.
현재는 **코드 이식 차단 조건**이며 개념 설계와 source-pointer 분석을 먼저 남긴다.

소스 확인은 `git show <SHA>:<path>`, 실제 caller, AST read/write inventory로
했다. [파라미터 해설](cyberpilot/analysis/CARROT_LONG_PARAMETERS.md)과
[기계 판독 inventory](cyberpilot/analysis/CARROT_LONG_SOURCE_INVENTORY.json)는
108개 Python 파일, 추가 4개 schema/config 파일의 정확한 blob과 line을 기록한다.
AST는 호출 경로 분석의 보조 수단이지 동작 증명이 아니다. 저장 장치 Params 실제값,
차량 firmware 상태, 모든 safety 구현과 모든 런타임 분기는 검증하지 않았다.

**“실제 효과”의 증거 수준:** 코드에 기능이 있다는 것은 효과가 입증됐다는 뜻이
아니다. 이번 분석에는 동일 입력 baseline replay, closed-loop 실험, shadow 데이터가
없다. 모든 Carrot-derived 성능 개선은 가설이며 효과 확인 전 활성화하지 않는다.

## 2. Current openpilot longitudinal data flow

아래 O 경로는 repository root 기준이며 모두 O SHA에 고정된다.

```text
camera / model inference
  modeld.get_action_from_model
    ├─ model action 또는 plan sampling → desiredAcceleration
    └─ should_stop 판정 → acceleration smoothing → modelV2.action
vehicle radar / vision leads → radard → radarState.leadOne/leadTwo
car CAN → card / upstream VCruiseHelper → carState.vCruise
driver monitoring / events / mode → controlsState.forceDecel, selfdriveState
  ↓
plannerd (modelV2 update)
  LongitudinalPlanner
    ├─ lead-only LongitudinalMpc → delayed MPC acceleration / should_stop
    ├─ get_cruise_accel → speed error, accel/jerk, turn/coast constraints
    └─ experimentalMode에서만 modelV2.action
    → min(acceleration candidates); OR(candidate shouldStop)
    → global accel clipping → longitudinalPlan.aTarget / shouldStop
  ↓
controlsd: enabled + override events + CP.openpilotLongitudinalControl
  CI.get_pid_accel_limits → LongControl → actuators.accel
  ↓
card: CI.apply → pinned opendbc vehicle controller → CAN packing → sendcan
  ↓
panda safety enforcement → vehicle actuator → carState.aEgo / vEgo
```

정확한 파일: `openpilot/selfdrive/modeld/modeld.py`,
`controls/plannerd.py`, `controls/radard.py`,
`controls/lib/longitudinal_planner.py`,
`controls/lib/longitudinal_mpc_lib/long_mpc.py`,
`controls/lib/drive_helpers.py`, `controls/lib/longcontrol.py`,
`controls/controlsd.py`, `car/card.py`, `car/cruise.py`
(controls/car 약칭은 `openpilot/selfdrive/` 기준).
차량 소비자는 OD `opendbc/car/interfaces.py`와 해당 차량 controller/CAN 파일이다.

유지해야 할 실제 계약:

- model action의 stop 판정은 acceleration smoothing 전에 계산된다.
- 현재 MPC에는 lead obstacle 두 개가 있고 cruise/traffic stop obstacle은 없다.
- cruise는 별도 가속도 후보다. turn combined-accel 제한, model throttle probability,
  pitch-based coast와 jerk smoothing을 유지한다. forceDecel이면 cruise speed는 0이다.
- 실험 모드에서만 모델 acceleration/stop 후보를 추가한다.
- 최종 acceleration은 가장 작은 후보, shouldStop은 **승자뿐 아니라 모든 후보의 OR**다.
  둘을 하나의 winner 상태로 합치지 않는다.
- action sampling은 CP.longitudinalActuatorDelay + DT_MDL을 사용한다.
  CP를 무시하는 전역 Params delay를 도입하지 않는다.
- publish의 speeds/accels/jerks는 MPC trajectory다. 최종 aTarget은 cruise 또는
  model 후보일 수 있다. trajectory를 최종 actuator target이라고 가정하지 않는다.
- 현재 LongControl은 off/stopping/pid 상태와 **acceleration error**
  aTarget - aEgo를 사용한다. Kp=0, CP Ki, feedforward를 보존한다.
  Carrot의 speed-error PID와 starting 상태를 섞지 않는다.
- should_stop의 현재 저속 기준은 vEgo < 0.3 m/s, aTarget < 0.1 m/s².
  stopping ramp는 1.0 m/s³로 CP.stopAccel을 향한다. 이들은 새 튜닝값이 아니다.
- stock resume은 enabled, cruise standstill, !shouldStop에 연결된다. signal hint는
  이 비트를 clear하거나 resume/engagement 명령을 만들 수 없다.
- OD global accel envelope는 [-3.5, 2.0] m/s²이나 차량별 CI/CAN/safety의 제한이
  별도로 존재한다. 이 global 값만으로 모든 차량의 허용 범위를 판단하지 않는다.

## 3. Carrot longitudinal data flow — actual callers

C 경로는 `selfdrive/` 및 `opendbc_repo/opendbc/car/` 기준이다.
line anchor는 source inventory에 고정되어 있다.

```text
modeld → modelV2.position/velocity/acceleration + leadsV3 + meta
CAN radar → card.liveTracks → RadarD / VisionTrack → radarState.leadOne/Two
CAN/buttons/brake/gas + Params + external CarrotManCommand
  → card.VCruiseCarrot.update_v_cruise
  → vCruise, softHoldActive, activateCruise, latEnabled
  → CarSpecificEvents → buttonEnable/buttonCancel/softHold events → selfdrived
external UDP/nav/route/DETECT + model curve
  → CarrotMan / CarrotServ → carrotMan.desiredSpeed, trafficState, atcType
  ↓
plannerd → LongitudinalPlanner.update
  → CarrotPlanner.update
      driving mode / gap / accel tables / filtered model stop
      traffic state + lead + gas/brake + soft hold → XState
      → v_cruise, stop_dist, comfort_brake, mode
  → legacy LongitudinalMpc
      lead0 + lead1 + cruise obstacle + virtual stop obstacle (ACC)
      OR blended model plan (experimental / prepare path)
      t_follow, comfort brake, stop distance → solver → x/v/a/j trajectories
  → Params LongActuatorDelay sampling → aTarget, vTarget, jTarget, shouldStop
  ↓
controlsd → LongControl (speed-error PID + stop/start/soft hold)
  → accel + aTargetNow + jerks[0]
  → card.CI.apply → per-brand conversion / jerk / hold / stock-ACC buttons
  → CAN → panda → vehicle
```

### 3.1 Lead, cut-in, follow distance

`radard.py` Track.update (68), match_vision_to_track (143), VisionTrack.update
(337), RadarD.update (414), RadarD.get_lead (490)에서 radar/vision을 조합한다.
거리 tolerance max(0.35 × vision distance, 5 m), 높은 model probability에서
velocity tolerance 증가, track reset 및 acceleration filtering이 있다.
RadarReactionFactor는 Track 생성 시 읽혀 lead acceleration tau에 영향을 준다.
VisionTrack은 model velocity와 거리차분 velocity를 결합하고 가속도를 필터링한다.

실제 leadOne/Two 호출은 **low_speed_override=False**다. 존재하는
potential_low_speed_lead helper가 활성화된 저속 개선이라고 보고하지 않는다.
leadLeft/Right/Center 목록도 publish하지만 MPC는 leadOne/Two만 소비한다.
주석 처리된 SCC-only cut-in fallback은 현재 활성 로직이 아니다.
따라서 **독립적인 predictive cut-in 기능 또는 효과가 입증된 cut-in 개선은
확인되지 않았다**. 연관된 fusion, lead jump 반응, follow 조절은 각각 실험 대상이다.

CarrotPlanner.get_T_FOLLOW (157)는 실제 Params gap1..4를 personality에
매핑한다. dynamic_t_follow (177)는 lane-change desire > 0.9이면 LC multiplier,
그 외 lead가 있으면 거리 error × DynamicTFollow를 [-0.1, 1.0] s로 clip해 더한다.
LC multiplier가 작으면 gap을 줄일 수 있다. lane-change 의도는 cut-in 관측과
동일하지 않다. 이 방법을 Cyber의 cut-in 예측이라고 이름 붙이지 않는다.

MPC process_lead (318)는 status, dRel, vLead, **aLead**와 aLeadTau를 사용한다.
최신 O의 present/aLeadK 계약과 다르다. lead를 정지 등가 장애물로 변환한 뒤
v²/(2b) + tFollow·v + stopDistance 형태의 거리 제약을 둔다.
lead 정지등가 계산과 desired_distance helper의 b/stopDistance는 fixed 값인데,
실제 solver 제약에는 Carrot comfort_brake/stop_distance가 들어갈 수 있다.
동일한 “desired distance” 표시라도 제약과 정확히 같다고 가정하지 않는다.

### 3.2 Stop, start, low speed

CarrotPlanner.check_model_stopping (194)는 마지막 model x/v/y와 lead distance로
정지/출발 징후를 판정한다. red는 양의 stopSign duration 즉시, green은 startSign
0.2 s 초과다. 82 km/h 이하, model endpoint/lead 상대거리/velocity/y 조건이 있으며
이는 traffic-light detector 자체가 아니다. stop filter는 median(3) + moving
average(15), endpoint velocity average(10); planner DT_MDL 기준으로 움직인다.

CarrotPlanner.update (265)의 XState는 lead/cruise/e2eCruise/e2eStop/
e2ePrepare/e2eStopped. gas/brake, soft hold, 외부 traffic state 및 model heuristic이
상태를 바꾼다. 정지거리 적분, v²/(2 comfortBrake) 하한, 정지 전 0.9 comfort
factor와 속도 의존 stop-distance 축소가 연결된다. stopped hold count 0.5 s,
gas 뒤 stop 판단 유예 10 s, prepare 저속 조건 5 km/h 등도 별도 정책이다.
user_stop_distance 변수의 갱신 분기는 있으나 현재 호출 경로에 양의 값을 공급하는
활성 producer는 확인되지 않았다. 존재만으로 운전자 수동 정지 기능이라 단정하지 않는다.

LongControl.long_control_state_trans (14)/update (69)는 off/stopping/starting/pid,
CP.startingState/startAccel/vEgoStarting, StoppingAccel override, CP stopping
rate, softHold를 조합한다. PID error는 vTargetNow-vEgo, feedforward는 aTarget.
jerk 소비값은 interpolation된 미래 jTarget이 아니라 trajectory **jerks[0]**다.
이 state machine과 가속도/속도 PID 의미를 최신 O에 복사하지 않는다.

### 3.3 Acceleration, deceleration, jerk, cruise

CarrotPlanner._params_update (117)/get_carrot_accel (152)는 0/40/60/80/110/
140 km/h 구간의 accel table을 driving mode factor와 곱한다.
eco=0.9, safe=0.8, high=1.2는 fixed factors. “safe”라는 이름이 safety 보장은 아니다.
cruise_eco_control (244)는 일부 조건에서 설정속도보다 4 km/h 높은 목표를 만든다.
Cyber는 사용자 설정속도를 자동으로 높이는 이 정책을 채택하지 않는다.

legacy planner는 A_CRUISE_MIN=-2.0 m/s², turn combined accel table, coast/throttle
로직을 MPC와 함께 사용한다. ACC mode에서 allow_throttle 조건은 mode=='acc'로
참이 될 수 있다. 최신 O throttle/coast 제약을 이 경로로 덮어쓰지 않는다.
C vendored interfaces의 global envelope는 [-4.0, 2.5] m/s²로 O보다 넓다.
이 값과 차량 safety/CAN 변경은 **채택하지 않는다**.

MPC set_weights (288)는 ACC에서 obstacle/acceleration-change/jerk cost,
blended에서 x/v/a reference cost를 쓴다. jerk factor는 aggressive=0.5,
나머지=1.0. 제약 penalty와 jerk cost는 hard jerk guarantee가 아니다.
MPC.update (347) 내부 local mode가 Carrot prepare 상태로 바뀌는 반면 cost와
일부 후처리는 self.mode를 사용한다. 이 경로의 일관성은 regression 확인 대상이다.

Carrot planner.publish는 carState/controlsState/selfdriveState의 check subset을
valid 판정에 쓰며, 현재 O는 sm.all_checks()를 쓴다. Cyber는 이를 좁히지 않는다.
모델/radar/provider 상태를 message alive 또는 정상 shape만으로 대체하지 않는다.

VCruiseCarrot._auto_speed_up (520), _update_cruise_state (573),
_prepare_brake_gas (642), _carrot_command (385)는 road-limit set-speed 변경,
gas/brake release, soft hold, lead/traffic 상황으로 activation과 cruise를 변경한다.
card가 activateCruise를 전달하고 car_specific.py에서 enable/cancel event로
바꾸며 Hyundai/GM controller의 버튼 전송까지 연결된다.
이는 comfort planner가 아니라 **driver/actuator authority**이므로 제외한다.

### 3.4 Curves, navigation, traffic signals

CarrotMan.broadcast_version_info (237) → carrot_curve_speed (713) →
vturn_speed (751) → CarrotServ.update_navi (1282) → desiredSpeed.
현재 carrot_curve_speed는 vturn_speed를 먼저 return하므로 아래 legacy model-curve
lookup 경로는 unreachable이다. 그러나 **route curvature**에서는 같은 lookup table을
carrot_navi_route (295)가 실제 사용한다. 두 경로를 혼동하지 않는다.

model curve는 orientationRate.z × velocity.x로 예측 lateral acceleration을 만들고,
현재 vEgo²로 curvature proxy를 나눈다. target lateral accel은 1.9 m/s² ×
aggressiveness, speed는 sqrt(target/curvature)이며 factor/min-speed와 방향 부호가
붙는다. 이것은 직접 model curvature와 동일한 추정량이 아니다.
zero curvature, shape mismatch, finite와 입력 freshness 처리가 별도 필요하다.

route 경로는 Shapely/활성 nav, 약 300 m 구간, 10 m resampling, 3점 curvature,
speed lookup, 역방향 decel propagation을 사용한다. 실제 code와 단위는 inventory
원본을 참조한다. model curve의 dead legacy lookup과 달리 route lookup은 활성이다.
SDI/bump/section, TBT 현재/다음 turn, model curve, route curve 중 minimum speed를
선택한다. gas override가 이 목표를 올릴 수 있다. desiredSpeed=250/300 km/h 같은
센티널을 일반 목표속도로 취급해서는 안 된다.

traffic_light (947)는 외부 DETECT 명령의 color/x/y/confidence와 최근 queue를
비교해 red/green/left state를 만든다. openpilot camera 자체의 신호 인식 출력이라고
보고하지 않는다. TTL은 service tick, packet/provider activity와 message alive는
다르다. update_navi가 msg.valid=True를 publish하는 것만으로 각 외부 데이터의
유효성이 입증되지 않는다. CarrotPlanner._update_carrot_man (217)의 alive 기반
red→green/left 전이는 stop 해제에 연결된다. **초기 Cyber는 이 입력으로 출발하지 않는다.**

carrot_staty_stop와 carrot_stay_stop 이름 불일치, model 짧은 배열 x[31] 접근,
delay=0 설정에서 division 가능성, 필터/상태 재사용은 정적 위험 지점이다.
실제 재현이나 사고/성능 결과를 확인한 것은 아니다.
CarrotMan의 remote command, 업로드/기기 관리, set_time/route network service는
navigation hint 개념과 분리하고 이식하지 않는다.

### 3.5 Actuator delay, vehicle parameters, compensation

planner get_accel_from_plan (55)는 Params LongActuatorDelay × 0.01을 읽는다.
Hyundai CP.longitudinalActuatorDelay=0.5 s와 manager default 0.2 s가 다를 수 있다.
실차 Params는 미확인이다. 전역값을 “정확한 차량 delay”라고 단정하지 않는다.

base interfaces → platform-specific _get_params → controller → CAN 함수로 추적했다.
13 brand의 interface/controller/state/radar/values/CAN 파일은 inventory에 있다.
body/mock도 포함하지만 그 분석을 passenger-car 실차 적합성으로 세지 않는다.

- Hyundai: interface flags/radar enable → safety config/OP longitudinal capability,
  controller accel clip → HyundaiJerk → hyundaican/hyundaicanfd.
  jerk/comfort-band 값은 CAN protocol 역할도 있다. soft_hold_mode는 실제로
  AutoCruiseControl에서 파생되고 SoftHoldMode key를 읽는 경로는 못 찾았다.
  EnableRadarTracks는 초기화 시 UDS WRITE 경로도 갖는다. 어떠한 장치 작업도 안 했다.
- Toyota: CarController.get_long_tune + 별도 local PID, pitch feedforward,
  accel winding limits, filtered aEgo/GVC와 future error, permit_braking hysteresis,
  clipping → toyotacan.create_accel_command. planner PID와 별개의 actuator 보상이다.
- GM: LongPitch, EVTable → pitch-based gas/brake compensation, speed-dependent EV
  gas/brake lookup, regen, stop/near-stop, interceptor/stock-resume branches → gmcan.
  EVTable은 interface 초기 설정과 controller runtime 양쪽에서 읽힌다.
- 기타 brand: mass/wheelbase/speed calibration, accel/PID/delay/stop capabilities,
  gas/brake table/actuator protocol은 platform 조건식과 함께 inventory에 기록한다.
  한 차량의 calibration을 global control 값으로 승격하지 않는다.

모든 protocol/safety/capability/stock-ACC/ECU configuration은 원래 O pin을 유지한다.
이 문서는 전체 panda firmware나 CAN 허용 frame의 안전 감사를 대신하지 않는다.

## 4. 파라미터 분류와 metadata 계약

분류는 배타적이지 않다. 1 차량 물리, 2 제어기, 3 취향, 4 안전 제한/권한,
5 상황 적응, 6 AutoTune 연구 후보, 7 AutoTune 금지.
4에는 safety enforcement뿐 아니라 engagement/신뢰/거리 envelope에 결합된 값도
포함한다. comfort라고 이름 붙었다고 자동 변경 대상이 되지 않는다.

146개 발견 key의 manager default, UI metadata, 실제 read/write file/line,
cadence, 단위/scale, 분류와 금지를 [catalog](cyberpilot/analysis/CARROT_LONG_PARAMETERS.md)에
기록한다. 고정 상수, CP/vehicle tables, 상태 적응값도 별도 분류했다.
UI 범위는 검증된 bounds가 아니며 기존 장치값이나 manager default와 같지 않다.

제안 registry의 각 항목:

```text
name, unit(SI), source(repo/branch/commit/path/blob), source_scale
default(stock baseline), vehicle_specific, vehicle_firmware_binding
category[], owner, update_policy
online_learn_allowed, offline_tune_allowed, enabled
min, max, rate_of_change_limit, confidence_requirement
validity_range, configuration_epoch, evidence_id, rollback_target
```

초기값은 stock 동일, AutoTune enabled=false.
검토되지 않은 min/max/confidence는 null/미정이며 **무제한이 아니라 사용 금지**다.
안전 제한/모델/flags/CAN/engagement/DM/driver takeover는 writable registry에
넣지 않는다. 승인된 safety envelope는 읽기 전용 snapshot으로만 참조한다.

사용자 personality/headway/comfort 선택과 vehicle delay/gain 식별을 분리한다.
오프라인 delay/gain 식별 후보는 실제 downstream controller에 맞는 단위와
차량/firmware/모델 binding 및 bounds를 심사한 후에만 허용한다.
기존 speed-error Kp를 current acceleration-error controller에 그대로 넣지 않는다.
RadarReactionFactor는 estimator 연구 후보일 뿐 planner AutoTune hook으로 연결하지 않는다.

## 5. Architecture 후보와 선정

| 후보 | 장점 | 비용/위험 | 결론 |
| --- | --- | --- | --- |
| 1. upstream planner + isolated policy/candidate seam | model/MPC/LoC/CAN 보존, 작은 diff, default-off parity 측정 가능 | 추가 후보도 강한 제동·delay/jerk/state 위험; explicit binding 필요 | **권장** |
| 2. Carrot virtual-stop/ACC/blended MPC port | Carrot 상태와 tuning을 직접 재현 가능 | solver dimension/cost/schema/LoC 계약 회귀, 큰 merge 충돌, 효과 미입증 | 제외 |
| 3. LoC 이후 actuator/CAN post-filter | planner 변경이 작아 보임 | planner trajectory/stop/FCW와 actuator 불일치, anti-windup 및 vehicle/safety 결합 | 제외 |

권장은 서로 다른 controller 출력 평균이나 modes의 빈번한 switching이 아니다.
최신 openpilot을 **단일 core**로 유지하고 독립 정책이 선택적으로 constraint
candidate를 제안한다. 상위 계획 단계에서 제약을 명시해야 downstream delay,
integrator, stop state 및 clipping 계약을 유지하기 쉽다.

## 6. Cyber Long proposed flow

```text
unchanged modeld / radard / VCruiseHelper / events / vehicle CP
  ↓
unchanged stock lead MPC + cruise + optional model candidates
  ├─ immutable stock context + validated config snapshot
  │    → CyberLongPolicy (default disabled; no external IO)
  │       ├─ follow diagnostics (stock personality)
  │       ├─ stop/start diagnostics (stock state/intent only)
  │       └─ future evidence-qualified comfort/speed cap candidate
  └─ stock candidate list
       + valid optional Cyber candidate
       → existing min-selection + original stop OR + existing clips
       → unchanged longitudinalPlan contract
  ↓
unchanged LongControl / controlsd / CI / CAN / panda
  ↓
observations → offline validation / separate non-actuating shadow comparator
```

### 6.1 Interface와 책임

- Context: monotonic model/radar/carState identity, CP/vehicle/firmware/model binding,
  vEgo/aEgo/vCruise, stock candidate accelerations/stop bits, forceDecel, personality,
  model throttle/curve observations, enabled/reset state, read-only limits.
  입력은 immutable. policy가 sm/Params/CP/stock candidate를 mutate하지 않는다.
- Output: None 또는 Candidate(accel_mps2, config_epoch, input_identity,
  reason, evidence_id). initial phase에는 diagnostic만 있고 실제 candidate는 None.
  no steer/gas/brake/CAN, no engage/resume/cancel, no positive-release request.
- State: policy-owned previous comfort reference만 선택적 보유. off, brake/cancel/
  override, stock reset, input stale/gap, vehicle/config epoch 변경, clock reversal,
  invalid/non-finite 입력이면 state reset + None. 다음 fresh stock cycle부터 재시작.
- Safety fallback: valid baseline이 있으면 **그 cycle의 stock output**으로 복귀한다.
  baseline 자체가 invalid면 stock fault/engagement 경로를 유지하며 오래된 stock
  또는 candidate를 valid인 것처럼 publish하지 않는다. last candidate hold 금지.
- Hot path에서 Params/network/file IO 금지. 한 cycle에 단일 검증된 config snapshot.
  부분 업데이트를 mixing하지 않고 reject/rollback은 진단에 기록한다.

### 6.2 Planner integration과 arbitration 불변식

예상 seam은 LongitudinalPlanner.update에서 **stock candidates 생성 뒤, 기존
min/OR/clipping과 state feedback 전**이다. post-control smoothing을 추가하지 않는다.

1. disabled 및 Phase A 관찰 모드는 stock 후보, stop bits, state, outputs를 그대로
   통과시킨다. adapter 실행으로 baseline float 계산 순서까지 바꾸지 않는다.
2. 선택적 comfort 후보는 stock cruise 제한/turn/throttle/coast/forceDecel을 완화하지
   않고 생성한다. 이미 더 작은 lead/model 후보를 높일 수 없다.
3. final aTarget <= stock aTarget이어도 **더 안전하다는 증명은 아니다**.
   과도한 감속/rear-end risk, low-speed stall, state feedback/jerk 증가를 검사한다.
4. baseline lead hard braking을 comfort jerk 제한 때문에 늦추거나 줄이지 않는다.
   comfort transition shaping은 **자기 후보**에만 적용한다.
5. initial candidate 권한은 baseline shouldStop을 clear/set하거나 resume를 바꾸지
   않는다. candidate가 upstream should_stop 결과를 새로 true로 만드는 저속 구간은
   후보를 reject하여 stock으로 간다. stop 정책 변경은 별도 설계/승인 항목이다.
6. 기존 global final clip와 CI/CAN/safety limit를 그대로 둔다. candidate가 clipped
   envelope 안에 있다는 것만으로 jerk나 차량 적합성을 보장하지 않는다.
7. speeds/accels/jerks는 기존 MPC 의미를 유지한다. candidate trace는 별도로 남긴다.
   필요한 source는 stock cruise 의미 안의 cap으로 표현하고 cap reason을 진단에
   기록한다. 새로운 stock enum 의미를 임의 재정의하지 않는다. 별도 live schema
   필요 시 cereal custom-fork 절차/old-log 검토를 별도 승인한다.
8. extra candidate가 MPC 초기 a feedback을 바꾸므로 다음 cycle에도 영향을 준다.
   replay + closed-loop regression에서 이 coupling을 반드시 검사한다.

**Follow extension 경계:** initial Phase A는 stock MPC personality/gap을 쓴다.
policy 인터페이스에 headway라는 필드를 만든다고 실제 lead constraint가 바뀌는 것이
아니다. dynamic headway를 채택하려면 LongitudinalMpc.update/set_weights의 작은
explicit policy API와 bounds/거리 일관성 검증이 **별도 필요**하다.
이번 권장 초기 버전은 MPC 변경 없이 baseline follow를 유지한다.

**Curve/navigation 경계:** Phase B 뒤의 선택 기능이다. authenticated/validated,
timestamped SI speed hint만 입력받고 stock speed보다 높일 수 없다. provider-invalid,
route jump/zero curvature/shape mismatch, uncertainty가 높으면 None.
traffic signal/remote command를 이 adapter에 multiplex하지 않는다.

### 6.3 Future AutoTune interface

AutoTune는 actuator caller가 아니라 validated parameter candidate의 producer다.
오프라인 artifact → schema/unit/range/binding/confidence 검사 → human approval →
immutable registry snapshot → policy consumer 순서다. initial adapter는 disabled다.

vehicle physical(delay 추정 등), controller, user preference를 다른 namespace로 둔다.
세션 도중 raw gain/delay 급변을 금지한다. 초기에는 inactive boundary에서만 snapshot
교체를 제안하고 later online learning은 별도 승인한다.
안전 envelope와 신뢰/acceptance 기준은 optimizer가 변경할 수 없다.
CP/CAN/panda에 registry write-back을 만들지 않는다.

## 7. 적용 후보와 제외 기능

| 기능 | 초기 Cyber Long | 이후 조건 |
| --- | --- | --- |
| stock follow + stop/start + acceleration pipeline | Phase A 그대로 유지, 관찰/parity 먼저 | upstream regression 기준 유지 |
| Carrot 속도별 comfort accel envelope | 개념만 재작성 후보, 초기 disabled | envelope/jerk/lead priority closed-loop 근거 |
| lead/gap/stop reason 분리 관찰 | 독립 진단 설계에 활용 | stock state가 truth, Carrot enum 복제 안 함 |
| dynamic follow/cut-in 대응 | diagnostics/offline 연구만 | actual cut-in dataset, headway/거리 제약 별도 승인 |
| model curve/route speed cap | 초기 제외, future hint contract만 | source freshness/geometry/법규/vehicle 검증 |
| global LongActuatorDelay 및 speed PID gain override | 제외 | 차량별 offline 식별과 current controller 단위 재설계 |
| Carrot model virtual stop / signal auto-start | 제외 | 이 설계로 stop authority 부여하지 않음 |
| eco 설정속도 +4 km/h / 자동 mode 전환 | 제외 | driver intent 보존 |
| AutoCruise/softHold/remote cruise commands/button spam | 제외 | 별도 authority/safety 검토 없이는 이식 안 함 |
| widened accel limits / safety flags / radar UDS / DM bypass | 금지 | AutoTune/성능 개선 대상으로 사용 안 함 |
| Toyota/GM/Hyundai CAN compensation, jerk/hold 코드 | initial 제외 | 최신 upstream pin 유지, brand별 별도 evidence/허가 필요 |
| full Carrot planner/MPC/CarrotMan service | 제외 | 전체 merge/clone 없음 |

Step 3의 A(기존 upstream 활용), B(개념 재구현), C(미채택) 구분을 유지한다.
Carrot 효과가 확인됐다는 가정을 Phase B 진입 근거로 쓰지 않는다.

## 8. 수정 예상 파일, 새 모듈, upstream merge 위험

아래는 **구현 승인 후의 예상 위치**이며 이번에는 만들거나 수정하지 않는다.

| 위치 | 계획 | merge 위험 |
| --- | --- | --- |
| openpilot/selfdrive/controls/lib/longitudinal_planner.py | isolated object 초기화, candidate seam, minimal stock context | 중간~높음: upstream arbitration/reset 변경 시 seam 재검토 |
| openpilot/selfdrive/controls/lib/cyber_long/policy.py | pure policy, reset/fallback, candidate validation | 낮음: independent 모듈이나 계약 drift 가능 |
| openpilot/selfdrive/controls/lib/cyber_long/params.py | central metadata, immutable snapshots, user/vehicle 구분 | 낮음~중간: CP/model binding 변화 |
| openpilot/selfdrive/controls/lib/cyber_long/types.py | context/candidate/diagnostic contracts | 낮음: stock schema를 복제하지 않음 |
| openpilot/selfdrive/controls/tests/test_cyber_long.py | contract/parity/optional-policy regressions | 낮음~중간: baseline 변경을 명시 반영 |
| docs/cyberpilot/changes/ | 승인 기능별 source/effect/risk/validation 기록 | 낮음 |
| longitudinal_mpc_lib/long_mpc.py | 초기 **변경 없음** | future headway API는 높은 위험, 별도 승인 |
| longcontrol.py/controlsd.py/card.py/cruise.py/modeld/ | **변경 없음** | 최신 core 유지 |
| cereal / opendbc_repo / panda / device Params | **변경 없음** | authority 및 compatibility 보호 |

새 daemon, manager process, persistent branch, speculative empty module을 추가하지 않는다.
향후 이름/위치는 implementation 직전 실제 패키지를 다시 읽고 확정한다.
feature/cyber-long은 당시 develop/기존 변경 상태를 확인해 base를 선택한다.
현재는 develop에서 문서만 남긴다. shared history force push는 금지다.

## 9. 단계별 구현/검증 계획 — 이번에는 실행 안 함

### Phase A: baseline-compatible connection

planner/control 연결은 기존 message/LoC를 재사용한다. follow/stop/start/accel/decel는
stock behavior 재현이다. policy default disabled + enabled-observation-only 모두
동일 출력과 stock state를 재현한 다음에만 별도 기능을 제안한다.
Carrot 전체 이식이나 자동 signal stop/start를 “최소 기능”에 포함하지 않는다.

### Phase B: evidence-qualified comfort / cut-in

comfort accel shape부터 단일 기능씩 feature record/승인/baseline 확보 후 재작성한다.
cut-in은 현재 “효과 확인된 기능”이 없으므로 자동 구현 항목이 아니다.
association jump, true cut-in/out, lead loss, low-probability false lead를 분리해
개선 가설을 검증하고 필요하면 headway API 설계를 다시 승인받는다.
lead emergency braking과 throttle/curve/forceDecel를 손상시키면 채택하지 않는다.

### Phase C: non-actuating AutoTune hooks

metadata validation/vehicle binding/rollback/diagnostics부터 넣는다.
tuning engine나 online write-back을 이 단계 이름만으로 승인하지 않는다.
null bounds, invalid/stale artifact, wrong vehicle/firmware, low confidence는 reject.
user headway나 safety envelope 자동 수정 금지.

### 검증 matrix

| 층 | 시나리오/측정 | 합격 조건 및 한계 |
| --- | --- | --- |
| static / contract | units, finite/shape, identity, config epoch, freshness, reset, no external IO | invalid → fresh stock fallback; no authority write |
| parity unit | disabled, observation-only, all modes, every stock candidate winner/tie, stop OR | control outputs/state parity; timestamp/진단 차이는 사전 명시 |
| policy unit | bounds, emergency lead, own jerk transitions, zero delay, stale/clock reset, brake/cancel | no uplift/no new stop/resume, limits 보존; lower a≠safety 증명 |
| upstream unit | controls tests; longitudinal_maneuvers default class combinations | 기존 tests/acceptance/refs 변경 없이 검증 |
| process replay | plannerd/controlsd/radard, lead jumps/cut-in/out, stop-go, model stop false positives | fixed logs/code/model/config identity; parity 또는 승인된 diff |
| closed-loop | lead brake, stopped lead, cut-in, slope/curve, delay/gain/regen uncertainty, loss faults | collision/min distance/TTC/response/jerk/stop-go regression 검토 |
| shadow | active=upstream, candidate isolated from actuators, synchronized identities | non-actuating provenance proof; device 작업 별도 승인 |

필수 metric: v/a tracking error, accel extrema, jerk RMS/percentiles/max,
lead-response latency, min dRel/TTC (closing-v 조건과 undefined 구간 명시),
headway/stop-distance error, stop overshoot, stop dwell/restart delay,
saturation/clipping duration, forceDecel/throttle/override/engagement mismatch,
source/state transitions, candidate reject/fallback 및 stale counts.
comfort 개선을 위해 collision/headway/hard-braking gate를 완화하지 않는다.

각 metric의 수치 threshold와 dataset는 승인된 baseline/vehicle envelope에서
**실험 전에 고정**한다. 아직 입력/vehicle/수치 acceptance가 없으므로 성능 합격
조건은 미충족이다. holdout/훈련 분리, 동일 code/model/input/config provenance,
row counts와 exit code를 기록하고 단순 aggregate로 위험 사례를 숨기지 않는다.

지원 환경: tools/README.md의 Ubuntu 24.04/필요 시 Windows WSL, exact gitlinks,
LFS 모델 자산, Python/native dependencies 확인 → scons -u.
예정 명령은 현재 checkout에서 존재/인자를 확인했지만 실행하지 않았다:

```bash
python tools/test_runner.py openpilot/selfdrive/controls/tests
python tools/test_runner.py openpilot/selfdrive/test/longitudinal_maneuvers/test_longitudinal.py
python openpilot/selfdrive/test/process_replay/test_processes.py --whitelist-procs plannerd controlsd radard
```

process replay/sim은 default runner discovery가 제외하므로 별도 실행해야 한다.
[replay README](../openpilot/selfdrive/test/process_replay/README.md),
[sim README](../openpilot/tools/sim/README.md)를 따른다. MetaDrive bridge만 켜는 것은
위 closed-loop longitudinal acceptance matrix를 실행한 것이 아니다.
--update-refs, test 삭제, ignore/threshold 확대, private logs 자동 commit은 금지다.
replay → closed-loop simulation → shadow 순서 뒤에도 실차/release 승인은 별도다.

## 10. 설계 승인 요청과 남은 입력

권장 승인 단위: **후보 1 구조 + Phase A baseline/관찰-only seam**, followed by
별도 근거를 가진 comfort 기능. Step 5 전에 다음을 확정해야 한다.

1. 최신 upstream fetch/rebase 필요성 및 새 SHA에서 seam 계약 변화.
2. Carrot-derived 적용 파일의 license/attribution.
3. 목표 차량/firmware/OP-long capability, 승인된 replay 입력과 model identity.
4. numeric bounds, metric acceptance, holdout 및 supported runtime 준비.
5. Phase B 기능별 효과 증거. cut-in/traffic/AutoTune 적용 범위는 자동 확장하지 않는다.

검토 결과를 [Step 4 검증 기록](cyberpilot/analysis/CYBER_LONG_DESIGN_VERIFICATION.md)에
남긴다. 이 문서는 Step 4의 static design deliverable이지 구현/성능/실차 안전 PASS가 아니다.
