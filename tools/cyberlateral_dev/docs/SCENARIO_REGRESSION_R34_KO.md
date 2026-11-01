# R34 — 저장된 합성 batch 자동 회귀 비교

R33에서 저장한 두 batch를 읽기 전용으로 비교합니다. 모델을 다시 실행하지
않고, 같은 입력의 명령·이전 상태·제한/정밀도 trace·최종 상태 변화와 입력
거절 코드 변화를 확인하는 개발 도구입니다. 공개0.3.0 계산 모듈/API/wheel은
변경하지 않습니다. 실차 후보 평가나 물리 안전·성능 검증 도구가 아닙니다.

## 사용

기존 pinned DEV 환경의 Linux/CPython3.12.13에서 저장소 root 기준입니다.
`--baseline`과 `--candidate`는 각각 **완전한 R33 출력 폴더**여야 합니다.
portable 공유 ZIP만 푼 폴더나 R31 단일 결과 폴더는 지원하지 않습니다.
환경 receipt의 옛 경로를 따라가거나 원래 입력 파일을 다시 열지 않습니다.

```bash
uv run --project tools/cyberlateral_dev --locked python -B tools/cyberlateral_dev/tools/scenario_compare.py --baseline /absolute/saved-batch-before --candidate /absolute/saved-batch-after --output /absolute/NEW-comparison
```

두 batch는 R33의 기존 `tools/scenario_batch.py`로 별도 생성합니다. 비교 CLI는
생성기를 호출하지 않습니다. 출력 부모는 존재해야 하며 출력은 새 경로이고
component와 두 입력 폴더 밖이어야 합니다. 같은 입력 폴더를 양쪽에 지정하는
자체 검산도 가능합니다. `--candidate`는 비교 대상 파일의 역할 이름일 뿐
vehicle Candidate=NO_GO를 바꾸지 않습니다.

## 비교 규칙

- case는 입력 인수의 순서대로 대응합니다. 중복 scenario_id를 합치지 않습니다.
  파일 추가·제거·순서 변경은 숨기지 않습니다. 자동 ID 매칭은 없습니다.
- raw SHA가 다르면 INPUT_CHANGED입니다. 입력이 바뀐 결과를 같은 입력의
  수치 회귀라고 표현하지 않습니다. 공백만 바뀌어도 raw identity는 바뀝니다.
- COMPLETE인 동일 raw 입력에서는 typed INPUT, 각 호출의 prepared sample/state,
  전체 model_output/trace/projection/next_state 및 final_state를 비교합니다.
  previous_requested와 previous_applied는 서로 다른 필드입니다.
- int/float/bool, signed zero, hex 표현과 scalar kind를 정확히 비교하며 임의
  허용오차는 없습니다. invocation index는 실제 초·10ms·100Hz를 뜻하지 않습니다.
- 동일한 저장 raw bytes의 동일 거절 코드는 거절 기록으로 일치할 수 있습니다.
  bytes/SHA가 없는 missing 입력은 양쪽 코드가 같아도 UNVERIFIABLE_INPUT이며
  MATCH로 확정하지 않습니다.
- producer identity 변화는 case별 flag와 양쪽 identity SHA로 별도 표시합니다.
  거절만 있는 batch도 root receipt에 기록된 producer 소스 inventory SHA와
  변화 flag를 표시합니다. 기록된 소스 경로는 metadata이며 열지 않습니다.
  숫자가 같으면 MATCH일 수 있지만 이때 identity 동일성을 주장하지 않습니다.
  기존 reader가 아는 R31/R32 public0.3.0 identity/스키마만 지원합니다. 새 모델
  버전의 비교는 자동 허용하지 않으며 별도 호환성 계약이 필요합니다.

## 검산과 출력

root/portable/nested Manifest, canonical JSON, 정확한 member 집합과 생성 경로,
case 순서·집계·닫힌 gate, raw snapshot↔typed INPUT 및 저장 R31/R32의 상호
일관성을 검산합니다. 기존 R32의 bytes-only decoder를 사용하며 Controller,
모델/native import, producer/renderer worker 실행은 없습니다. 재해시된 수치가
일관되면 비교 대상이 될 수 있으므로 검산 PASS는 출처 인증이나 산술 증명이 아닙니다.

- `COMPARE.json`: portable 결과, case별 분류·차이 수·첫 차이, 전체 상세 중
  첫256개, 전체 차이 수와 잘림 여부, source identity 변화, 닫힌 gate.
- `SUMMARY_KO.md`: 사람용 요약과 한계. 전체 값은 JSON이 기준입니다.
- `RECEIPT.json`: 실제 로컬 경로·Python 및 비교 코드 identity. 개인 경로를
  포함할 수 있으므로 portable 자료로 공개하지 마십시오.
- `SHA256SUMS.txt`: 위3개 파일의 검산값. 출력 폴더에서
  `sha256sum -c SHA256SUMS.txt`로 확인합니다.

CLI exit0은 비교 가능한 기록 MATCH, exit1은 정상 완료된 DIFFERENT(검증 불가
입력 포함), exit2는 요청/묶음/환경/쓰기 오류입니다. exit1은 실제 성능이 나쁘다는
뜻이 아닙니다. 회귀 CI에서는 exit1을 실패로 취급하고 변경을 검토할 수 있습니다.
baseline 자동 갱신·r/dt/policy/fallback/허용오차 옵션은 없습니다.

완료 JSON은 마지막에 배타적으로 씁니다. 성공 exit와 전체 Manifest를 함께
확인해야 하며 JSON 파일의 존재만 완료로 보지 않습니다. 쓰기/close/crash 시
부분 출력이 남을 수 있고 atomic publication/resume/덮어쓰기를 보장하지 않습니다.
실패 폴더를 삭제하거나 재사용하지 않고 새 이름을 사용하십시오.

## 범위 제한

각 묶음은 최대32 case·8192 sample,512파일·파일당16MiB·합계128MiB입니다.
깊이4, root Manifest128KiB, BATCH/receipt512KiB 한도도 적용합니다. R31 데이터는
기존 파일별 한도를 추가 적용합니다. 이는 개발 자원 제한이지 차량 한계가 아닙니다.
최종 root와 모든 하위 member의 symlink·FIFO·device는 거부하고 nofollow/
nonblocking regular-file bytes를 소유합니다. 조상 경로의 symlink 전체 금지나
atomic snapshot·OS/출처 인증·악의적 동시 교체 방어를 주장하지 않습니다.

새 모델 실행0, F61·r/dt·Controller·Runtime·CAN·실차 입력/활성화0.
R_BUDGET=UNRESOLVED, Static Gate=FAIL, actual r/T2/vehicle scale=null,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO, F70UH/V/F71 NOT_ALLOWED.

[로컬 구현 검증 기록](SCENARIO_REGRESSION_R34_RESULTS.md)
