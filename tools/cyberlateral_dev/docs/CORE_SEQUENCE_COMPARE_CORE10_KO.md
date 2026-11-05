# CORE10 — 저장된 합성 패키지 사이의 차이 비교

CORE8가 만든 두 폴더를 [CORE9 검사](CORE_SEQUENCE_INSPECT_CORE9_KO.md)로 각각
검증한 다음, 저장된 INPUT.json/RESULTS.json의 모든 필드를 비교한다. 모델·reference·
F61 재실행, 실제 차량/log 입력, native/dt/r 산출 기능이 아니다.

## 실행

개발판 디렉터리에서 기존 Python 환경으로 실행한다. 예시 경로는 실제 CORE8 결과
폴더로 바꾼다. 새 예제 생성은 별도 [CORE8 안내](CORE_SEQUENCE_CLI_CORE8_KO.md)를 따른다.

```bash
python -I -B tools/core_sequence_compare.py --left /tmp/saved-core8/sign-cycle --right /tmp/saved-core8/declared-difference
python -I -B tools/core_sequence_compare.py --left /tmp/saved-core8/sign-cycle --right /tmp/saved-core8/declared-difference --format markdown
```

`--left`, `--right`가 필수이며 `--format json|markdown`만 선택 가능하다. 출력은
stdout뿐이고 `--output`/`--execute`는 없다. API는
`integration_tools.core_sequence_compare.compare_saved_sequences(Path(...), Path(...))`,
그 결과의 `render_comparison(result, 'json' 또는 'markdown')`이다. renderer는
comparator가 반환한 dict용이며 임의 외부 요약 파일의 validator가 아니다.

## 판정과 차이 항목

| exit | comparison_status | 뜻 |
| --- | --- | --- |
| 0 | SAVED_PACKAGES_IDENTICAL | 검증된 저장 기록이 같다 |
| 1 | SAVED_PACKAGES_DIFFERENT | 저장 기록에 차이가 있다 |
| 2 | 요약 없음 | 인자·패키지·작업 오류 |

저장된 DIFFERENT나 REJECTED를 자기 자신과 비교하면 정상 exit0이다. 이는 새 계산의
MATCH나 저장된 거절의 해제가 아니다. 왼쪽이 정답/승인 baseline이라는 뜻도 아니다.
출력의 left/right.saved_status와 comparison_status는 별개로 읽어야 한다.
오류는 `COMPARE_LEFT:INSPECT_*`, `COMPARE_RIGHT:INSPECT_*`로 구별한다.
일반 작업 오류는 고정 `COMPARE_OPERATION_FAILED`다. stdout 장치가 쓰기 도중
실패하면 이미 전달된 일부 bytes는 되돌릴 수 없다. exit2 출력은 성공 요약이 아니다.

차이는 INPUT, RESULT, IDENTITY로 나눈다. IDENTITY는 저장된 opaque metadata의
차이이지 현재 소스 확인/과거 생산자 인증이 아니다. CORE9 요약에서 생략된 입력과
metadata도 비교하며 caller의 폴더 위치는 비교하지 않는다. metadata 자체의 경로
문자열은 저장 데이터이므로 차이로 나타날 수 있다.

path는 `/INPUT.json/...` 또는 `/RESULTS.json/...`로 시작하는 JSON Pointer다.
key의 `~`는 `~0`, `/`는 `~1`로 표시한다. dict key는 정렬하고 배열은 **위치 기준**으로
비교한다(model index 정렬/LCS/시퀀스 원인 분석 아님). `false`와 `0`은 TYPE_CHANGED다.
LEFT_ONLY/RIGHT_ONLY는 left_present/right_present로 누락을 구별하며 실제 null과
혼동하지 않는다. 값/타입 변경은 VALUE_CHANGED/TYPE_CHANGED다.

상세는 deterministic 순서의 첫256개만 보존한다. difference_count와
difference_counts는 전체 차이 수다. reported_difference_count와
differences_truncated를 반드시 확인한다. 잘려도 차이 판정과 exit1은 유지한다.
Markdown은 HTML/표/코드 구분자·제어문자를 escape한다. 브라우저 화면 검증은 아님.

## 읽기 전용·근거 한계

각 side는 고정 세 파일을 한 번씩 열어 확보한 bytes만 검증/비교한다. 검증 후 파일을
다시 열지 않는다. 같은 경로를 두 번 지정해도 각 side를 따로 캡처한다. 협조적
파일시스템 기준이며 atomic snapshot/hostile race/atime 불변 보장이 아니다.
원본 파일/이름 집합/권한은 변경하지 않지만 읽기로 atime이 바뀔 수 있다.
CORE9의 크기·canonical JSON·타입/저장 관계·닫힌 Gate 검사가 모두 유지된다.

산술/거절 사유의 진위·원본 출처·현재 source·성능은 인증하지 않는다. 저장 기록과
checksum을 일관되게 조작하면 검사를 통과할 수 있다. 신규 모델/reference 실행0은
조회/비교에 한정하며 unit/gate/fixture 준비의 합성 작업은 nonzero다.
CORE9 direct validator의 tuple 수용 Minor는 이 변경에서 해결하지 않았다.
JSON 파일 경로는 builtin container로 읽으므로 해당 직접 호출 문제와 구분한다.

유지: R_BUDGET=UNRESOLVED, Static Evidence Gate=FAIL, 실제 r/T2/scale=null,
SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO,
D2=PERFORMANCE_NOT_EVALUATED, F19=LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY=NOT_PROVEN, F70UH/F70V/F71·실차 활성화=NOT_ALLOWED.
