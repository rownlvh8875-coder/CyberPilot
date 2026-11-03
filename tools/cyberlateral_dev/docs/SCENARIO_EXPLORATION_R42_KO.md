# R42 — 재현 가능한 자동 합성 경계 탐색

고정 경계 입력과 seed 기반 조합을 R31 JSON으로 자동 생성한 뒤 기존 R40 실행·R39 독립 참조를 연결합니다. 공개0.3.0 모델/API/wheel과 lockfile은 그대로이며 새 의존성은 없습니다. 차량 로그를 읽거나 설정을 최적화하는 도구가 아닙니다.

## 실행

기존 pinned CPython3.12.13/Linux binary64 DEV 환경에서 repository 또는 component 부분 export root 기준입니다. 출력 부모가 존재해야 하며 각 출력은 **새 경로**여야 합니다.

```bash
r42_component="$PWD/tools/cyberlateral_dev"
r42_parent="$(mktemp -d /tmp/cyberlateral-r42-XXXXXX)"
uv run --project "$r42_component" --locked --offline python -B "$r42_component/tools/scenario_explore.py" --seed 42 --cases 4 --steps 128 --output "$r42_parent/one"
```

seed/cases/steps/output은 모두 필수입니다. seed0..4294967295, cases1..16, steps16..256이며 최대4096samples입니다. Python API는 builtin int만 받으며 bool·수치 문자열·float·int subclass는 받지 않습니다. CLI의 정수 token은 argparse를 통해 int가 됩니다. `--input`, `--r`, `--dt`, vehicle 설정, 자동 기본값은 없습니다.

정상 실행은512 model/512 selected-source reference steps, MATCH/exit0입니다. unit/gate의 추가 합성 작업은 별도 NONZERO이며 이 숫자를 전체 작업량으로 사용하지 않습니다. 테스트/참조는 기존 격리 worker에서 실행됩니다. frontend와 generator 자체는 public 모델/NumPy/native를 import하지 않습니다.

## 무엇을 생성하나

Generator V1의 각 case 첫16samples는 요청 부호 전환, signed zero, `0.5/scale`·`1.5/scale`과 binary64 인접 값, fractional/opposing driver 입력, abs-angle85 주변, 비활성화/재활성화를 조합합니다. 나머지 입력은 유한 catalog에서 선택합니다. 부동소수 `0.5/scale` 표현 자체가 모든 scale에서 수학적 정확 half-tie라는 보장은 없으며 실제 quantization 결과는 기존 모델/참조가 계산합니다.

선택 인덱스는 ASCII `<generator_id>:<seed>:<zero_based_case>:<offset>:<channel>`의 SHA256 첫8bytes를 big-endian 정수로 읽고 catalog 길이로 나눈 나머지입니다. process-global random/시간/파일 순서를 쓰지 않습니다. seed나 generator source가 바뀌면 같은 실험이라고 보지 않습니다.

순환 scale16/8/32/5와 한 개의 UP0 profile은 합성 stress 설정이지 차량 scale/r 정책이 아닙니다. 첫 case는 canonical index0 상태이고 나머지는 index5, previous_requested4/previous_applied-3, counter88/89/90을 명시한 합성 재개 상태입니다. 실제 이전 호출 이력을 관측했다는 뜻이 아닙니다.

`GENERATION.json`은 원형 입력 SHA·조건·actual input feature 수를 기록합니다. 양/음/zero/signed-zero 요청, 인접 nonzero sign 변화, fractional driver, inactive, abs-angle>=85, resumed case 수입니다. **입력 feature 수는 exhaustive branch coverage 또는 실제 모든 분기 실행 증명이 아닙니다.** 모든 원형 JSON은 기존 R31 parser로 전체 검증한 후 계산합니다.

## 결과와 재현

- `EXPLORATION.json`: 최종 상태·조건·source identity·계산량·차이·기존 closed gates.
- `GENERATION.json`, `generated/case-001.json` 등: 재현 가능한 생성 조건과 원형 입력.
- `workflow/batch/index.html`: 기존 R32 그래프·표와 전체 case 목록.
- `workflow/reference/SUMMARY_KO.md`: 기존 독립 선택-source 참조의 case별 판정.
- 비일치 case만 `reproducers/case-001.json` 등으로 **전체 원형 sequence**를 보존합니다. 처음 차이 전의 상태/입력이 중요하므로 임의 truncate/minimize하지 않습니다. 모든 비일치 case를 보존하며 참조 오류도 수치 차이와 분리합니다.

보존된 입력은 기존 R40으로 다시 실행할 수 있습니다.

```bash
uv run --project "$r42_component" --locked --offline python -B "$r42_component/tools/scenario_workflow.py" --input "$r42_parent/one/reproducers/case-001.json" --output "$r42_parent/reproduced"
```

동일 source/runtime과 같은 구현 결함이 있어야 같은 수치 문제가 재현됩니다. 저장값 변조·참조 worker 오류를 이용한 개발용 negative control은 입력 JSON만으로 그 변조/환경 오류까지 재생하는 기능이 아닙니다. 원래 complete 결과·차이·source identity도 함께 보존합니다.

## 판정과 실패

| 상태 | 의미 | exit |
|---|---|---|
| MATCH | 모든 생성 case 완료·전체 참조 일치·요청한 계산량 일치 | 0 |
| DIFFERENT | 기존 독립 참조가 실제 수치 field 차이를 발견 | 1 |
| ERROR | 참조 실행 오류·미완료/거절·상태/계산량 모순 | 2 |

사전 조건/출력 경로/worker/source·input 변경/IO 실패는 stderr `REJECTED: <code>`/exit2이며 root 완료 JSON을 만들지 않습니다. 부분 출력은 삭제/덮어쓰기/재개하지 않습니다. 실패한 참조 작업이 NONZERO일 수 있어 보고된 성공 reference 합계와 실제 총작업량을 같다고 주장하지 않습니다.0 matched case를 MATCH로 승인하지 않습니다.

출력 사전 점검의 미분류 OS/값 오류는 `EXPLORATION_IO`/exit2입니다.
기존 parameter 검증과 작은 합성 입력 생성이 먼저이며 출력 충돌·부모·encoding의
검사 순서는 유지합니다. 이 경계는 후속 parser/identity/worker 결함을 숨기지 않습니다.

내부 R39 stage JSON은 기존1MiB bounded/no-follow regular-file capture와 canonical parser로 읽고, 소비하는 필수 field·container·nullable count·helper count·case/report 결속을 모두 검증합니다. 누락 field, list/null/scalar root, 잘못된 case/helper 형태, duplicate key/nonfinite/비정규 JSON 등은 traceback 대신 `REJECTED: EXPLORATION_STAGE_RECORD`/exit2로 거절하며 root 완료 기록·부분 재현 subset을 게시하지 않습니다. 전체 R39 API를 재설계하는 loader가 아니며 소비하지 않는 추가 metadata는 허용합니다. 구조가 유효한 참조 오류·수치/계산량 모순의 기존 ERROR 판정은 유지합니다.

Root 완료 JSON은 마지막에 기록됩니다. 파일 존재만으로 성공을 판정하지 말고 canonical JSON과 모든 root/nested Manifest를 검산하세요. source/input 전후 비교는 협조적인 파일 관찰이며 atomic OS snapshot이나 출처 인증이 아닙니다.

## 두 회차 비교·보관 경계

같은 seed/cases/steps/source/runtime에서 generated JSON, GENERATION/EXPLORATION/SUMMARY와 batch portable bytes는 반복 일치합니다. 원래 complete workflow에는 개인 경로 receipt·로그가 있으므로 full Manifest가 다른 것은 가능합니다. 자동 업로드/ZIP/공유/기준 갱신은 없습니다. 완전한 batch의 저장값 회귀는 기존 R34를 사용합니다.

```bash
uv run --project "$r42_component" --locked --offline python -B "$r42_component/tools/scenario_explore.py" --seed 42 --cases 4 --steps 128 --output "$r42_parent/two"
uv run --project "$r42_component" --locked --offline python -B "$r42_component/tools/scenario_compare.py" --baseline "$r42_parent/one/workflow/batch" --candidate "$r42_parent/two/workflow/batch" --output "$r42_parent/comparison"
```

기대값은 R34 MATCH/512samples/차이0/새 모델0입니다. portable 부분 ZIP을 complete baseline으로 쓰지 않습니다. 저장값 일치는 독립 수치 참조 검사와 다른 개념입니다. 허용오차·차이에 맞춘 튜닝·r=0 fallback은 없습니다.

## 유지 제한

한정 합성 선택-source parity이며 전체 Controller·물리 차량 안전/성능·실제 이력 인증이 아닙니다. 호출 index는 elapsed time·10ms·100Hz가 아닙니다.

실제r/T2/vehicle scale=null, R_BUDGET=UNRESOLVED, Static Evidence Gate=FAIL, SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime=NO_GO, D2=PERFORMANCE_NOT_EVALUATED, F19=LEGACY_UNRESOLVED, NATIVE_EXACT_REPLAY=NOT_PROVEN, F70UH/V/F71=NOT_ALLOWED 유지. F61·실제r/dt·Controller·차량 Runtime·CAN·실차 input/활성화·후보 성능 평가는0입니다.
