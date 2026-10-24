# Track F-21 — 비활성 Source Version 계약

## 상태와 권한

Source A의 역사적 Pin을 유지하면서 Source B의 선언된 파일 집합을 별도로
읽기 전용 검증하는 로컬 진단 코드다. 운영 Source 승인이나 CI 계약 개정이 아니다.

- F-19 Legacy Source Publication: UNRESOLVED ERROR
- Runtime Integration: NO-GO
- effective=false, runtime_authorized=false, diagnostic_only=true
- promotion_enabled=false, performance_qualified=false
- Vehicle authority NONE, selected_candidate=null, selected_policy=null
- D2 PERFORMANCE_NOT_EVALUATED, Private E2 NOT_AUTHORIZED, HOLDOUT CLOSED
- F-7/F-9 effective=false 유지

## 명시적 승인 범위 / Feature Change Record

사용자가 신규 비Frozen 네 파일의 로컬 생성 및 검증을 승인했다.
기존 파일 수정, F19 되돌리기, Commit/Push/GitHub CI/Runtime/차량 연결은 미승인이다.

Repository: https://github.com/rownlvh8875-coder/CyberPilot
Branch: feature/cyber-autotune
Parent HEAD: 51c1cdb3327f442d026e5ba3bdcc173438a6aae1
Source B: 같은 HEAD 위 F19의 미커밋 세 파일. HEAD는 실제 실행 Source 전체 식별자가 아니다.
기존 MIT/Upstream Attribution과 여섯 Submodule Pin을 보존한다. 외부 코드는 도입하지 않았다.

신규 파일:
1. capture-only-source-version-v1.json — 정확한 Source/의존/Receipt/권한 계약
2. tools/cyberpilot/source_version_contract_v1.py — 독립 비활성 검증기
3. tools/cyberpilot/tests/test_source_version_contract_v1.py — 파일 변조 및 권한 차단 시험
4. 이 문서 — Source 관계, 검증 범위와 다음 승인

수치 제어값·Gain·단위·시간·상태는 새로 정의하지 않는다.
코드는 명시적 로컬 파일을 읽고 JSON 결과를 stdout에 반환한다.
Controller/Planner/Params/CAN/Device/Runtime Apply를 import하거나 실행하지 않는다.
상태는 한 호출의 파일 바이트 캐시뿐이며 호출 간 Controller 상태를 갖지 않는다.

## Source A/B와 계약 Identity

Source A ID: SOURCE_A_HEAD_51C1CDB3_V1
Source B ID: SOURCE_B_F19_CAPTURE_ONLY_LOCAL_V1

source_a_sha256 / source_b_sha256는 controlsd.py 한 파일의 바이트 Anchor다.
modified_file_sha256가 F19의 정확한 세 파일을 각각 결속한다.
checked_component_sha256는 검증한 전체 선언 파일 맵의 정렬 Canonical SHA다.
어느 값도 전체 작업 트리 또는 실제 차량 동작의 Identity라는 뜻은 아니다.

A controlsd SHA:
f2857c1ffac0a7e3f6835cc235c510f0ee979eaaca6b6ace7291f3e00ad13dc1

B controlsd SHA:
1479d36585964bf7fcae481abcde7926cdee530c35a7cd976251539a224193d0

계약 Raw SHA256:
7f76b6d571092ae86200d963edc2959333fbf95868d443b78dc73bc02ec9d782

검증기는 이 단일 정확한 계약 바이트 Identity를 코드에 고정한다.
JSON의 Source SHA만 바꾸거나 재직렬화/공백 추가로 새 계약을 자동 승인할 수 없다.
무제한 SHA Allowlist, 환경변수 우회, 자동 Version 등록은 없다.

신뢰 경계는 검토된 검증기 코드와 외부 Source Manifest다.
검증기와 계약을 함께 악의적으로 고치면 자기 코드가 자신을 인증할 수는 없다.
검증기 자체와 네 신규 파일의 SHA는 별도 F21 제출 Manifest/독립 검토로 결속한다.
Contract 내부에 자기 자신/검증기의 최종 해시를 넣는 순환 해시는 만들지 않는다.

## 읽는 Source 범위

- F19 세 파일: B의 정확한 바이트, A는 원래 controlsd와 두 신규 F19 파일의 부재
- 불변 의존 28개: 기존 Source 검증 및 Native Reference 코드와 F7/F9/Frozen Manifest
- Frozen Source 231개
- 역사 Receipt 16개: Architecture 7, 사전 정책 6, TA 실행 관련 3
- Receipt의 Raw File SHA와 Canonical Body Receipt ID를 모두 구분해 검사

기존 Source A Publication 검증기를 바꾸거나 새 검증기에 위임하지 않았다.
새 코드는 Source A의 역사 파일/Receipt 보존만 별도로 확인한다.
Source B를 기존 A의 실행 결과로 소급 재분류하지 않는다.

F19/F20 외부 실험 Evidence의 SHA는 Reference로 계약에 결속되어 있다.
이 검증기가 외부 Archive를 자동 탐색하거나 과거 실험을 재실행하지는 않는다.
실제 Evidence 파일 검증은 로컬 F21 결과의 별도 증거 수집 범위로 보고한다.

## 실행

Ubuntu 24.04/WSL 및 기존 Python 환경에서 명시적 경로와 Version을 사용한다.

~~~bash
.venv/bin/python -B tools/cyberpilot/source_version_contract_v1.py \
  --source-root /absolute/path/to/CyberPilot \
  --contract /absolute/path/to/CyberPilot/docs/cyberpilot/changes/capture-only-source-version-v1.json \
  --source-version SOURCE_B_F19_CAPTURE_ONLY_LOCAL_V1
~~~

정확한 선언 파일 집합이면 exit=0, STRUCTURALLY_VALID다.
이는 Source 무결성 진단이며 성능 합격·Runtime 승인·Publication 성공이 아니다.
차단 시 exit=2, STRUCTURALLY_BLOCKED와 사유를 반환한다.
CLI 필수 인자가 빠진 경우 argparse의 일반 오류이며 Source 적격성 결과가 아니다.

Source A는 해당 정확한 원본 파일과 의존 집합을 가진 별도 명시적 Root로 검증한다.
현재 B Root를 A라고 지정하면 차단한다. Version ID만 바꿔 동일 Source로 위장할 수 없다.
현재 Git HEAD를 코드에서 실행/조회하지 않으며 reference_git_head는 계약의 Reference다.

## 경계 및 오류 처리

JSON 중복 Key, 비정상 JSON, NaN/Infinity/overflowed float, 과도한 깊이를 차단한다.
상대 경로·상위 디렉터리 이동·Symlink·특수 파일을 거부한다.
Linux Directory FD와 O_NOFOLLOW를 사용한다. 명시적 /dev, /proc, /sys 입력을 차단한다.
읽는 중 파일 크기/mtime/파일 Identity가 바뀌면 중단한다.
파일 단위 검증이 전체 디렉터리의 원자적 Snapshot을 증명하지는 않는다.
검증 중 Source를 바꾸지 않는 읽기 전용 환경에서 사용해야 한다.

Resource cap: Contract 128KiB, 개별 파일 4MiB, 고유 Source 바이트 합계 16MiB,
JSON 깊이 32. 현재 선언된 파일 크기를 수용하는 오프라인 Reader 한도다.
차량 성능·Freshness·지연·안전 Threshold가 아니다.
Windows Native 파일 시스템 지원을 주장하지 않으며 지원 개발 환경은 Linux/WSL이다.

## 로컬 시험과 기존 오류

~~~bash
.venv/bin/python -B tools/test_runner.py tools/cyberpilot/tests/test_source_version_contract_v1.py -j 1 -v
~~~

신규 시험은 실제 파일 복사본과 기존 검증기를 사용한다.
변조/누락/잘못된 Version/권한 위조/Manifest 변경/특수 파일/Symlink 등을 검사한다.
A Fixture는 선언 파일 집합이며 전체 역사 Runtime/CI checkout의 재현이 아니다.
A의 원본 controlsd는 정확한 Git 객체로 확보하며 숫자나 Report에서 합성하지 않는다.
Native 제어기와 대규모 A/B/C 주행 실험은 실행하지 않는다.

신규 테스트가 old verifier의 B 거부를 예상했다고 해서
기존 test_source_binding의 ERROR가 PASS로 바뀌는 것은 아니다.
실제 기존 Publication 파일의 6 PASS / 1 ERROR는 별도로 보존·보고한다.

이 새 tools 테스트는 기존 Full V2 TARGETS와 Upstream Unit 기본 수집에 자동 포함되지 않는다.
이번에는 CI를 수정하거나 실행하지 않았다.
새 Source Version의 공식 Publication/CI 지원은 별도 승인과 계약 개정이 필요하다.

## 불변성 및 복구

F19 세 파일·기존 Source Pin·역사 Receipt·기존 검증기·Workflow·Native/Replay Reference는
수정하지 않는다. 검증 결과가 실패해도 원문을 재봉인하거나 Source Pin을 치환하지 않는다.

F21을 되돌리는 작업도 사용자의 별도 결정 후 이 네 신규 파일만 대상으로 해야 한다.
F19의 세 파일과 기존 Artifact를 Reset/Checkout/Revert/Stash/덮어쓰기하지 않는다.
과거 Source로의 복귀는 별도 승인 범위다.

실제 측정 Freshness, Sensor Timing, Calibration, Firmware/Model Provenance,
물리 조향 응답, Road-relative Heading/Position, Performance Qualification은 미검증이다.
계약이 유효해도 LEVEL 3을 부여하지 않는다.
