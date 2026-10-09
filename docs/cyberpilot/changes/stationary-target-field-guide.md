# 정지 표적 calibration 현장 가이드

CALIBRATION_TOOL_READY / CALIBRATION_MEASUREMENT_PENDING.
독립 calibration·meter qualification·sealed reference·차량 활성화는 아직 불가합니다.

## 최소 준비: 관측 자료 수집

준비된 표적과 vehicle datum이 있다면 약 5–10분의 자료 수집을 목표로 합니다.
완전한 target-to-vehicle survey, distortion/intrinsics 검증까지 이 시간에 끝난다는 뜻은 아닙니다.
새 주행 데이터를 수집할 필요는 없습니다.

준비물: 줄자/레이저 거리계, 수평 확인 장치, 단단하고 평평한 표적 받침,
출력물 실제 치수 확인용 ruler/caliper, 필요하면 tripod/stand. 특정 제품 구매는 필요 없습니다.

1. 안전한 곳에 정지하고 차량/표적이 움직이지 않게 합니다. 평탄해 보인다는
   이유로 slope=0을 입력하지 않습니다. 수평 조사 근거와 conservative slope bound를 기록합니다.
2. local target sheet를 100%/actual size로 인쇄합니다. page-fit/축소 금지.
   nominal20mm square,8×6 squares,7×5 inner corners입니다. 실제 출력물을 재측정합니다.
   **width는 top-left~top-right 내부 corner 사이6칸, height는 top-left~bottom-left
   내부 corner 사이4칸의 실제 거리**입니다. 전체 종이 치수와 혼동하지 않습니다.
   가로/세로 scale 차이, 종이 휨, 설치 평탄도도 bound/evidence에 기록합니다.
3. ground → camera optical center의 수직 높이를3회 측정합니다. coarse1.40m를 복사하지 않습니다.
   min/max/spread는 도구가 계산하지만 absolute bound는 사람이 instrument·광학 중심 위치·
   수직 정렬·지면을 포함해 판단합니다. 줄자 눈금=설치 uncertainty가 아닙니다.
4. 표적 top-left 내부 corner를 target origin으로 잡습니다. 기존 surveyed vehicle datum:
   X forward / Y left / Z up 기준 위치를 실측합니다. 표적 x는 오른쪽, y는 아래, normal은 전방입니다.
   이 base에 대한 orientation은 Rz(yaw)Ry(pitch)Rx(roll), UI degrees → 저장 radians입니다.
   "앞에 세웠다"만으로 yaw를 알 수 없습니다. target 위치/roll/pitch/yaw 및 bound/방향
   근거가 없으면 draft만 저장하고 측정 완료로 처리하지 않습니다.
5. 확인된 comma4/mici narrow-road sensor, 원본 해상도 road-camera PNG와 hardware 근거를 준비합니다.
   screenshot/crop/resize/qcamera 이미지를 static intrinsics 해상도에 임의로 맞추지 않습니다.
   도구는 device에 접속하거나 영상/로그를 자동 탐색하지 않습니다.
6. 6개 실제 corner를 순서대로 클릭합니다: top-left, top-right, middle-left, middle-right,
   bottom-left, bottom-right. middle은5개 내부 corner row 중3번째입니다.
   자동 보간으로 관측점을 만들지 않습니다. 작은 화면 클릭 오차가 크면 큰 화면을 사용하고
   corner bound를 정직하게 기록합니다. 결과에 맞춰 bound를 통과시키지 않습니다.
7. local instrument/target/ground 사진·기록을 선택해 SHA를 얻고 해당 evidence field에 연결합니다.
   binary와 경로는 publication에 포함하지 않습니다.
8. Preview에서 residual/height/pose/conditioning을 확인하고 실제 관측 확인 후 immutable capture를
   저장합니다. draft는 수정 가능, final capture는 덮어쓰지 않습니다. 재측정은 새 capture입니다.

## 권장 강화: 서로 다른 정지 촬영3장

center / slight-left / slight-right의 **서로 다른 실제 이미지**를 권장합니다.
표적 이동마다 target-to-vehicle survey를 다시 기록합니다. 필요하면 다른 거리도 사용합니다.
동일 이미지를 복제해 반복 촬영으로 세지 않습니다. 반복 비교 거리/각도 bound와 근거는
결과 전에 정의합니다. 작은 residual/동일 fit만으로 planar ambiguity, intrinsics, distortion,
전체 physical uncertainty가 검증되지 않습니다.

## 실행

준비된 Ubuntu/WSL repository에서:

    .venv/bin/python -m openpilot.tools.cyber_autotune.stationary_target_ui

출력된 http://127.0.0.1:<port>를 같은 컴퓨터에서 엽니다.
responsive layout은 좁은 화면에서도 작동하지만 phone/LAN 접근을 위해0.0.0.0에 bind하지 않습니다.
기본 private workspace는 repository 밖에 생성됩니다. Ctrl-C로 종료합니다.
측정 sheet: /measurement-sheet. Private export: /export/local-captures.json.
Export를 GitHub에 올리지 않습니다.

## Admission은 별도

CALIBRATION_SOLVED는 **pinhole candidate fit**입니다.
STATIC_INTRINSICS_PRIOR / INTRINSICS_VALIDATION_PENDING / DISTORTION_UNVERIFIED,
단일 평면 ambiguity와 pose uncertainty pending을 유지합니다.
6개 corner로 intrinsics/distortion을 독립 검증하지 않습니다.

실제 survey·metrology review·undistortion residual·전체 uncertainty 근거를 갖춘 후에만
기존 physical_calibration_wizard / camera_calibration_evidence validator로 제출합니다.
Target candidate를 independent measurement JSON처럼 admission에 넣으면 거부됩니다.
기존 조건을 완화하지 않습니다. CALIBRATION_EVIDENCE_ADMITTED도 독립 validation 완료는 아닙니다.

Holdout은526×330입니다. calibration camera frame과 sensor/crop/resize mapping도 별도 검증해야 합니다.
다른 해상도 intrinsic matrix를 그대로 곱하지 않습니다. Model-derived orientation,
coarse height, assisted-human pixels는 독립 물리 calibration을 대체하지 않습니다.

NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED
