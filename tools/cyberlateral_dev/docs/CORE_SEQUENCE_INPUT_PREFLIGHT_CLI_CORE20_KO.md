# CORE20 저장 합성 입력 사전 검증 CLI

[CORE19 API](CORE_SEQUENCE_INPUT_PREFLIGHT_CORE19_KO.md)를 한 명령으로 실행한다.
기존 API·입력 규칙·canonical JSON을 그대로 사용하며 새 모델 실행 기능이 아니다.

## 사용

기존 tools/cyberlateral_dev 전용 환경에서:

```bash
.venv/bin/python -I -B tools/core_sequence_input_preflight.py \
  --input-root /absolute/saved-core8-case
```

스크립트와 Python 경로를 절대 경로로 주면 다른 cwd에서도 실행할 수 있다.
source 선택은 스크립트의 component ROOT/ROOT/src 기준이며 caller cwd 기준이 아니다.
입력은 INPUT.json/RESULTS.json/SHA256SUMS.txt 세 파일의 완전한 고정 CORE8 case다.
CORE17 root·ZIP·partial portable subset·임의 JSON/차량 로그는 입력 형식이 아니다.
공백 있는 경로는 shell에서 인용한다. 정확히 한 번, 비어 있지 않은 --input-root가
필수다. 줄임말·중복 root·--run·--output-root·--format·rate/T2/scale 옵션은 없다.
stdin을 JSON으로 읽지 않으며 --help는 API import/입력 접근 없이 도움말만 출력한다.

## exit와 출력

| exit | 의미 | stdout |
|---|---|---|
| 0 | 현재 입력 INPUTS_COMPATIBLE | CORE19 canonical JSON |
| 1 | 현재 입력 INPUTS_REJECTED | 거절 code가 포함된 CORE19 canonical JSON |
| 2 | 잘못된 사용법·저장 파일 오류·운영 실패 | 출력 전 실패라면 빈 값 |

exit는 과거 saved_status와 별개다. 정상적인 declared-difference 입력은 저장
DIFFERENT여도 exit0이다. 과거 REJECTED label인 유효 입력도 현재 호환이면0이다.
반대로 checksum이 맞는 저장 MATCH라도 driver 등이 현재 규칙 밖이면1이다.
late-invalid는 SEQUENCE_INPUT:2:MODEL_DRIVER를 포함한 정상 거절 receipt와 exit1이다.

사용법 오류의 stderr는 INPUT_PREFLIGHT_USAGE_NO_MODEL_EXECUTION, 저장 오류는
기존 INPUT_PREFLIGHT_SAVED:&lt;INSPECT code&gt;, 예상하지 못한 실패는
INPUT_PREFLIGHT_FAILED_NO_MODEL_EXECUTION으로 고정한다. raw argv/입력값/path를
진단에 덧붙이지 않는다. API 호출·serialization이 완료된 뒤 stdout을 쓰고 짧은 쓰기는
반복하며0/음수 진행은 실패로 처리한다. 전송한 prefix는 후속 stdout 실패 때 되돌릴 수
없으므로 JSON prefix만 보고 성공으로 판단하지 말고 exit도 확인한다.

도움말·진단도 실제 descriptor에는 버퍼를 거치지 않고 쓴다. 도움말 출력 실패는 운영
오류2이며, stderr 진단 자체를 전달할 수 없더라도2를 유지한다. 이때 진단 문구가
누락될 수 있다. 실패한 CLI 출력이 종료 시 다시 flush되어120으로 바뀌는 것을 막는다.
main 이전에 host가 이미 버퍼에 남긴 출력이나 host hook의 종료 부작용까지 보장하지 않는다.

stdout 저장이 필요하면 **입력 폴더 밖의 별도 경로**를 caller가 선택한다. 이 명령은
exclusive/atomic 저장 publisher가 아니다. shell redirection이 먼저 입력 파일을
truncate하는 것을 막지 못하며, 입력 내부로의 redirection은 지원하지 않는다.

## 쓰기·실행 경계

main의 인자 파서 생성부터 stdout까지 sys.dont_write_bytecode=True를 유지한다.
캐시/임시 디렉터리 생성과 gettempdir probe가 없으므로 TMPDIR/TEMP/TMP 또는 cached
tempfile.tempdir가 입력 내부여도 사용하지 않는다. sys.pycache_prefix와 temp 설정은
변경하지 않는다. 성공·거절·오류·help·중단 전파 모두 원래 bytecode flag와 sys.path를
복구한다. interpreter 시작/CLI module import 전후의 host hook까지 제어하는 sandbox는
아니므로 안내 명령은 -I -B를 사용한다. 동시/반복 CLI embedding 보장은 추가하지 않는다.

기존 CORE19가3파일을 한 번씩 bounded/read-only 캡처하고 소유 선언을 검증한다.
float 해석·이전 요청 양자화 검증은 NONZERO_NOT_AGGREGATED다. 명령의 신규 model/
reference/F61/실제 r-dt·Controller/Runtime/CAN/차량 실행은0이다. 전체 unit/gate의
합성 fixture 작업은 별도 비영이다. 입력 bytes/layout/mode는 수정하지 않지만 atime,
atomic snapshot, 적대적 alias/경로 경쟁, 갑작스런 중단의 stdout 내구성은 보장하지 않는다.

호환 판정은 저장 출력의 산술 진실·출처·현재 source·이전 실행·anchor/prehistory·
computed rollout·차량 성능 인증이 아니다. prepared/model/F61 constructor args도
출력하지 않는다. 실제 r/T2/scale=null, R_BUDGET=UNRESOLVED, Static Gate=FAIL,
Candidate/Runtime=NO_GO, F70UH/F70V/F71·실차 활성화=NOT_ALLOWED 유지.
