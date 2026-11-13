# 상태 웹의 host-native 통신 검증

콤마4 / 더 뉴 싼타페 TM 2021 디젤 설치 전, 클라우드 Linux x86_64에서
실제 Cereal schema·msgq native IPC와 상태 웹의 연결을 검증하는 개발 도구다.
합성 상태 메시지만 사용한다. 콤마4용 빌드·실제 차량·실제 폰 연동 결과가 아니다.

## 고정된 범위

- msgq: `0e266c1dbcf7328beee3e57b4a8688555387c877`
- opendbc: `4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`
- Python 3.12, pycapnp 2.1.0 및 uv.lock의 검증 도구.
- 외부 새 폴더에서 `msgq/ipc_pyx.so`만 빌드한다. root native submodule,
  root Python 환경, 기존 개발판과 제어 소스는 변경하지 않는다.

운영 환경의 기본 IPC에 시험 메시지를 보내지 않는다. native 진입 시 폴더의 실제
경로가 정확히 /dev/shm의 해당 prefix 경로인지 확인하며, endpoint는 동일 소유자의
단일 링크인 일반 파일만 허용한다. 테스트용 임시 폴더는 native 진입에 사용할 수 없다. 매 시험은 고유한
`OPENPILOT_PREFIX`와 소유자 전용 0700 `/dev/shm/msgq_cyberpilot_web_native_*`
폴더를 생성한다. 환경에 기존 OPENPILOT_PREFIX 또는 CEREAL_FAKE가 있으면 거절한다.
CEREAL_FAKE_PREFIX만으로 IPC 격리가 되는 것은 아니다. 이미 설정된 세션을
임의로 해제하지 말고 이 시험용으로 분리한 프로세스에서 실행한다.

시험 publisher는 deviceState/selfdriveState/carState/managerState 네 종류만
허용한다. CAN·sendcan·제어 명령은 만들거나 송신하지 않는다. 원래 상태 웹은
그대로 읽기 전용이며 publisher 코드는 개발 검증 도구 안에만 있다.

## 클라우드 재현 명령

저장소 루트, Linux x86_64, Python 3.12.13과 C++ 컴파일러/g++가 필요하다.
최소 빌드라 별도 comma 장치·모델·전체 SDK는 사용하지 않는다.
기본 예의 `workspace`는 이번 실행 전용 **새 외부 경로**다.

```bash
uv sync --locked --project tools/cyberpilot_web_native
workspace=$(mktemp -d /tmp/cyberpilot-native-XXXXXX)
python_bin="$PWD/tools/cyberpilot_web_native/.venv/bin/python"
"$python_bin" -B tools/cyberpilot_web_native/prepare.py --output "$workspace/build"
"$python_bin" -B tools/cyberpilot_web_native/verify.py \
  --prepared "$workspace/build" --output "$workspace/verification"
```

prepare는 고정 커밋을 GitHub에서 새로 받고 tracked source hash와 native binary
SHA를 기록한다. verify는 이를 재검산하고 격리된 새 하위 프로세스에서 실제
native collector 테스트·별도 웹 CLI·HTTP·PC/모바일 Chromium 검사를 수행한다.
실행 환경은 자동으로 출력 폴더의 native 경로를 사용하며 운영 환경을 수정하지 않는다.
Chromium 또는 Google Chrome이 없으면 Playwright의 Chromium을 설치해야 한다.
기존 basic web 검증도 실행한다. 단계가 실패하면 PASS 영수증을 생성하지 않는다.
웹 프로세스 생성·브라우저 종료가 실패해도 다른 정리 단계를 계속 시도한다.
통신 자원 종료를 확인하지 못하면 IPC_NAMESPACE_*.json과 오류에 소유 경로를
남기고 시험 폴더를 보존하며 FAIL 처리한다. 명령 timeout은 새 세션의 프로세스
그룹을 종료한다. 강제 종료·커널 중단 등에서는 사후 폴더 정리가 보장되지 않으며
일반 메시지 폴더를 일괄 삭제하지 않는다.

출력의 RESULTS.json, NATIVE_TEST_RESULTS.json, native-web/NATIVE_WEB_RESULTS.json,
BUILD_RECEIPT.json, SOURCE_SHA256.json, MANIFEST.json과 로그·캡처를 보존한다.
native 바이너리의 비트 재현성은 주장하지 않는다. 컴파일러/SDK/경로가 다르면
바이너리 SHA도 달라질 수 있다. 원본 커밋·소스 SHA·기능 검증을 기준으로 삼는다.

## 결과 해석

검증 항목은 실제 SubMaster의 유효성/형식, 미수신 값 숨김, UInt64 타임스탬프 보존,
중복/역행 수신의 freshness 갱신 거절, 독립 topic 만료, 별도 웹 프로세스 전달,
화면의 invalid/중단/복구와 서버 연결 구분이다. 화면의 CAN 연결됨은 시험에서
명시한 canValid=true 합성 메시지를 표시한 결과이며 실차 연결 증거가 아니다.

남은 일은 실제 comma4 접근/기기 식별, 대상 native 전체 빌드·시작·업데이트·복구,
실제 상태 및 폰 네트워크 검증, 실제 제어 Adapter 입력 결속과 rate/static 근거다.
R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제 r/T2/vehicle scale=null을 유지한다.
실차 제어·F70UH/V/F71은 열리지 않는다.
