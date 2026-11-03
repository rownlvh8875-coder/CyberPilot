# R44 — 저장된 여러 seed 캠페인 비교

두 개의 **완전한 R43 V1 폴더**를 읽어 전체 회귀를 비교하는 별도 DEV 명령입니다.
R43를 다시 실행하거나 새 모델/참조 worker를 호출하지 않습니다. 전체 원형 자료와
private receipt/log가 있는 complete 결과가 필요하며 portable subset은 입력이 아닙니다.

## 실행

CPython3.12.13/Linux binary64의 기존 DEV 환경에서 사용합니다. 아래 두 입력 경로는
이미 생성된 R43 캠페인 root로 바꾸세요. 출력은 부모가 존재하는 새 외부 경로여야 합니다.

```bash
r44_component="$PWD/tools/cyberlateral_dev"
r44_parent="$(mktemp -d /tmp/cyberlateral-r44-XXXXXX)"
uv run --project "$r44_component" --locked --offline python -B "$r44_component/tools/scenario_campaign_compare.py" \
  --baseline /absolute/saved-campaign-one --candidate /absolute/saved-campaign-two \
  --output "$r44_parent/compare"
```

세 flag 모두 필수입니다. `candidate`는 비교 대상 저장 폴더이지 차량 후보 평가가 아닙니다.
자동 기준 갱신·허용오차·업로드·공유·설치·r/dt/차량 입력 옵션은 없습니다.
입력/출력의 symlink·기존 출력·component/입력 내부 출력은 거절하며 입력은 수정하지 않습니다.

## 무엇을 비교하는가

seed와 case는 **저장된 명시 순서**로 대응합니다. 이름으로 정렬하거나 누락한 run을
zip으로 버리지 않습니다. 조건·run 추가/삭제·저장 상태/참조 판정/계산량/전체 findings와
R34의 입력·명령·상태·trace를 비교합니다. 입력이 바뀐 case를 동일 입력 sample 수에
넣지 않습니다. producer identity 변화는 별도로 표시하며 값 MATCH가 identity 일치는 아닙니다.
참조 보고서의 첫 차이/총수뿐 아니라 보존된 상세 전체와 expected digest도 비교합니다.
입력 결속 hash·producer identity·고정 runtime metadata는 값 차이와 분리합니다.

`regression_status`는 저장된 기록의 차이가0이면 MATCH입니다. 전체 `status`는
원본 캠페인 중 ERROR가 있으면 ERROR, DIFFERENT가 있거나 회귀 차이가 있으면 DIFFERENT,
그 외에만 MATCH입니다. 동일한 실패 기록을 두 번 읽어도 전체 성공으로 바꾸지 않습니다.

| 전체 status | exit | 의미 |
|---|---|---|
| MATCH | 0 | 두 원본 MATCH, 저장된 조건/값/판정 차이0 |
| DIFFERENT | 1 | 원본 DIFFERENT 또는 저장 회귀 차이 존재 |
| ERROR | 2 | 유효하게 완료된 원본에 참조 ERROR 존재 |

손상·모순·불완전 입력/IO/늦은 입력·source 변경은 `REJECTED: CAMPAIGN_COMPARE_*`/exit2입니다.
완료된 ERROR 비교에는 최종 record가 있지만, 거절/미완료에는 유효한 완료 record가 없습니다.
초기 invalid input은 출력 폴더를 만들지 않고, publication 실패의 부분 파일은 보존합니다.

직접 Python API `run_campaign_comparison(baseline: Path, candidate: Path, output: Path)`의
초기 경로 검사도 예상 가능한 파일시스템 오류·잘못된 경로 값은
`CampaignCompareError(code='CAMPAIGN_COMPARE_IO')`로 거절합니다. 기존 출력·부모·위치·
encoding/runtime의 구체적인 거절 코드는 유지하며, 이 시점에는 입력/source를 읽거나
출력을 만들지 않습니다. 원래 예외는 API의 cause에 보존하지만 CLI는 경로/내부 오류
상세를 출력하지 않습니다. 잘못된 호출 형식 같은 프로그래머 `TypeError`를 숨기는
범용 예외 처리 계약은 아닙니다. 공유 R34 도구의 별도 API 동작은 변경하지 않습니다.

## 결과

- `CAMPAIGN_COMPARE.json`: 전체/회귀/원본 판정, 조건과 source record/identity hashes,
  정확한 차이 수·최초 차이·최대256 상세, 비교 sample 수, 오류·비일치 run, 닫힌 gates.
- `comparisons/seed-NNN/COMPARE.json`: 각 paired run의 기존 R34 전체 비교 결과.
  추가/삭제 run에 가짜 batch를 만들지 않습니다.
- `SUMMARY_KO.md`: source-aware 요약과 child 비교 링크.
- `RECEIPT.json`: private 경로·관찰 runtime·comparator source hashes·원본 Manifest 결속.
- root/nested `SHA256SUMS.txt`: 실제 전체 결과의 closed Manifest.

모든 다른 파일을 쓴 뒤 완성된 임시 record를 같은 filesystem의 exclusive link로
게시합니다. 부분 marker 쓰기나 관찰된 입력 변경으로 성공 파일을 만들지 않습니다.
이 link가 완료 시점입니다. 이후 임시 폴더/cache 정리의 IO 실패는 경고하며 이미 완료된
결과/exit 판정을 publication 실패로 바꾸지 않습니다.
전체 폴더의 원자적 OS snapshot·fsync/crash durability를 제공한다는 뜻은 아닙니다.
완료 파일 존재만 보지 말고 canonical record·판정·모든 Manifest를 함께 검산하세요.

같은 입력/code/runtime의 path-free 비교 record와 요약은 재현 가능합니다. private
receipt/log 경로 때문에 전체 Manifest는 다를 수 있습니다. 부모 상세256 제한과
개별 R34 상세256 제한은 차이 **총수**를 줄이지 않습니다.

## 검증과 한계

R43 child/root·R34 complete batch·canonical JSON·nested/portable hash·수치/상태/참조
기록의 결속을 재검산합니다. R40 workflow의 고정 경로·no-baseline 조건과 VALIDATION의
실제 입력 결속도 검사합니다. R43 V1의 deterministic 입력/feature 생성 규칙은 메모리에서
재검산하지만 모델/참조 산술을 실행하지는 않습니다. 현재 V1 외의 새 generator/layout을
자동으로 허용하는 loader가 아닙니다. 상한은 input별8192files/512MiB,16MiB/file/depth16,
child별2048files/128MiB이며 최대 크기의 속도/메모리 성능 검증은 별개입니다.

입력 전후 hash와 source identity 관찰은 cooperative 검증이지 적대적 순간 교체를 막는
OS snapshot이나 hard-link 소유권·출처 인증이 아닙니다. 재봉인된 일관성만으로 과거
참조 수치 판정이 참인지 새로 입증할 수 없습니다. 원본의 계산량은 과거 기록이며 새 실행이 아닙니다.

비교의 새 모델/참조/F61/실제r/dt·Controller·차량 Runtime·CAN·실차 input/후보 평가는0입니다.
unit fixture/full gate는 별도의 NONZERO 합성 작업을 실행하며 총합 미집계입니다.
R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제r/T2/vehicle scale=null,
Candidate/Runtime NO_GO, F70UH/F70V/F71과 실차 활성화 NOT_ALLOWED 유지입니다.
