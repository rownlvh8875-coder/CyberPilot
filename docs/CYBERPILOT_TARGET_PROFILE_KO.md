# 1차 검증 대상: 콤마4 / 더 뉴 싼타페 TM

사용자 진술(2026-11-13): **콤마4, 더 뉴 싼타페 TM 2021년식 디젤**.
이는 앞으로 검증할 대상 지정이며 기기 연결·차량 식별·설치 완료 증거는 아니다.
실차 장치나 차량에서 읽은 값은 이번 작업에 없다.

## 소스에서 확인한 범위

- 이 저장소의 `openpilot/cereal/log.capnp` InitData.DeviceType은 `mici`를
  comma four로 명시한다. `openpilot/common/hardware/comma/hardware.py`에도
  mici 분기와 기기 타입 식별 경로가 있다. 실제 사용자의 기기 식별 결과는 아니다.
- `docs/CARS.md`에는 Hyundai Santa Fe 2021-23 행이 있다.
- 현재 gitlink가 지정한 commaai/opendbc 커밋
  `4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`의
  `opendbc/car/hyundai/values.py`를 GitHub에서 읽고 Git blob을 검산했다.
  `CAR.HYUNDAI_SANTA_FE_2022`는 문서명 `Hyundai Santa Fe 2021-23`와
  연결된다. 심볼의 2022를 사용자의 연식으로 바꾸거나 실제 fingerprint로
  채택하지 않는다. HEV/PHEV는 별도 항목이다.
- 위 파일의 blob SHA: `c3df8a51b39b5bf0f40ff9857915a15ff14b8a61`.
  SHA256: `52ce46aafba6ebc3260b06d39e6263e2e80bf5c15562b13ee68220097aa8228f`.
  크기: 39,403 bytes. 분석용 사본은 외부 evidence에 보관한다.

## 아직 확정하지 않은 것

해당 모델군의 소스 지원 표기는 국내 디젤 사양의 exact 플랫폼/펌웨어·옵션·
실제 장착 하네스·설정값·물리적 한계의 증명이 아니다. 차량 fingerprint,
실제 소비 설정, 제어 입력/상태/시각 결속, normalization scale, r/T2를
이 표에서 자동 결정하지 않는다. native 의존성은 현재 클라우드 checkout에서
초기화되지 않았으며 전체 빌드·콤마4 부팅·업데이트·복구도 검증하지 않았다.

모바일 웹은 이 대상에서 향후 확인할 상태 조회 기능이다. 현재의 호스트/브라우저
검증을 실제 콤마4/싼타페 실시간 연동 결과로 보고하지 않는다.
R_BUDGET=UNRESOLVED, Static Evidence Gate=FAIL, 실제 r/T2/scale=null을 유지한다.
설치용 URL을 확정하거나 실차 제어를 켜는 단계는 아직 열리지 않았다.
