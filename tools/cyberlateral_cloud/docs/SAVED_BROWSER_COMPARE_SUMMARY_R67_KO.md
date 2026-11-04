# R67 — 저장 묶음 비교의 한국어 요약

R66의 같은 검산·바이트 비교 결과를 한국어 Markdown으로 읽는 기능입니다.
기본 JSON/API는 그대로이며, 브라우저나 모델을 새로 실행하지 않습니다.
설치·네트워크·HF 인증 없이 Python 표준 라이브러리만 사용합니다.

## 실행

R67이 포함된 checkout에서 기존 완료 폴더 두 개를 지정합니다.
고정 R64 복구 도구에는 이 기능이 없으므로 과거 복구 tool/source pins를
main/latest로 바꾸지 마세요. 원래 archive identity도 그대로 유지합니다.

```bash
python -B tools/cyberlateral_cloud/browser_compare.py \
  --baseline /workspace/EXISTING-browser-baseline \
  --candidate /workspace/EXISTING-browser-candidate \
  --format markdown
```

stdout은 UTF-8 Markdown입니다. 도구가 파일을 만들거나 입력을 수정하지는 않습니다.
저장하려면 두 입력 폴더 **밖의 새 파일**을 선택하세요. 닫힌 입력 폴더 안에 파일을
추가하면 다음 검산에서 거절됩니다. 기존 파일을 덮어쓰지 않도록 아래처럼
subshell의 `noclobber`를 사용할 수 있습니다. redirect는 caller가 수행하며 오류 때
빈 파일이 남을 수 있습니다. 빈 파일이나 부분 stdout을 완료 보고서로 취급하지 마세요.

```bash
(
  set -C
  python -B tools/cyberlateral_cloud/browser_compare.py \
    --baseline /workspace/EXISTING-browser-baseline \
    --candidate /workspace/EXISTING-browser-candidate \
    --format markdown > /workspace/NEW-comparison-summary.md
)
```

exit 1은 정상적인 차이 결과이므로 단순히 성공/실패로 합치지 마세요.
`--format json` 또는 옵션 생략은 기존 R66과 같은 JSON bytes를 출력합니다.
지원 형식은 소문자 `json`, `markdown` 두 개뿐입니다.

## 무엇을 읽는가

- 비교 상태와 비교·변경·불변 파일 수.
- baseline/candidate 각각의 원래 R60 상태, case 수, 실패 case 수,
  전체 실패 기록 수와 RESULT SHA256. 개별 실패 case가 0개인 전체 FAIL도 보존합니다.
- 모든 변경 파일의 정렬된 상대 경로, 양쪽 전체 SHA256과 bytes 크기.
  경로는 링크가 아니며 실제 파일 내용을 Markdown에 삽입하지 않습니다.
- 범위와 미해결 정책·실차 금지 조건.

| exit | 의미 | 화면 검사와의 관계 |
|---|---|---|
| 0 | 38개 소유 파일의 저장 바이트 MATCH | 동일한 FAIL도 MATCH. 새 화면 PASS 아님 |
| 1 | 양쪽 유효, 저장 바이트 DIFFERENT | 새 시각적 회귀·성능 저하 판정 아님 |
| 2 | 무효 입력 또는 형식 오류 | 비교 결과 아님. 요약 stdout 없음 |

무효 묶음은 stderr의 `REJECTED: BASELINE_BROWSER_BUNDLE_*` 또는
`REJECTED: CANDIDATE_BROWSER_BUNDLE_*`로 거절합니다. baseline부터 검사하며
부분·손상·symlink·크기 초과 등을 일반 DIFFERENT로 표시하거나 복구하지 않습니다.
옵션 오류는 argparse stderr로 표시합니다. 실패 Markdown은 따로 생성하지 않습니다.

## 읽기 보조물의 한계

`render_comparison_summary(result: dict) -> bytes`는 R66 결과의 소비 필드와
일관성을 확인하는 pure renderer입니다. standalone JSON-file 입력 기능은 없으며,
CLI는 `compare_saved_browser`를 한 번 호출한 그 결과만 요약합니다. 원본을 다시 열거나
기록된 수치/화면 판정을 재계산하지 않습니다. API에 임의로 조립한 dict를 전달해도
출처 인증이 되지는 않습니다. 요약 파일 자체에 별도 전자서명이나 Manifest가 없습니다.

`quality_assessment=NOT_PERFORMED`, `source_identity_reauthenticated=false`입니다.
이는 새 화면·픽셀 유사도·발행자 인증·수치 정답·실차 적격성 검증이 아닙니다.
양쪽 저장 snapshot은 순차적이며 atomic/concurrent-writer 보호가 없습니다.
비교 중 입력을 편집하지 마세요. [기존 R66 비교 범위](SAVED_BROWSER_COMPARE_R66_KO.md)와
[R64 무결성 검산 범위](SAVED_BROWSER_VERIFY_R64_KO.md)는 그대로 유지됩니다.

비교·요약의 새 브라우저/모델/F61/실제 r·dt/Controller/Runtime/CAN/차량 실행은 0입니다.
전체 unit/gate의 별도 합성 작업은 NONZERO/미집계입니다.
R_BUDGET=UNRESOLVED · Static Gate=FAIL · 실제 r/T2/scale=null · Candidate/Runtime NO_GO.
F70UH/F70V/F71 및 실차 활성화 NOT_ALLOWED.
