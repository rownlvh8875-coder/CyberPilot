# 차량 옆에서 사용하는 물리 calibration 측정 가이드

이 도구는 실제로 관측한 값과 근거를 기록합니다. 사진에서 각도를 추정하거나
modelV2/live calibration을 가져오지 않습니다. 저장을 마쳐도 독립 calibration
검증은 별도로 필요합니다. 모르는 값은 UNKNOWN / PENDING으로 남기세요.

현재 실제 측정은 없습니다. CALIBRATION_MEASUREMENT_PENDING /
INDEPENDENT_CALIBRATION_VALIDATION_PENDING입니다.
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.

## 시작과 준비물

저장소의 Linux/WSL 터미널에서 다음 한 명령으로 실행합니다.

~~~sh
.venv/bin/python -m openpilot.tools.cyber_autotune.physical_calibration_wizard_ui
~~~

표시된 http://127.0.0.1:포트 주소를 같은 컴퓨터 브라우저에서 여세요.
127.0.0.1만 지원합니다. 종료는 터미널에서 Ctrl-C입니다.
기본 저장 위치는 Linux 사용자 홈의 .local/share/cyberpilot-physical-calibration/
아래 새 session입니다. 다시 열 때는 같은 디렉터리를 --workspace로 명시합니다.
소스가 바뀌면 기존 session을 자동 이관하지 않습니다. 새 버전을 만드세요.

필요한 준비물은 사용하는 측정법에 따라 다릅니다. 줄자 또는 레이저 거리측정기,
독립 수평계/경사계, target 지지대, 출력 크기를 확인할 ruler/caliper,
측정 기록과 독립 metrology 검토 자료를 준비합니다. 특정 제품은 필요하지 않습니다.
폰 기울기 앱 값 하나나 눈대중으로 independent measurement를 대체하지 마세요.

차량을 정지시키고 측정 중 움직이지 않도록 합니다. ground reference와 datum을
독립적으로 survey할 수 있는 장소를 사용합니다. “주차장이 평평해 보임”은
측정 근거가 아닙니다. 이 wizard는 차량이나 comma4 로그에 연결하지 않습니다.

## A — 실제 device 확인

device family, hardware generation, 실제 sensor, narrow road camera role을 확인합니다.
해상도나 렌즈 모양만으로 sensor를 선택하지 마세요. 확인할 수 없으면 선택하지 않습니다.
unit ID와 operator ID는 이름/차량번호 대신 opaque ID로 기록할 수 있습니다.
hardware 확인 문서/사진은 G 단계에서 명시적으로 선택한 후 hash ID로 연결합니다.

static source 파일과 SHA가 화면에 보입니다. 실제 camera identity에 대응하는
pinned source 확인은 F 단계에서 수행합니다. source가 존재한다는 사실은
장치별 calibration이 검증됐다는 의미가 아닙니다.

## B — datum, 높이, mount X/Y

좌표는 오른손 좌표계이며 X 전방, Y 왼쪽, Z 위입니다.
원점은 기존 contract의 independently surveyed vehicle datum입니다.
원점을 실제로 어디에 정했는지와 optical center 위치를 기록하고 근거를 연결합니다.
차량 중심이나 bumper를 임의 원점으로 가정하지 마세요.

height_m은 관측한 ground plane에서 camera optical center까지의 수직 거리입니다.
렌즈 housing 끝, windshield edge까지의 거리가 아닙니다.
mount_x_m / mount_y_m은 같은 datum에서 optical center까지의 signed 위치입니다.
측정하지 않은 X/Y를 0으로 입력하지 마세요.

각 항목은 값, m 단위, positive conservative absolute uncertainty,
실제 method, instrument 종류/눈금, source/instrument/uncertainty evidence가 필요합니다.
줄자 눈금 1 mm가 전체 설치 uncertainty 1 mm를 의미하지 않습니다.
optical center 확인, 정렬, datum, ground, instrument 오차를 검토한 독립 bound를
사용자가 직접 입력해야 합니다. wizard가 bound를 결정하지 않습니다.

## C — pitch, roll, yaw

회전 convention은 Rz(yaw) Ry(pitch) Rx(roll)입니다. 내부 단위는 radians입니다.
degrees를 입력하면 원 입력값과 단위를 local package에 보존하고 radians로 변환합니다.
uncertainty도 같은 입력 단위를 선택하세요. 화면의 converted radians를 확인합니다.

+ yaw는 X 전방에서 Y 왼쪽, + pitch는 X 전방에서 아래,
+ roll은 Y 왼쪽에서 Z 위입니다. 카메라 optical axes에서 vehicle axes로의 변환을
기존 optical-frame convention과 함께 survey해야 합니다.
폰에서 표시하는 “pitch”를 이 convention의 pitch로 그대로 복사하지 마세요.

TIER A는 independently surveyed target/solution,
TIER B는 independently surveyed reference를 사용하는 독립 경사계/수평계 또는
독립 metrology 기록입니다. TIER C 폰 IMU/비공식 측정은 independent admission에
사용할 수 없습니다. instrument 종류, 단위와 tier가 일치해야 합니다.
단순 checkbox나 tier 선택으로 independent accuracy를 인증할 수 없습니다.

## D — stationary target와 survey 자료

실제 method를 선택합니다. SURVEYED_CHECKERBOARD, SURVEYED_APRILTAG,
SURVEYED_STATIONARY_TARGET은 독립적으로 측정한 target 실제 width/height/distance,
target-to-vehicle datum geometry, positive absolute bound, 사진과 survey 자료가 필요합니다.
개별 관측 항목에서 target method를 쓰는 경우에도 target 자료가 필요합니다.
OPTICAL_CENTER_SURVEY는 optical center 위치와 축을 직접 survey한 기록을 요구합니다.

Local printable sheet는 8 × 6 squares, nominal 20 mm square, 160 × 120 mm board,
7 × 5 inner corners와 nominal 100 mm control bar를 제공합니다.
100% / actual size로 출력하고 페이지 맞춤을 끕니다.
**인쇄 후 실제 크기를 ruler/caliper로 다시 측정하세요.**
명목 크기나 화면 pixel은 physical truth가 아닙니다. 실제 measured dimensions와
uncertainty가 없으면 target을 evidence로 사용할 수 없습니다.

AprilTag는 survey된 실제 tag/target geometry 자료를 사용합니다.
이 도구는 tag 생성기, pose solver, camera fit 도구가 아닙니다.
target 정렬·평탄도·거리·인쇄 변형·datum 연결 오차를 따로 검토해야 합니다.
여기서 실제 angle/height 값을 자동 생성하지 않습니다.

## E — ground와 distortion

ground survey method, observed slope bound, evidence를 기록합니다.
ground_vertical_m의 value=0은 surveyed datum 중심 정의입니다.
positive independent vertical approximation bound가 별도로 필요하며
“ground 오차가 0”이라는 선언이 아닙니다.

distortion은 기본 UNKNOWN / PENDING입니다. 임의의 k1=k2=0은 입력하지 않습니다.
기존 contract가 요구하는 independently bounded undistorted residual evidence가
있을 때만 해당 상태와 residual bound를 입력합니다.
distortion_residual_px value=0 역시 bound 중심 정의이며 zero distortion truth가 아닙니다.
fit/holdout/ground survey 자료가 없으면 draft만 저장하고 admission을 기다립니다.

## F — static intrinsics

실제 camera identity와 hardware evidence를 연결하고 pinned source를 확인합니다.
명시적으로 nominal source 사용 버튼을 눌렀을 때만 값이 form에 들어갑니다.
STATIC_SOURCE_INTRINSICS는 INDEPENDENTLY_MEASURED_INTRINSICS가 아닙니다.
nominal focal/principal point에도 독립 per-unit uncertainty 증거가 필요합니다.
source의 nominal 값으로 uncertainty나 distortion 검증을 대신하지 마세요.

## G — local evidence와 uncertainty

사용자가 만든 stationary measurement photo, target photo, instrument 기록,
survey note, metrology 검토 자료만 명시적으로 선택합니다.
private comma4 route images/raw logs를 선택하지 마세요.
선택된 binary는 repository 밖 local/private evidence 디렉터리에만 저장됩니다.
UI에는 filename-neutral opaque SHA, byte size가 표시됩니다. 이 SHA ID를 해당
source/instrument/uncertainty/ground/target 항목에 연결합니다.
파일 SHA는 무결성 근거이며 사진의 내용이 사실이라는 인증은 아닙니다.

METROLOGY_REVIEW는 실제 독립 검토 자료가 있다는 선언입니다.
검토를 아직 받지 않았다면 선택만으로 완료시키지 마세요.
unsupported units, missing/zero uncertainty, unknown methods와 model-derived source는
admission이 차단됩니다.

## H — preview와 제출

Draft 저장은 미완성 상태에서도 가능합니다. 새로고침/다시 열기로 복원합니다.
모든 관측값·단위·변환된 각도·bound·instrument·method·evidence hash를 preview에서 확인합니다.
실제로 물리 관측한 값이며 modelV2/live calibration에서 복사하지 않았음을
명시적으로 확인합니다. cameraOdometry/calibrationd/planner/candidate 출력도 금지입니다.

Preflight PASS는 구조와 선언한 provenance 검증입니다.
Immutable structural admission은 수정할 수 없는 local submission과 기존
authoritative admission receipt를 만듭니다. 이후 independent validation은 PENDING입니다.
잘못 입력했거나 재측정한 경우 새 session/version을 만들고 이전 receipt를 보존합니다.
중단된 admission은 기존 prepared package를 검증한 복구 버튼으로만 완료합니다.

Local/private submission export에는 실제 값과 원 입력, 근거 hash가 포함됩니다.
binary 증거는 같은 local evidence 폴더에 남으며 export JSON이 binary를 포함하지는 않습니다.
원 package와 evidence 폴더를 함께 보존하세요.
Public summary export는 hash/status allowlist만 포함합니다.
**실제 측정 package/사진/개인 파일 경로를 GitHub에 올리지 마세요.**
public summary도 자동 업로드되지 않습니다.

## 제출 후 필요한 것

CALIBRATION_EVIDENCE_ADMITTED는 INDEPENDENT_CALIBRATION_VALIDATED가 아닙니다.
실제 instrument/metrology 정확도, ground/distortion/target provenance,
projection uncertainty와 independent validation이 필요합니다.
sealed reference/차량 활성화가 자동 허용되지 않습니다.
blind reviewer, official CULane, ego association, road registration, desired-path,
private-domain validation blocker는 이 wizard와 별도로 남습니다.
