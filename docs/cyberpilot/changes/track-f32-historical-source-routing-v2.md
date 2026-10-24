# F32 Historical Source Routing V2 — UNAPPLIED_PROPOSAL

이 문서는 격리 구현의 적용 검토안이다. 실제 원본 적용·Commit·Push·Workflow 실행을 승인하지 않는다.

## Source 의미

- A: 현재 Source-A-compatible controlsd. SHA256 f2857c1ffac0a7e3f6835cc235c510f0ee979eaaca6b6ace7291f3e00ad13dc1. B 전용 파일이 남아 있으므로 순수 역사적 Source A 전체 트리가 아니다.
- B1: 고정 d94c908d287d0da389dc552e1d4e26ce6dae7a78 및 pinned opendbc Git Object에서 읽은 선언된 328파일의 역사적 Capsule. 현재 작업 파일을 B1 생산에 사용하지 않는다. Blob ID·SHA256·계약·Receipt·Frozen Source를 검증한다. thin Git object view는 전체 Git 이력 clone이 아니다.
- B2: F32_A_COMPATIBLE_INACTIVE_CAPTURE_TYPE_V2. A-compatible controlsd를 유지하며 비활성 Capture 모듈의 타입만 수정한 별도 파생 프로필이다. 과거 F29의 B-controlsd 기반 B2 전체 Source와 동일하지 않다.
- Capture v1 SHA256: e08c243b97d81928194d143f42e79886324f7de88cc7bfb903bc70a8c5ac9028.
- Capture 제안 SHA256: a13017c9a03d6075a4bd2f55c7ae0a64c483bc648b7018af238e5bbfb6cf8dde.

v1 Source Version Contract·Validator·Dual-source Contract·Driver·Tests·Workflow 및 역사적 Receipt는 변경하지 않는다. v1은 B1 Capsule에서 실행하며 새 Router가 v1 오류를 면제하지 않는다.

## 실행 경로

현재 A-compatible ROOT의 Legacy 7개, B1의 Legacy 6 PASS/1 ERROR, F21 38개, F23 6개, B2의 기존 Capture 8개 테스트를 별도 프로세스로 실행한다. B1의 INJECTION_SOURCE_DRIFT와 suite exit1은 실제 오류로 기록한다. 새 진단 집계가 성공해도 B1 Legacy 성공으로 바꾸지 않는다.

A 실행에 쓰이는 기존 v1 테스트·검증기·계약의 Pin도 A의 검증 Inventory와 Source Identity에 포함한다. Test ID가 같아도 테스트 파일 바이트가 달라지면 차단한다.

각 Source의 test IDs/source identity/raw unittest counts/exit/records/새 execution receipt를 별도 JSON으로 보존한다. Source A 성공을 B1/B2 성공으로 재사용하지 않는다. 새 Receipt는 기존 역사적 Receipt의 재봉인이 아니다.

~~~bash
.venv/bin/python -B tools/cyberpilot/historical_source_routing_v2.py \
  --repo /absolute/repository --current-root /absolute/repository \
  --contract /absolute/repository/docs/cyberpilot/changes/historical-source-routing-v2.json \
  --output /absolute/external/new-output
~~~

출력 디렉터리는 새 경로여야 한다. 잘못된 Ref·Blob·Source·계약·권한·Test ID/Result는 차단한다. 기존 F21 테스트의 ROOT 가정을 변경하지 않고 인증된 Capsule의 정확한 파일을 로드한다. 원본 ROOT의 v1 테스트를 실행하면 실패가 남을 수 있다.

## 타입 변경

검증 직후 native_result를 두 변수로 unpack하고 명시적 2원소 튜플을 구성한다. 허용오차나 입력 Validation을 바꾸지 않는다. 역사적 iterable 처리와 오류 동작을 보존한다. 현재 A-compatible controlsd는 Capture 모듈을 import/call하지 않는다. 타입 적합성은 센서 측정 적격성·제어 성능·Runtime 승인과 무관하다.

## Workflow

신규 YAML은 workflow_dispatch 전용, contents: read이며 기존 Workflow나 Required Check를 교체하지 않는다. checkout/upload-artifact는 공식 v7 ref에서 확인한 전체 SHA에 고정한다. checkout credential persistence는 false다. Artifact는 result.json과 Source별 execution receipt 3개만 포함한다. Capsule/.git/환경/자격증명/Private Evidence는 업로드하지 않는다.

실제 GitHub Workflow는 실행하지 않았다. 기존 tools/op.sh setup을 이용하는 향후 Runner 설치·네트워크·환경은 별도 GitHub 실행 승인이 필요하며 성공을 보장하지 않는다. Source/Action Pin 검토는 외부 Action 전체 코드의 보안 인증이 아니다.

## 기존 CI와 승인

기존 Full CI V2의 두 Test namespace와 5,960 IDs/Baseline5,927을 바꾸지 않는다. 새 테스트는 tools/cyberpilot/tests에 있다. Capture 타입 변경은 현재 openpilot Runtime/Full-suite import 경로에서 참조되지 않는다. F31의 5,960 PASS는 이전 실행 증거이며 새 Patch의 Full CI 성공이라고 표시하지 않는다.

적용 후보는 정확히 6파일: Capture 1개 수정, 신규 계약·Router·Tests·수동 Workflow·본 문서 5개 추가다. F31의 controlsd 복원은 그대로 보존한다. 적용 승인 시 기존 unstaged controlsd 1개와 별도로 이 6개 경로만 허용해야 한다. Git staging/commit/push/CI 실행은 다시 별도 승인 대상이다.

Rollback은 승인된 새 변경만 보존·회수하는 별도 작업이다. Source B v1 Pin 또는 Receipt를 치환하지 않으며 controlsd 복원을 자동 취소하지 않는다.

D2 PERFORMANCE_NOT_EVALUATED; Private E2 NOT_AUTHORIZED; HOLDOUT CLOSED; Vehicle authority NONE; selected_candidate=null; selected_policy=null; F7/F9 effective=false; RUNTIME_NO_GO.
