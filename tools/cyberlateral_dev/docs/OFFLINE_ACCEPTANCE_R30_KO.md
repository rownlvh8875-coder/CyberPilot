# 오프라인 개발판 인수·사용 안내 (R30)

현재 제공하는 것은 CyberLateral0.3.0 합성 command/state 계산 패키지와 개발
검증 도구입니다. 실제 차량용 CyberPilot 완성판이나 openpilot 설치 패키지가
아닙니다. root README의 upstream openpilot 설명을 이번 기능의 구현 성과로
세지 않습니다. 전체 제품 요구사항은 확인한 목표 문서에서 확정되지 않았습니다.

## 무엇을 사용할 수 있나

| 범위 | 현재 제공 | 제한 |
| --- | --- | --- |
| Python API | step, explicit state, simulate | 합성 tuple1..4096; 시간·실차 증명 아님 |
| 일반 CLI | 고정7시나리오 보고서 | 사용자 시나리오 파일 입력은 아직 없음 |
| 공개 wheel | 설치 가능한0.3.0, runtime dependencies0 | 어댑터/native 도구는 포함하지 않음 |
| 기본 검증 | 전체 테스트·정적 검사·설치·보고서 재현 | pure 경로; native 자동 실행하지 않음 |
| R28 | 자체 생성 native 합성 메시지 읽기 | 범용 외부 파서·실제 custody 아님 |
| R29 | 어댑터→모델의 고정4/99회 상태 전달 | profile별 초기화; 실제 이력/elapsed time 아님 |
| R27 | native 기존8단계 전체 회귀 | 명시적 opt-in, 아래 별도 환경만 |

정확한 source SHA·symbol과 미구현/미확정 구분은
[기능 목록 JSON](OFFLINE_CAPABILITY_INVENTORY_R30.json)을 참고하십시오.
모델 history의 previous_requested는 정수 candidate 상태이며 raw normalized
CC request나 F61 previous_native와 같다고 주장하지 않습니다. 입력의 native
읽기는 출력 projection을 CAN wire로 승격하지 않습니다.

## 1. 기본 검증: 저장소 root에서 실행

검증한 도구는 uv0.12.23, CPython3.12.13입니다. 최초 Python/DEV 의존성 준비에는
네트워크가 필요할 수 있습니다. root `uv sync`, submodule/LFS, Docker, 차량
장치 준비는 하지 않습니다. 아래 모든 경로는 NEW여야 합니다. 다시 실행할
때는 이름의1을2 등으로 바꾸고 기존 폴더를 삭제하거나 덮어쓰지 마십시오.

```bash
uv run --project tools/cyberlateral_dev --locked python -B tools/cyberlateral_dev/dev.py verify --output tools/cyberlateral_dev/out/r30-pure-1
```

성공 시 SUMMARY.json과94개 파일 hash를 담는 SHA256SUMS.txt, 로그, wheel,
두 보고서 및 고정 재현 산출물이 나옵니다. 해당 output 디렉터리에서
`sha256sum -c SHA256SUMS.txt`로 확인합니다. 현재 기존 테스트는440개입니다.
PASS는 오프라인 개발 경로의 결과이지 실차 안전·성능 판정이 아닙니다.

## 2. 패키지만 별도 설치하고 보고서 보기

다음도 저장소 root에서 실행합니다. 프로젝트를 editable로 설치하지 않습니다.

```bash
uv run --project tools/cyberlateral_dev --locked python -B tools/cyberlateral_dev/tools/build_wheel.py --output tools/cyberlateral_dev/out/r30-package-1
uv venv --python 3.12.13 tools/cyberlateral_dev/out/r30-runtime-1
uv pip install --offline --no-deps --link-mode copy --python tools/cyberlateral_dev/out/r30-runtime-1/bin/python tools/cyberlateral_dev/out/r30-package-1/cyberlateral_dev-0.3.0-py3-none-any.whl
tools/cyberlateral_dev/out/r30-runtime-1/bin/python -I -B -m cyberlateral_dev --report --output tools/cyberlateral_dev/out/r30-report-1
```

out/r30-report-1/index.html을 로컬 브라우저에서 열 수 있습니다. HTML/CSV/JSON
4개와 report checksum이 생성됩니다. 이 작업의 검증은 데이터·구조·byte 비교이며
브라우저에서 보이는 품질을 검증했다는 주장은 아닙니다. wheel은46,646 bytes,
SHA256 `3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c`입니다.

Python 사용자 코드는 기존 LateralInput/Limits와 명시적 state를 구성해 step이나
simulate를 호출할 수 있습니다. CLI가 고정이라고 이 API까지 미구현은 아닙니다.
자세한 예는 [component README](../README.md)의 Build and use separately에 있습니다.

## 3. 선택 사항: native 합성 경로

이 절차는 Linux x86_64/CPython3.12.13과 정확한 pycapnp2.1.0 wheel에만 검증돼
있습니다. Windows/macOS/다른 Python에 대한 native 자격 주장은 하지 않습니다.
별도 venv를 쓰며 기본 pure 환경에 pycapnp를 섞지 않습니다. 위2번의 wheel이
있어야 합니다. 아래 setup/download에는 네트워크가 필요합니다.

```bash
uv venv --python 3.12.13 tools/cyberlateral_dev/out/r30-native-1
uv pip install --python tools/cyberlateral_dev/out/r30-native-1/bin/python --require-hashes --no-deps --only-binary :all: --link-mode copy -r tools/cyberlateral_dev/native_qualification/requirements.txt
uv pip install --python tools/cyberlateral_dev/out/r30-native-1/bin/python --offline --no-deps --link-mode copy tools/cyberlateral_dev/out/r30-package-1/cyberlateral_dev-0.3.0-py3-none-any.whl
curl --fail --location 'https://files.pythonhosted.org/packages/63/9d/18e978500d5f6bd8d152f4d6919e3cfb83ead8a71c14613bbb54322df8b9/pycapnp-2.1.0-cp312-cp312-manylinux_2_28_x86_64.whl' --output tools/cyberlateral_dev/out/r30-package-1/pycapnp-2.1.0-cp312-cp312-manylinux_2_28_x86_64.whl
```

native wheel SHA256는
`48938e0436ab1be615fc0a41434119a2065490a6212b9a5e56949e89b0588b76`입니다.
require-hashes가 설치본을, 각 runner가 전달 wheel/schema/설치 파일을 import 전에
검사합니다. 다른 bytes를 허용하도록 hash를 바꾸지 마십시오.

같은 root shell에서 다음 task 전용 변수를 설정하고 실행합니다.

```bash
r30_python="$PWD/tools/cyberlateral_dev/out/r30-native-1/bin/python"
r30_wheel="$PWD/tools/cyberlateral_dev/out/r30-package-1/pycapnp-2.1.0-cp312-cp312-manylinux_2_28_x86_64.whl"
r30_public="$PWD/tools/cyberlateral_dev/out/r30-package-1/cyberlateral_dev-0.3.0-py3-none-any.whl"
uv run --project tools/cyberlateral_dev --locked python -B tools/cyberlateral_dev/native_qualification/suite.py --fixed-native-suite --python "$r30_python" --wheel "$r30_wheel" --package-wheel "$r30_public" --output tools/cyberlateral_dev/out/r30-r27-1
uv run --project tools/cyberlateral_dev --locked python -B tools/cyberlateral_dev/native_qualification/adapter_run.py --controlled-synthetic-adapter --python "$r30_python" --wheel "$r30_wheel" --package-wheel "$r30_public" --output tools/cyberlateral_dev/out/r30-r28-1
uv run --project tools/cyberlateral_dev --locked python -B tools/cyberlateral_dev/native_qualification/adapter_sequence_run.py --fixed-adapter-model-sequences --python "$r30_python" --wheel "$r30_wheel" --package-wheel "$r30_public" --output tools/cyberlateral_dev/out/r30-r29-1
```

각 runner는 새로운 -I/-B process를 시작합니다. 같은 부모 venv를 사용해도
한 process에서 qualified context를 반복해서 여는 것은 아닙니다.
上記3回のformal qualification model callsは454+0+206=660です。
pure/unit/CI/별도 report의 모델 계산은 추가입니다.660을 전체 작업의 총계로
표시하거나 invocation을 초·실차100Hz로 변환하지 마십시오.

## 4. 開発判定・GitHubと残りの範囲

이 milestone의 수락 조건은 source/wheel 불변, fresh pure/static/compile,
별도 runtime report 일치, 선택 native portable 결과 일치, Manifest/data 검산,
독립 review, exact-final-head 전용 CI와 Draft 상태 확인입니다. 실제 결과는
R30 결과 문서와 외부 receipt를 기준으로 하며 README나 static inventory의
기재만으로 PASS라고 하지 않습니다.

전용 workflow만 사용하며 기존 openpilot build/replay workflow를 켜서 이
수락 조건을 채우지 않습니다. Draft PR2 업데이트는 main merge 허가가 아니며
GitHub required checks/branch policy를 우회하지 않습니다. 자동 merge/install 없음.

未確定:実際のr/T2/vehicle scale、静的車両文脈、実際の履歴custody、対象配備、
全CyberPilot製品要件。これらはoffline開発の阻害条件ではありませんが、
offline受入でも解消しません。F61/Controller/Runtime/CAN/実車入力/r/dt実行0、
R_BUDGET UNRESOLVED、Static Gate FAIL、activation/F70UH/F70V/F71 NOT_ALLOWED。

次の実装候補は既存pure APIを使う「ユーザー定義SYNTHETICシナリオのファイル
入出力・CLI契約」です。これは便利機能の提案であり、今回の実装・実車入力
許可や、確認済みの製品必須要件としては扱いません。
