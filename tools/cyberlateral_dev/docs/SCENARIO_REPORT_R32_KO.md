# R32 — 사용자 합성 기록 HTML 리포트

R31 결과를 읽어 checksum과 기록 간 일관성을 확인하고 HTML 그래프·표를 만듭니다.
리포트 생성 자체는 모델을 import하거나 다시 실행하지 않습니다. 기존 public0.3.0
wheel/API·고정 catalog 보고서·R31 생산기·native 경로는 바꾸지 않았습니다.

## 실행

CyberPilot 저장소 루트 기준입니다. 기존 R31 결과가 있다면 생산 명령을 생략하고
`scenario_report.py`에 그 결과 디렉터리를 넘기면 됩니다.

```bash
uv sync --project tools/cyberlateral_dev --locked
mkdir -p tools/cyberlateral_dev/out
# 이 생산 명령만 모델4회 실행. 이미 R31 결과가 있으면 생략합니다.
uv run --project tools/cyberlateral_dev --locked python -B tools/cyberlateral_dev/tools/scenario.py --input tools/cyberlateral_dev/examples/synthetic_sign_cycle_v1.json --output tools/cyberlateral_dev/out/r32-data-1
# 저장된 결과만 읽기: 새 모델 호출0
uv run --project tools/cyberlateral_dev --locked python -B tools/cyberlateral_dev/tools/scenario_report.py --input tools/cyberlateral_dev/out/r32-data-1 --output tools/cyberlateral_dev/out/r32-view-1
```

`tools/cyberlateral_dev/out/r32-view-1/index.html`을 로컬 브라우저에서 엽니다.
서버·JavaScript·외부 자산은 필요 없습니다. 매번 새 출력 이름을 사용합니다.

## 화면에서 확인할 것

- 정규화 요청 graph와 정수 요청/이전 적용값/제한값/최종값 graph를 구분합니다.
  두 단위는 같지 않으며 정수값은 실제 물리 torque가 아닙니다.
- X축은 호출 index입니다. 실제 초·10ms·관측 주기를 뜻하지 않습니다.
- previous_requested와 previous_applied, 초기/다음 counter, active, 요청 비트,
  기록된 fault condition을 표에서 별도로 확인합니다.
- sign 예제 final은 `[2,-2,0,2]`입니다. resumed 예제의 요청 비트는 false여도
  final은-2입니다. 요청 비트 해제와 명령0을 동일시하지 않습니다.
- limiter_adjusted는 기록된 integer/limited의 차이일 뿐 driver/rate 단독 원인
  판정이 아닙니다. 이벤트 개수는 설명용이며 성능·feasibility 지표가 아닙니다.

SVG 좌표는 표시용 소수3자리입니다. 정확한 값은 VIEW.json과 표의 정수/hex를
사용합니다. 원본 signed zero는 hex에 남지만 그림에서는0과 겹칠 수 있습니다.
단일 샘플은 중앙 점으로 표시하고 평평한 series도0 폭 축을 사용하지 않습니다.
전체1..4096개 행을 표에 표시하므로 가로·세로 스크롤이 필요할 수 있습니다.

## 검산 범위와 출처 한계

입력은 정확히6개 파일인 R31 결과 디렉터리입니다.
INPUT.json,RESULTS.json,TRACE.csv,SUMMARY_KO.md,RECEIPT.json,SHA256SUMS.txt.
누락/추가 파일과 최종 symlink/FIFO/device/directory member를 거부합니다.
알 수 없는 manifest 경로를 열지 않으며 지정5개 hash를 전부 확인합니다.

bounded snapshot 한도는 INPUT/TRACE 각1MiB, RESULTS16MiB, SUMMARY16KiB,
RECEIPT512KiB, manifest4KiB입니다. 개발 자원 한도이지 차량 제약이 아닙니다.
JSON은 R31 canonical UTF-8 형식과 exact type/hex를 요구하며 중복·비유한 값·
float token128자 초과/int token32자 초과/중첩64단계 초과를 거부합니다.

전체 row의 형식, 저장된 중복값, 초기/다음 상태 연결, 최종 상태와 JSON/CSV/
요약 투영의 byte 일관성을 확인합니다. 양자화·limiter·fault·gate·Float32 공식을
다시 평가하지 않으며 독립 수치 oracle이 아닙니다. producer identity와 환경
receipt는 기록된 선언입니다. receipt나 source inventory의 경로를 열지 않습니다.
옛 R31 결과의 inventory를 오늘의 renderer 파일 목록과 혼동하지 않습니다.

원본 scenario bytes는 R31 출력에 없으므로 raw-input SHA를 원본에서 재계산할 수
없습니다. 기록 사이의 SHA 일치만 확인합니다. SYNTHETIC_ONLY 역시 출처 인증이
아니며, 일관되게 위조하고 hash를 다시 만든 기록은 탐지하지 못합니다.

## 출력과 실패 처리

새 디렉터리에 다음4개를 만듭니다.

- index.html: self-contained 정적 HTML/SVG.
- VIEW.json: 검산한 기록의 portable 투영, source portable4 hash, 닫힌 gate.
- RECEIPT.json: 실제 입력/출력/Python/tool 경로·hash, 소유한 입력6개 hash.
- SHA256SUMS.txt: 위3개 파일 hash.

같은 저장 입력의 index.html/VIEW.json은 source·출력 경로를 옮겨도 같습니다.
환경 receipt와 이를 포함한 전체 manifest가 같다고 주장하지 않습니다. 실제
receipt 경로를 portable HTML에 넣지 않습니다. 원본6개 파일은 수정하지 않습니다.

기존 출력·깨진 symlink·부모 부재·입력 트리 내부 출력은 읽기 전에 거부합니다.
전체 검증/렌더 후에만 새 디렉터리를 만들고 배타적으로 쓰며 index.html은 마지막입니다.
crash atomicity·동시 교체 방지·durability·자동 rollback/resume 보장은 없습니다.
IO/close/crash로 부분 출력이 남을 수 있습니다. CLI exit0과 전체 checksum을 모두
확인해야 하며 index 존재만 성공으로 취급하지 않습니다. 새 이름으로 재시도합니다.

오류는 exit2와 `REJECTED: REPORT_*`입니다. suffix는 INPUT_FILE/FILES/SIZE/
CHECKSUM/JSON/SCHEMA/CONSISTENCY, OUTPUT_EXISTS/OUTPUT_PARENT/OUTPUT_LOCATION,
RUNTIME/PUBLICATION_FAILED입니다. runtime은 Linux/CPython3.12.13/binary64이며
cooperative filesystem의 관찰입니다. OS image나 적대적 프로세스 인증은 아닙니다.
CLI는 cold private cache prefix를 쓰나 in-process API 격리는 보장하지 않습니다.

## 계속 닫힌 gate

R_BUDGET=UNRESOLVED, Static Evidence Gate=FAIL, 실제 r/T2/차량 scale=null,
SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO, F70UH/V/F71=NOT_ALLOWED.
실차 입력/F61/Controller/Runtime/CAN/r/dt/후보 성능 평가·설치·활성화를 열지 않습니다.
전체 테스트·CI는 기존 합성 모델을 실행하므로 작업 전체를 model0이라고 표현하지 않습니다.
새 renderer의 모델 호출0과 입력에 기록된 모델 호출 수를 분리합니다.

[검증 기록](SCENARIO_REPORT_R32_RESULTS.md)
