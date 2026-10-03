# 향후 수동 차량 평가 체크리스트

현재 상태: **REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED**.
이 문서는 평가 준비용이며 설치·활성화·도로주행 승인서가 아니다.
합성 PASS나 오프라인 리허설의 사용자 확인으로 활성화 차단을 해제하지 않는다.

## 적용 전에 충족할 조건

- 차량 fingerprint, firmware, source/model revision, 설정 및 정상 운용 브랜치를
  확인하고 복구 가능한 백업을 별도 보관한다. 개인 로그와 인증자료는 공개하지 않는다.
- 차량별 독립 기준값과 실제 plant의 유효 영역, 입력 단계, timestep 및 delay를
  검토한다. 합성 Hyundai CarParams fixture를 실제 차량 설정으로 사용하지 않는다.
- replay → 차량별 calibrated closed loop → non-actuating shadow 순서의 별도
  검토를 완료한다. 후보 출력이 actuator 경로에 연결되지 않았음을 확인한다.
- 현재 후보는 거부된 합성 실험이다. 시험을 위해 거부 결과나 safety 조건을
  우회하지 않는다. 적용 후보와 허용 범위는 별도 기술·안전 검토가 필요하다.
- 기존 정상 브랜치의 정확한 revision과 공식적으로 지원되는 복구 절차를 기록하고,
  정차 상태에서 복구 가능성을 검증한다. 주행 중 설치·설정·프로필 변경 금지.

## 향후 별도 승인 후 평가 원칙

숙련된 운전자가 안전하게 통제할 수 있는 적법한 폐쇄 시험 환경을 우선한다.
첫 시험은 넓고 충분한 안전 여유가 있는 직선 구간에서 시작하고, 별도 평가자가
기록을 담당한다. 손을 핸들에 유지하고 주변 상황을 직접 감시한다.
Driver monitoring, Panda safety, 속도/조향/가감속 제한, brake/cancel takeover를
그대로 유지한다. 시험 때문에 안전 제한을 확대하지 않는다.

직선 → 완만한 좌/우 곡선 → 속도별 조건 → 복잡 조건 순으로 단계적으로 평가한다.
한 번에 한 변경만 비교하고, 변경 전/후의 차량·노면·속도·경로·설정 차이를 기록한다.
위험한 cut-in, 급정지, 센서 오류를 공도에서 인위적으로 만들지 않는다.

## 즉시 개입 및 중단 조건

예상 밖 조향/가감속, 차선 가장자리 접근, 진동, 포화, 제어 지연, 경고,
운전자 override 후 비정상 복귀, 센서/차량 상태 불일치가 나타나면 운전자가
즉시 수동 제어하고 안전한 장소에 정차한다. 정차 후 후보를 격리하고 원래 정상
구성으로 복구한다. 원인 확인 전 시험을 재개하지 않는다.
리허설의 `ROLLED_BACK`은 메모리상의 스냅샷 선택일 뿐 실제 장치 복구가 아니다.

## 비교할 지표

- 횡방향: 독립 lane truth에 대한 중앙 오차, 좌/우 곡선 오차, edge margin,
  curvature/steering tracking, jerk, oscillation, saturation, override 및 복귀.
- 종방향: lead 거리/TTC, accel tracking, jerk, 정차 오차, 재출발 지연,
  cut-in 응답, 잘못된 정지 요구에 대한 반응, 운전자 개입.
- 지연: 실제 control latency와 scheduling jitter. PC의 worker timeout 통과를
  차량의 실시간 deadline 충족으로 해석하지 않는다.

모든 결과는 성공·실패·미실행·미검증을 구분하고 소프트웨어/설정 revision과
함께 기록한다. 이번 개발은 추가 주행데이터를 요구하거나 기다리지 않는다.
