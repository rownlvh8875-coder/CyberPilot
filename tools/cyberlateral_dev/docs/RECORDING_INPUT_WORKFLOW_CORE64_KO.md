# CORE64 — 합성 입력 진단 결과의 덮어쓰기 없는 저장

기존 [CORE61 입력 생성 예제](RECORDING_INPUT_CLI_CORE61_KO.md)의 첫 Python block으로
새 외부 임시 폴더에 `INPUT.json`을 만든다. 그 안내의 stdout 명령 대신 아래를 실행한다.
이 명령은 **명시적 합성 모델 실행**이며 차량/실제 로그 입력 명령이 아니다.

```bash
core64_input_sha=$(sha256sum "$CORE61_EXAMPLE_DIR/INPUT.json" | cut -d ' ' -f 1)
.venv/bin/python -B tools/recording_input_workflow.py --run \
  --input-file "$CORE61_EXAMPLE_DIR/INPUT.json" --expected-sha256 "$core64_input_sha" \
  --output-root "$CORE61_EXAMPLE_DIR/saved"
```

`saved`는 없어야 하며 부모는 이미 존재해야 한다. 실행 후 정확히
`DIAGNOSTICS.json`, `SHA256SUMS.txt` 두 파일이 생긴다. stdout은 저장 영수증이며
예제는 `diagnostic_status=MATCH`, exit0,2frames/1transition/1새 합성 step이다.
결과 행의 computed state는 index6/requested8/applied2/counter5다.

```bash
(cd "$CORE61_EXAMPLE_DIR/saved" && sha256sum -c SHA256SUMS.txt)
```

같은 목적지로 다시 실행하면 기존 파일을 보존하고 모델0으로 exit2 거절한다.
다른 새 목적지에서는 명시적으로 합성 모델을 다시 실행한다. 같은 입력이라면
두 파일과 영수증 bytes는 동일하지만, 이는 전체 테스트2회 재현성이나 원본 인증이 아니다.

## 계약과 실패

- 기존 CORE61 stdout CLI/API·codec·계산 코드는 그대로다. 새 저장 명령만 추가한다.
  `--run`, `--input-file`, `--expected-sha256`, `--output-root`는 각각1회 필수다.
  축약/중복/빈 값/잘못된 SHA/알 수 없는 옵션은 project import나 모델 없이 거절한다.
- SHA 문법 검사→출력 경로 사전 검사→단일 입력 캡처/SHA/전체 사전 검증→기존
  진단1회→전체 JSON/영수증 직렬화→exclusive 저장/전체 readback 순서다.
  파일/입력·의미 오류는 모델 prefix0, 기존/부적법 목적지도 모델0이다.
- 결과가 DIFFERENT여도 모든 행과 차이를 그대로 저장하며 exit1이다. 선언된
  이전 상태를 계산 결과로 고치지 않고, 이후 진단을 생략하지 않는다.
- 새 외부 폴더만 받으며 현재 checkout 내부/없는 부모/symlink 목적지는 거절한다.
  입력 원문은 복사하지 않는다. 원본은 호출자가 SHA와 함께 별도로 보존해야 한다.
- 디렉터리0700/파일0600을 요청하고, 덮어쓰기나 자동 삭제/재시도는 하지 않는다.
  저장·검산 실패 시 부분 폴더가 남을 수 있다. fsync/전원 장애 내구성/atomic
  transaction/악의적인 경로 교체 방어를 보장하지 않는다.
- MATCH0/DIFFERENT1은 **저장까지 성공했을 때**다. 나머지는 exit2와 고정 code다.
  저장 후 stdout 실패라면 완전 파일이 남아 있어도 CLI는 실패다. 일부 stdout
  prefix는 되돌릴 수 없으므로 exit2 영수증을 성공으로 사용하지 않는다.
  늦은 실패에 이미 발생한 합성 작업은 있을 수 있으며0으로 주장하지 않는다.
- 기존 파일/입력/검산 code는 그대로 쓰고, 일반 실패는
  `RECORDING_WORKFLOW_FAILED_DIRECTORY_MAY_EXIST_WORK_MAY_BE_NONZERO`다.
  경로나 원문 예외를 stderr로 유출하지 않는다. 캐시/temp 생성 없이 main의
  sys.path/bytecode 설정을 복원한다. Linux/Python3.12 개발 tree 명령이다.

저장 MATCH는 origin/source/첫 anchor/prehistory/독립 산술/차량 성능 인증이 아니다.
실제 r/T2/scale=null,R_BUDGET UNRESOLVED,Static Gate FAIL,Candidate/Runtime NO_GO,
F70UH/F70V/F71 NOT_ALLOWED를 유지한다. 실제 input/capture/Controller/Runtime/CAN/
F61/actualdt/r/install/deploy0이며 전체 합성/model/reference/numeric 작업은 비영/미집계다.
