# R43 — 명시한 여러 seed의 합성 경계 검사

R42를 seed별로 순차 실행하고, 모든 결과와 전체 재현 입력을 모으는 별도 DEV 명령입니다.
새 generator·수치 oracle·모델/API·wheel·lockfile·의존성은 추가하거나 바꾸지 않습니다.
차량 로그를 읽거나 설정을 최적화하지 않습니다.

## 실행

기존 CPython3.12.13/Linux binary64 DEV 환경에서 실행합니다. output 부모는 존재해야 하며
최종 경로는 **새 폴더**여야 합니다. 기존 결과·깨진 링크·component 안의 출력은 거절합니다.

```bash
r43_component="$PWD/tools/cyberlateral_dev"
r43_parent="$(mktemp -d /tmp/cyberlateral-r43-XXXXXX)"
uv run --project "$r43_component" --locked --offline python -B "$r43_component/tools/scenario_campaign.py" \
  --seed 42 --seed 43 --cases 2 --steps 32 --output "$r43_parent/one"
```

seed/cases/steps/output 모두 필수이며 자동 기본값은 없습니다. seed는 중복 없이1..4개,
각각0..4294967295, cases1..16, steps16..256입니다. 최대16384 declared samples입니다.
API는 builtin list와 builtin int만 받고 bool·수치 문자열·subclass를 거절합니다.
CLI 정수 token은 argparse int 변환을 따릅니다. `--input`, baseline, r/dt/차량 옵션은 없습니다.

위 예제는2seeds×2cases×32samples=128 model/128 selected-source reference steps입니다.
이는 명시한 한 실행의 계산량이며 unit/gate/실패한 worker 추가 작업은 별도 NONZERO일 수 있습니다.
seed는 입력 조합의 재현 조건이지 차량 설정이나 rate-policy 값이 아닙니다.

## 상태·결과

| 상태 | 조건 | exit |
|---|---|---|
| MATCH | 모든 seed/case 완료, 선언한 계산량 일치, 독립 참조 차이0 | 0 |
| DIFFERENT | 참조 수치 차이가 있고 완료된 ERROR는 없음 | 1 |
| ERROR | 하나 이상의 완료된 R42 ERROR; 수치 DIFFERENT보다 우선 | 2 |

완료된 ERROR 뒤에도 나머지 seed는 실행합니다. 각 상태·보고된 계산량·비일치를 별도로
보존합니다. 던져진 worker 오류·손상된 record·IO·늦은 source/child 변경은 즉시
`REJECTED: CAMPAIGN_*`/exit2이며 최종 CAMPAIGN.json을 만들지 않습니다. 이미 완료되거나
일부 생성된 child는 삭제/덮어쓰기/재개하지 않습니다.0개 실행을 성공 처리하지 않습니다.

- `CAMPAIGN.json`: 순서·seed별 상태/record SHA·계산량·차이·소스 identity·닫힌 Gate.
- `SUMMARY_KO.md`: 각 child의 기존 그래프·표·검사 기록·전체 재현 입력 링크.
- `runs/seed-001/`, `runs/seed-002/` 등: 원래 R42의 complete 결과.
- `runs/seed-001/reproducers/case-001.json` 등: 비일치/오류의 **전체 원형 sequence**.
- `SHA256SUMS.txt`: private receipt/log를 포함한 전체 실제 파일의 closed Manifest.

seed와 case 사이로 상태를 전달하지 않습니다. 원형 initial state와 입력 순서를 보존하고
truncate·renumber·minimize하지 않습니다. checksum은 출처 인증이 아닙니다. 저장값 변조나
고장난 worker를 이용한 negative control은 입력만으로 그 변조/환경 오류까지 재생한다는 뜻이 아닙니다.

내부 완료 record는1MiB bounded canonical JSON으로 읽으며 bool/음수/모순 counter,
요청한 seed/조건·source·gate·reproducer/생성 bytes 결속을 확인합니다. 기존 R42/R40/R39의
소비 field와 V1 파일 집합을 검산하고, 추가·누락·손상·링크·특수 파일은 거절합니다.
child별2048files/128MiB,16MiB/file/depth16; campaign 전체8192files/512MiB입니다.
root/nested closed Manifest와 portable subset checksum을 검산합니다. 이 검사는 임의의
새 R42 버전을 자동 승인하는 loader나 적대적 동시 파일 교체를 막는 OS snapshot이 아닙니다.

CAMPAIGN.json은 마지막에 기록합니다. 파일 존재만 보지 말고 canonical JSON·상태·모든
Manifest를 함께 확인하세요. 실패한 작업은 보고된 reference 합계 외에 추가 NONZERO일 수 있습니다.

## 두 회차 재현성

같은 명시 순서/조건/source/runtime이면 CAMPAIGN/SUMMARY, child EXPLORATION/GENERATION,
generated JSON과 기존 batch portable bytes가 일치합니다. complete 결과의 private 경로/log
때문에 전체 Manifest는 다를 수 있습니다. 자동 upload·ZIP·공유·baseline 갱신은 없습니다.

```bash
uv run --project "$r43_component" --locked --offline python -B "$r43_component/tools/scenario_campaign.py" \
  --seed 42 --seed 43 --cases 2 --steps 32 --output "$r43_parent/two"
uv run --project "$r43_component" --locked --offline python -B "$r43_component/tools/scenario_compare.py" \
  --baseline "$r43_parent/one/runs/seed-001/workflow/batch" \
  --candidate "$r43_parent/two/runs/seed-001/workflow/batch" --output "$r43_parent/compare-seed-001"
```

이 비교는 MATCH/64samples/차이0/새 모델0이 기대값입니다. seed-002도 같은 방식으로 따로
비교합니다. R34 저장값 일치와 R39 독립 수치 참조는 서로 다른 검사입니다.
portable subset은 complete baseline으로 사용하지 않습니다.

## 유지 제한

입력 feature 수나 seed 개수는 exhaustive branch coverage가 아닙니다. 합성 선택-source
parity이며 전체 Controller·실제 이력·물리 안전/성능 승인도 아닙니다. 호출 순서는 실제
시간·10ms·100Hz가 아닙니다. 허용오차·차이에 맞춘 튜닝·r=0 fallback은 없습니다.

R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제r/T2/vehicle scale=null,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime=NO_GO, D2=PERFORMANCE_NOT_EVALUATED,
F19=LEGACY_UNRESOLVED, NATIVE_EXACT_REPLAY=NOT_PROVEN, F70UH/V/F71=NOT_ALLOWED 유지.
F61·실제r/dt·Controller·차량 Runtime·CAN·실차 input/활성화·후보 평가는0입니다.
