# R66 — 저장된 브라우저 묶음 두 개의 정확한 바이트 비교

이미 저장된 완료 묶음 두 개를 각각 R64 규칙으로 검산한 뒤, 검증한38파일의
원래 bytes를 비교합니다. 브라우저·화면·모델을 다시 실행하지 않습니다.
표준 라이브러리만 사용하며 설치·네트워크·HF 인증·입력 쓰기가 없습니다.

## 실행

새 비교 도구가 포함된 Git checkout에서 Linux의 일반 Python 진입을 사용합니다.
고정 R64 복구 tool commit `af4523c05c24ea2c9368a869c0cf9f4df0f54590`에는
이 명령이 없습니다. [고정 복구 안내](RECOVERY_R64_KO.md)의 tool/source pins나
원래 archive identity를 새 문서/main commit으로 바꾸지 마세요.

```bash
python -B tools/cyberlateral_cloud/browser_compare.py \
  --baseline /workspace/EXISTING-browser-baseline \
  --candidate /workspace/EXISTING-browser-candidate
```

둘 다 기존 완료 폴더이며 같은 경로도 허용합니다. candidate는 비교할 저장 묶음이지
차량 candidate 승인이 아닙니다. ZIP·리포트 일부·과거/미래 형식은 자동 변환하지 않습니다.
JSON을 보존하려면 두 입력 폴더 밖의 새 파일을 사용하세요. 닫힌 입력 폴더 안에
stdout/debug 파일을 추가하면 형식 위반입니다. `python -I script.py`는 인접 모듈
경로를 포함하지 않아 지원 진입 방식이 아닙니다.

## 판정은 원래 화면 PASS/FAIL과 별개

- exit0 / `R66_SAVED_BROWSER_EXACT_BYTES_MATCH`: 소유 파일38개 bytes가 모두 같습니다.
- exit1 / `R66_SAVED_BROWSER_BYTES_DIFFERENT`: 양쪽은 유효하지만 일부 bytes가 다릅니다.
- exit2: 어느 한쪽이 손상·부분·지원하지 않는 형식·읽기 불가입니다. 일반 차이가 아닙니다.

동일한 FAIL 묶음끼리 비교해도 exit0입니다. 각 `baseline_verification`과
`candidate_verification`의 원래 `recorded_status=R60_BROWSER_SMOKE_FAIL`을
그대로 보존하며 `quality_assessment=NOT_PERFORMED`입니다. MATCH를 화면 PASS로,
DIFFERENT를 새로 판정한 시각적 회귀나 성능 저하로 취급하지 마세요.
각 묶음의 개별 판정이 필요하면 [R64 검산 명령](SAVED_BROWSER_VERIFY_R64_KO.md)을 사용합니다.

결과 schema1은 비교 파일 수·변경/불변 수와 정렬된 `differences`를 담습니다.
각 차이는 상대 `path`, 양쪽 `sha256`·`byte_size`를 담으며 원문 내용·절대 경로·시각은
추가하지 않습니다. 같은 저장 bytes에는 동일한 JSON을 출력합니다. 손상 시 stdout은
비어 있고 stderr는 `REJECTED: BASELINE_BROWSER_BUNDLE_*` 또는
`REJECTED: CANDIDATE_BROWSER_BUNDLE_*`입니다. baseline부터 검사하며 무효이면 중단합니다.

## 정확히 무엇을 비교하는가

API는 `compare_saved_browser(baseline: Path, candidate: Path) -> dict`입니다.
R64의 새 `load_saved_browser(root: Path) -> tuple[dict, dict[str, bytes]]`는 기존
receipt와 바로 그 검증된 snapshot을 반환합니다. 기존 `verify_saved_browser` API/
CLI/receipt는 유지됩니다. 비교하려고 검증 후 다른 bytes를 다시 읽지 않습니다.

기존 파일별8MiB·묶음32MiB 제한을 각각 적용합니다. 한 쌍의 saved bytes는 최대64MiB이며
이는 Python 전체 메모리 한도 주장이 아닙니다. regular-file/no-follow·정확한38파일/
7디렉터리·root/중첩 Manifest·strict JSON·원래 RESULT/요약 연결 검사를 재사용합니다.
손상·symlink·FIFO·누락·추가 파일·oversized 입력을 repair/fallback 없이 거절합니다.

모든 소유 파일이 대상입니다. 로그, Manifest, RESULT의 공백/JSON 표현도 무시하지 않습니다.
같은 RESULT를 가진 두 묶음이라도 log bytes가 다르면 DIFFERENT입니다. PNG도 원래 bytes만
비교하며 화면/픽셀 유사도를 해석하지 않습니다. 허용 오차·정규화·무시 목록은 없습니다.
따라서 환경별 로그나 JSON 표현 차이는 내용상 동등해 보여도 차이로 나올 수 있습니다.

`source_identity_reauthenticated=false`입니다. 저장된 source 기록의 발행자나 실제 실행,
child VIEW 수치, 물리 시간·차량 적격성을 인증하지 않습니다. 일관되게 위조·재봉인한
묶음을 배제하지 못합니다. 양쪽 snapshot은 순차적이고 atomic/concurrent-writer 보호가
없으므로 비교 중 입력을 편집하지 마세요. 자동 수정·삭제·새 요약/FAILURE 출력은 없습니다.

비교기의 새 모델/F61/실제r·dt/Controller/Runtime/CAN/차량 실행은0입니다. 기존 전체
unit/gate의 합성 작업은 별도 NONZERO/미집계입니다. R_BUDGET UNRESOLVED · Static Gate
FAIL · 실제r/T2/scale null · Candidate/Runtime NO_GO · F70UH/F70V/F71 및 실차 활성화
NOT_ALLOWED를 유지합니다.
