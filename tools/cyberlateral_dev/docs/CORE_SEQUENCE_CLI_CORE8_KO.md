# CORE8 — 고정 합성 시퀀스 실행·결과 저장

CORE3~7 DEV API를 명령 한 번으로 실행하고 INPUT.json, RESULTS.json,
SHA256SUMS.txt를 저장한다. **고정 합성 예제 세 개만** 지원한다. 실제 차량·raw 로그·
임의 JSON reader가 아니며 외부 입력, r/T2/scale 옵션은 받지 않는다.

## 실행

기존 개발 환경의 `tools/cyberlateral_dev` 폴더에서 실행한다. 기존 환경을 재설치하거나
STEP7/차량 폴더에 설치하지 않는다. 출력은 checkout 밖의 **새 폴더**여야 한다.

```bash
demo_parent=$(mktemp -d)
.venv/bin/python -I -B tools/core_sequence.py --case sign-cycle --output "$demo_parent/sign-cycle"
```

동일한 demo_parent 아래에서 다른 예제도 실행할 수 있다. 같은 출력 폴더를 재사용하면
거절하며, 기존 결과를 지우거나 덮어쓰지 않는다.

```bash
.venv/bin/python -I -B tools/core_sequence.py --case declared-difference --output "$demo_parent/declared-difference"
.venv/bin/python -I -B tools/core_sequence.py --case late-invalid --output "$demo_parent/late-invalid"
```

두 번째/세 번째 명령은 의도적으로 exit 1/2다. `set -e`를 켠 script에서는 예상 exit를
별도로 처리해야 한다. CLI stdout의 canonical JSON 요약과 저장 RESULTS.json을 확인한다.
출력 위치를 명시하므로 절대 script 경로로 다른 cwd에서도 실행할 수 있다.

| case | 기대 결과 | public 합성 step | exit |
|---|---|---:|---:|
| sign-cycle | 세 전이 모두 MATCH | 3 | 0 |
| declared-difference | 첫 전이 DIFFERENT, 후속 두 전이 MATCH | 3 | 1 |
| late-invalid | SEQUENCE_INPUT:2:MODEL_DRIVER, 전체 사전 거절 | 0 | 2 |

작업 실패도 exit2일 수 있다. **저장된 REJECTED 진단**은 세 번째 fixture의 사전 거절이며,
stderr의 운영 실패/불완전 폴더와 구분한다. step0은 validation/이전 요청 양자화까지
전혀 없었다는 뜻이 아니다. 정상/불일치에서는 합성 모델 계산을 실제 수행한다.

## 저장값과 무결성 확인

- INPUT.json: 고정 fixture의 모든 frame/context. 요청 bytes는
  requested_binary32_be_hex, driver/angle은 정확한 binary64 hex로 저장한다.
  선언된 시각과 요청/제한 상태, 별도 flags/settings 역할을 그대로 보존한다.
- RESULTS.json: MATCH/DIFFERENT/REJECTED, 완료 여부, 정확한 rejection code,
  전이별 entry/computed/saved 상태와 차이, counts, 로컬 소스 관찰값, 유지 Gate.
- SHA256SUMS.txt: 앞 두 파일의 SHA256. 파일 집합은 세 개가 전부다.

```bash
cd "$demo_parent/sign-cycle"
sha256sum -c SHA256SUMS.txt
```

추가/누락 파일이 없는지도 확인한다. 체크섬은 bytes 무결성 검사이지 서명·출처 인증이
아니다. 파일 하나의 존재나 exit 값만으로 package를 인증하지 않는다. source가 같으면
새 폴더에 반복한 세 파일은 byte-identical이며, portable 파일에 출력/실행/cache 절대
경로나 생성 시각을 넣지 않는다. 이 도구는 saved package reader/서명 verifier가 아니다.

기존 runtime/source loader를 사용해 CPython3.12.13 Linux 및 고정 모델 bytes/version/
origin을 확인하고 계산 전후 소스 관찰값을 비교한다. CLI bytes SHA도 기록한다.
이는 **로컬 개발 소스 관찰**이며 차량 배포본, 실제 소비 설정, 물리 한계의 authority가
아니다. CLI만 빈 private pycache prefix를 사용하고 종료 시 복구한다. in-process API는
이미 import된 모듈을 격리/재검증하는 security sandbox가 아니다.

## 실패·범위 경계

case/output 검증은 model load/계산 전에 한다. 기존 파일/폴더·dangling symlink,
symlink parent, 없는 parent, checkout 내부 출력, 잘못된 UTF8/NUL path는 거절한다.
세 고정 파일을 새 폴더에 exclusive 생성하고 Manifest를 마지막에 쓴다.
운영 중 IO 실패 시 부분 새 폴더는 보존하며 자동 삭제/재시도/resume하지 않는다.
이 경우 prefix/부분 작업은 비영일 수 있고 완성 package라고 주장하지 않는다.
동시 파일시스템 공격을 막는 sandbox나 atomic rollback도 제공하지 않는다.

`DemoError.code`는 DEMO_CASE, DEMO_OUTPUT_EXISTS/PARENT/LOCATION/PATH,
DEMO_SOURCE:&lt;기존 code&gt;, DEMO_SOURCE_CHANGED,
DEMO_CHECK_FAILED_WORK_MAY_BE_NONZERO,
DEMO_PUBLICATION_FAILED_WORK_MAY_BE_NONZERO 등이다. 계산 중 오류를 사전 거절 step0으로
바꾸지 않는다. 예상하지 못한 API 오류는 전파되며 CLI는 고정 운영 오류/exit2로 보고한다.

검사는 [CORE7 선언 기반 진단](SYNTHETIC_SEQUENCE_CORE7_KO.md)이다. 앞 계산값으로 다음
선언을 보정하지 않으며 first anchor/prehistory·전체 output/source/차량 성능 인증이
아니다. fixture scale16·driver1.5·표시된 시각은 예제 상수일 뿐 실제 차량 정책값이 아니다.

R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제 r/T2/vehicle_scale=null,
SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO,
D2=PERFORMANCE_NOT_EVALUATED, F19=LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY=NOT_PROVEN, F70UH/F70V/F71 및 실차 활성화=NOT_ALLOWED를 유지한다.
실제 입력·F61·Controller·Runtime·CAN 실행 및 실제 r 계산은 0이다.
