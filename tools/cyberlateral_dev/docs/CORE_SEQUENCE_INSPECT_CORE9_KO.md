# CORE9 — 저장된 합성 시퀀스 조회

CORE8가 저장한 `INPUT.json`, `RESULTS.json`, `SHA256SUMS.txt` 세 파일의
captured bytes와 저장 관계를 읽기 전용으로 검사한다. 모델·reference·F61을
import/실행하거나 명령·native·dt·r을 재계산하지 않는다. 차량 로그 reader가 아니다.

## 사용

개발판 디렉터리에서 기존 Python 환경으로 실행한다. 입력은 CORE8가 만든 폴더다.
경로 예시는 실제 저장 위치로 바꾼다. 새 실행이 필요하면 별도
[CORE8 안내](CORE_SEQUENCE_CLI_CORE8_KO.md)를 따른다.

```bash
python -I -B tools/core_sequence_inspect.py --input /tmp/saved-core8/sign-cycle
python -I -B tools/core_sequence_inspect.py --input /tmp/saved-core8/sign-cycle --format markdown
```

출력은 stdout만 사용한다. `--output`, `--execute`, arbitrary input 실행 옵션은 없다.
API는 `integration_tools.core_sequence_saved.inspect_saved_sequence(Path(...))`,
`format_saved_sequence(Path(...), 'json' 또는 'markdown')`이다.
`InspectError.code`와 예외 문자열은 raw 입력 없는 고정 코드다.

## 판정과 한계

- exit0: 저장 패키지 검사가 성공했다. `saved_status`는 MATCH, DIFFERENT,
  REJECTED 모두 가능하다. **새 계산의 MATCH가 아니다.**
- exit2: 파일/체크섬/형식/저장 관계/인자/작업 오류. 요약을 출력하지 않는다.
  stdout 장치 자체가 쓰기 도중 실패하면 이미 전달된 일부 bytes는 되돌릴 수 없으며,
  exit2와 고정 작업 오류를 반환한다. 완전한 성공 출력으로 사용하지 않는다.
- 저장된 `recorded_model_steps`는 과거 기록이다. 이번 조회의
  `inspection_model_executions`, `inspection_reference_executions`는 각각0이다.
  unit/gate의 fixture 준비와 합성 검증 실행은 별도이며 nonzero다.

파일 이름·개수·일반 파일 여부·크기 상한을 검사한다. symlink root/부모/member,
FIFO, 추가 파일/디렉터리를 거절한다. 고정된 세 이름을 directory fd 기준으로
각각 한 번 열어 bounded bytes를 확보한다. Manifest의 경로를 따라가지 않는다.
INPUT/RESULTS 체크섬을 먼저 검사한 뒤 strict UTF8, 중복 key·float token·비정상
상수·과도한 깊이/정수 길이 거절과 canonical JSON 검사를 수행한다.

소비하는 스키마·정확한 타입·frame/state 링크·행 차이·집계·닫힌 Gate를 검사한다.
명령 비교는 저장 정수끼리만 수행한다. declared entry와 computed result는 다른
역할이며 DIFFERENT 다음 행에 computed 명령을 주입하지 않는다.
REJECTED는 저장된 preflight 오류와 zero-work 구조만 표시한다.

이 검사는 **캡처한 bytes의 checksum과 저장 관계**에 한정된다. checksum까지
일관되게 바꾼 기록은 통과할 수 있다. 기록된 산술·거절 사유가 사실인지, 원본
출처·현재 소스·배포본·차량 기능은 인증하지 않는다. source identity는 저장
metadata이며 현재 checkout과 비교하지 않는다. anchor/prehistory는 미검증이다.
파일시스템 전체의 atomic snapshot, 악의적 race/bind mount sandbox가 아니다.
입력 bytes/파일 집합/권한은 수정하지 않지만 읽기로 인한 filesystem atime은 보장하지 않는다.

유지: R_BUDGET=UNRESOLVED, Static Evidence Gate=FAIL, 실제 r/T2/scale=null,
SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO,
D2=PERFORMANCE_NOT_EVALUATED, F19=LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY=NOT_PROVEN, F70UH/F70V/F71·실차 활성화=NOT_ALLOWED.
조회 성공으로 Gate·권한·정책을 승격하지 않는다.
