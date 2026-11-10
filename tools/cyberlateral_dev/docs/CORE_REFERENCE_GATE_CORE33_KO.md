# CORE33 — 여섯 참조 검증을 전체 개발 gate에 연결

[CORE32](CORE_REFERENCE_SUITE_CORE32_KO.md)의 명령과 계산식·벡터는 바꾸지 않는다.
기존 dev.py verify가 unit tests/static/자체 compile 뒤, wheel 작업 전에 기존 CLI를
개발 Python의 별도 프로세스에서 -I -B --run으로 두 번 실행한다. 임의 입력·차량 reader나
새 rate 정책은 없다. 정상 pair의 reported model19+19=38이며 전체 작업 총계는 아니다.

## 실행과 결과

repository root에서 기존 준비된 환경으로:

```bash
tools/cyberlateral_dev/.venv/bin/python -B tools/cyberlateral_dev/dev.py verify --output /tmp/YOUR_NEW_VERIFY_DIRECTORY
```

출력 경로는 반드시 새 경로여야 한다. 기존 경로를 삭제하거나 덮어쓰지 않는다.
자식 프로세스의 cwd는 호출자가 --output으로 지정한 경로를 resolve한 출력 폴더다.
컴포넌트 내부·외부 모두 가능하며 외부 cwd를 강제하지 않는다. 위 예시와 기록된
CORE33 acceptance는 외부 폴더를 사용했다. 이는 개발 tree를 사용하는 명령이며
cwd 위치만으로 installed-wheel 격리나 Python sandbox를 보장하지 않는다.
CORE33이 추가하는 파일은 core_reference_one.json/core_reference_two.json과 같은 이름의
.log 두 개다. JSON은 각 CLI의 stdout 원문,log는 기존 runner의 stdout+stderr다.
정상 CLI에는 stderr가 없으므로 각각 같은 bytes다. 최종 SUMMARY.json의
synthetic_core_reference_suite에 결과를 넣고 네 파일을 최종 SHA256SUMS.txt에 포함한다.
기존 gate의 top-level status는 그대로여서 기존 cloud consumer와 호환된다.

통과 조건은 두 출력이 단순히 서로 같은 것 이상이다. 각각10463bytes이며 SHA256이
6dba6db52bbaf8a5e602a4c2266a2e29908629f894683c67bcdb11adaf32dead여야 한다.
기준은 CORE32 봉인 ZIP의 acceptance-1/direct-receipt.json 원문이다.
ZIP SHA256은63fb38b5326ae689ff07fefa171557630b99b220337dc42c46718d33db525737다.
현재 출력에서 기준을 자동 생성·갱신하지 않는다. 같은 손상 결과 두 개,보기 형식 변경,
추가 field나 gate 승격도 거절한다. 이것은 pinned bytes 검사이지 새 JSON schema나
산술의 범용 validator가 아니다. 기준 변경은 별도 변경 관리와 검증이 필요하다.

## 판정과 작업량

정상 nested status는 CORE33_FIXED_REFERENCE_SUITE_GATE_PASS다. 호출당 case6,
audit6MATCH와 observed4MATCH/1DIFFERENT/1REJECTED를 구분한다. 의도된 차이·거절이
참조와 맞는 것이 정상이다. reported model19/call·38/pair,reference generation model0,
numeric preflight NONZERO_NOT_AGGREGATED이며 runtime attestation=false다.
이 수치는 전체 unit/gate 작업량을 합산한 값이 아니다.

첫 command가 실패하면 log를 보존하고 두 번째를 실행하지 않는다. exit0이어도 원문이
기준과 다르면 그 stdout JSON을 보존하고 중단한다. 두 번째가 실패하면 첫 JSON과
기존 log를 유지한다. 오류는 REFERENCE_SUITE_GATE_FAILED_WORK_MAY_BE_NONZERO이며
dev.py는 exit2다. retry/fallback/부분 성공은 없고 최종 SUMMARY/Manifest를 만들지 않는다.
기존 CORE32가 차이를 모두 처리한 뒤 exit1이면 여기서는 전체 gate 실패가 된다.
네 artifact 이름의 기존 file/dir/dangling symlink를 모두 선행 거절한다. xb write가
race 시 덮어쓰기를 막지만 atomic snapshot/rollback을 제공하는 것은 아니다.
BaseException은 전파하며 실패 전 합성 작업을0이라고 표시하지 않는다.

## 한계

개발 tree를 명시적으로 사용하는 CLI 검사다. -I는 임의 ambient 경로를 격리하지만
CLI 자체의 component/src 추가를 금지하지 않으며 installed-wheel 검증으로 표현하지 않는다.
기존 installed-wheel 검증은 별도로 유지된다. pure pair validator는 파싱/모델/참조 실행0이다.
실제 자식 프로세스의 실행량 계측은 별도 증거이지 returned summary 자체가 감시기는 아니다.
기존 subprocess runner의 trusted capture를 사용한다. hostile stdout size 제한·timeout·
process sandbox·현재 source 인증·전체수치/실차 적합성을 추가로 보장하지 않는다.
이 단계에서 cloud publication/CI/차량 실행을 열지 않는다.

실제 r/T2/scale=null,R_BUDGET UNRESOLVED,Static Gate FAIL,SOURCE_SCHEMA_UNQUALIFIED6000,
Candidate/Runtime NO_GO,D2 PERFORMANCE_NOT_EVALUATED,F19 LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY NOT_PROVEN,F70UH/V/F71·실차 활성화 NOT_ALLOWED.
실제 inputs/F61/Controller/Runtime/CAN/실제 r/dt0;합성 검증 작업은 비영이다.
