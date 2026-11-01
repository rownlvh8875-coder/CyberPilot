# R33 · 합성 시나리오 일괄 실행

여러 R31 JSON을 지정한 순서대로 독립 실행하고 개별 R32 그래프·상태 표를
한 정적 HTML 목록에서 엽니다. 기존 공개0.3.0 계산 모듈/API/wheel은 변경하지
않습니다. 실차·로그 입력 도구나 F61/production Adapter가 아닙니다.

## 실행

저장소의 `tools/cyberlateral_dev`에서, 활성화된 기존 WSL 개발 환경을 사용합니다.
개인 uv 설치라면 해당 `runtime/bin`이 **현재 세션 PATH**에 있어야 합니다.
전역 설치나 기존 STEP7 변경은 필요하지 않습니다.

```bash
uv run --locked python -B tools/scenario_batch.py \
  --input examples/synthetic_sign_cycle_v1.json \
  --input examples/synthetic_resumed_v1.json \
  --output /tmp/NEW-cyberlateral-batch
```

출력 부모는 존재해야 하며 출력은 새 경로여야 합니다. 이 예시 경로가 이미
있으면 새 이름을 선택하세요. 컴포넌트 내부 출력은 금지합니다.
`--input`을1..32회 반복하며 파일을 자동 탐색하거나 재귀 검색하지 않습니다.
입력 순서가 출력 순서입니다. 총 유효 sample은8192개 이하이고 각 파일에는
[기존 R31 제한](SYNTHETIC_SCENARIO_CLI_R31_KO.md)이 그대로 적용됩니다.
실제 시간·r·T2·차량 설정 인자는 없습니다.

위 예시는2파일/5모델 호출입니다. 별도 테스트 실행의 모델 작업을 포함한
프로젝트 전체 누적 호출 수는 아닙니다. 리포트 생성의 새 모델 호출은0입니다.

## 결과

```text
NEW-cyberlateral-batch/
  index.html                   파일별 상태와 개별 리포트 링크
  BATCH.json                   전체 완료 기록 (마지막에 기록)
  RECEIPT.json                 실제 경로·Python·관찰 source hash
  SHA256SUMS.txt               하위 파일까지 전체 검산 (자기 자신 제외)
  PORTABLE_SHA256SUMS.txt      환경 제외 부분집합 검산
  inputs/case-001.json        소유한 원본 입력 bytes
  inputs/case-002.json
  case-001/
    data/                     기존 R31의6개 산출물
    report/                   기존 R32의4개 산출물; index.html 포함
    producer.log
    renderer.log
  case-002/                   두 번째 독립 실행 (위와 같은 구조)
```

Windows에서 출력 폴더의 `index.html`을 열면 됩니다. 하위 폴더 구조를 유지하세요.
새 일괄 목록의 HTML 구조·링크·escaping은 자동 검사하지만, 실제 브라우저
화면 검증은 별도입니다. 기존 R32.2 화면 PASS가 이 새 목록의 화면 PASS를
뜻하지는 않습니다. JavaScript·외부 자산·웹 서버를 사용하지 않습니다.

각 파일의 initial_state와 limits만 그 파일에 적용됩니다. 이전 파일의 마지막
상태를 다음 파일로 넘기지 않습니다. 다른 파일의 scenario_id가 같아도
case-001 등의 독립 경로를 사용합니다. 같은 경로를 두 번 지정하면 요청을
거절합니다. 부모 디렉터리의 별칭은 해소하지만 마지막 심볼릭 링크는 따라가지
않고 해당 파일을 거절합니다. 경로 조상과 작업 프로세스는 협조적 환경을
전제하며 OS 보안·atomic snapshot을 인증하지 않습니다.

## 입력 오류와 종료 코드

- `0`: 모든 파일 COMPLETE. 의미는 실행·저장·리포트 생성 완료이지 독립
  계산 검증, 안전성 또는 성능 PASS가 아닙니다.
- `1`: BATCH_COMPLETE_WITH_REJECTIONS. 읽기/스키마 오류 파일은 REJECTED,
  유효 파일은 실행합니다. 모든 파일이 잘못되어도 목록을 만들고 모델 호출은0입니다.
- `2`: 배치 요청/실행 환경/worker/기록 실패. 완료된 배치라고 사용하지 마세요.

모든 원본 입력을 먼저 제한적으로 읽고 검증합니다. 이후 원본 경로가 바뀌어도
worker는 소유한 snapshot을 사용합니다. 읽을 수 있고1MiB 이하인 잘못된 JSON도
원본과 SHA를 보존합니다. 읽기 불가/초과 파일에는 전체 bytes SHA나 snapshot을
주장하지 않고 null을 기록합니다. 입력 오류는 코드로 표시하며, 예외 메시지에
원본 내용을 끼워 넣지 않습니다.

출력 충돌·입력 개수/총 sample 초과·중복 경로는 worker 없이 배치를 거절합니다.
worker/identity/기록 실패는 즉시 중단하며 이후 파일을 실행하지 않습니다.
그 전에 실행된 모델 작업이 있을 수 있으므로0회라고 간주하지 마세요.
기존/부분 출력은 삭제·덮어쓰기·자동 재시도·resume하지 않습니다. 새 경로로
다시 실행하세요. 파일 쓰기는 crash-atomic이 아니므로 BATCH.json 존재만으로
성공을 판정하면 안 됩니다. canonical JSON, 상태 및 **전체 checksum**이 모두
일치해야 완료된 기록입니다. 중단 시 불완전한 마지막 파일도 남을 수 있습니다.

## 재현성과 한계

`PORTABLE_SHA256SUMS.txt`는 BATCH.json/index.html, 소유한 입력 snapshot,
완료 파일의 R31 INPUT/RESULTS/TRACE/SUMMARY와 R32 index/VIEW를 검산합니다.
같은 입력명·순서·bytes·source에서는 이 부분집합이 반복 실행 시 동일합니다.
경로/Python receipt, worker log와 receipt 포함 manifest는 제외합니다.
전체 SHA256SUMS가 서로 다를 수 있으며 그것을 재현 실패라고 보지 않습니다.
checksum은 인증이나 독립 numerical oracle이 아닙니다. REJECTED 입력은 모델
수치를 만들지 않으며, 임의 사용자 시나리오의 결과는 기존 모델의 출력입니다.

R_BUDGET=UNRESOLVED, Static Evidence Gate=FAIL, 실제 r/T2/scale=null을
유지합니다. SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO,
D2=PERFORMANCE_NOT_EVALUATED, F19=LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY=NOT_PROVEN, F70UH/F70V/F71=NOT_ALLOWED.
Controller·차량 Runtime·CAN·F61·실차 입력·r/dt 산출·candidate 성능 평가는
실행하지 않습니다. 순수 합성 모델 실행만 수행합니다.
