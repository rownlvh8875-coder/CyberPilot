# CORE28 — 고정 합성 rollout 실행·저장 명령

[CORE27](SYNTHETIC_SEQUENCE_ROLLOUT_CORE27_KO.md)을 명시적으로 실행하고 입력·결과·
체크섬을 새 외부 폴더에 보존한다. 기존 CORE7/CORE8의 선언 entry 진단은 바꾸지 않는다.
범용 파일 reader·차량 데이터·F61 calculator·실제 r/dt·차량 실행 명령이 아니다.

## 실행

tools/cyberlateral_dev의 기존 전용 환경에서,parent가 존재하고 출력 폴더는 없을 때:

```bash
.venv/bin/python -I -B tools/core_rollout_run.py \
  --case sign-cycle --run --output-root /absolute/NEW-rollout-folder
```

허용 case는 sign-cycle,declared-difference,late-invalid 세 개뿐이다.
각 --case/--output-root/--run은 정확히 한 번 필요하다. `--run`이 없으면 계산하지 않는다.
약어·중복·positional·check/외부 입력/format/rate 옵션은 거절한다.
Python API `integration_tools.core_rollout_run.run_rollout_case(case_id, output_root: Path)`도
이름대로 명시적인 실행 요청이며,조회 함수가 아니다.

| case | 결과 | public 합성 model steps | 종료값 |
|---|---|---|---|
| sign-cycle | MATCH | 3 | 0 |
| declared-difference | DIFFERENT | 3 | 1 |
| late-invalid | REJECTED | 0 | 2 |

late-invalid는 non-dyadic driver0.1을 사전 검증에서 거절하는 고정 예제다.
정상적으로 저장된 거절도 exit2이므로 **완전한 stdout receipt·result_status·exit를 함께**
확인한다. stderr 운영 오류2와 구분한다. 모델0이어도 사전 numeric validation은 비영이다.

## 저장 묶음과 receipt

- INPUT.json: CORE28_CLOSED_COMPUTED_ROLLOUT_INPUT_V1. 원래 frame/context를 보존하되
  요청 binary32는 requested_binary32_be_hex,driver/angle binary64는 *_hex로 저장한다.
- RESULTS.json: CORE28_CLOSED_COMPUTED_ROLLOUT_RESULT_V1. 첫 선언 seed·최종 계산 상태,
  선언 entry/전달 entry/계산 next state/선언 saved state를 분리한다. 각 row의 entry와
  saved-output 차이,전이 순번과 model index,모델 작업량·거절 사유·Gate를 기록한다.
- SHA256SUMS.txt: 앞의 두 파일을 이름순으로 기록하며 자기 자신은 제외한다.

전부 canonical UTF8 JSON/정확한 hex다. CORE8 schema나 기존 저장 reader 호환을 주장하지
않는다. 전체 projection/trace/steer-request는 이 형식에 내보내거나 비교하지 않는다.
별도 stdout receipt는 CORE28_CLOSED_COMPUTED_ROLLOUT_RUN_V1 /
COMPUTED_ROLLOUT_RUN_PUBLISHED이며,result_status/result_exit_code,실행 여부·완료·
model_steps,세 파일 SHA/size,권한 flags/Gates를 담는다. 네 번째 저장 파일이 아니다.
저장 완료가 입력 호환·실차 PASS라는 뜻은 아니다. 같은 case의 파일과 receipt는 다른
NEW 경로에서도 동일 bytes다. 경로·현재 시각·현재 source 인증은 넣지 않는다.

## 순서와 오류 보존

1. 고정 case를 output 경로보다 먼저 확인한다.
2. CORE16 _output으로 NEW 외부 경로를 확인한다. 기존 빈/완전 폴더도 입력 조립·모델 전에 거절한다.
3. 고정 case를 한 번 조립하고 INPUT encoding을 모델 실행 전에 완료한다.
4. CORE27을 한 번 호출한다. 정상3steps 또는 사전 거절0steps이며,실행 오류를 정상 거절로 바꾸지 않는다.
5. 결과와 checksum을 모두 직렬화한 뒤 CORE16 _publish로 저장·bounded readback한다.

기존 저장기의 exclusive/nofollow,regular-file/size/전체 bytes/fileset/root identity 검사를
재사용한다. 요청 mode는 폴더0700·파일0600이며 실제 권한은 umask/환경 영향을 받는다.
symlink·없는 parent·잘못된 경로·현재 checkout 안의 출력은 거절한다.

ROLLOUT_RUN_CASE는 잘못된 case,ROLLOUT_RUN_INPUT_ENCODING은 모델 전 encoding 오류다.
출력 사전 검증은 원래 ARCHIVE_WORKFLOW_* code를 보존한다.
ROLLOUT_RUN_EXECUTION_FAILED_WORK_MAY_BE_NONZERO는 계산 실패,
ROLLOUT_RUN_RESULT_FAILED_WORK_MAY_BE_NONZERO는 계산 후 결과 encoding 실패다.
ROLLOUT_RUN_PUBLICATION:<원래code>:WORK_MAY_BE_NONZERO는 저장·검산 실패다.
이 오류에서 모델·실패 prefix가 이미 실행됐을 수 있으며 성공 receipt를 내보내지 않는다.
뜻밖의 내부 예외는 API에서 전파한다. CLI 사용법은 ROLLOUT_RUN_USAGE_NO_MODEL_EXECUTION,
그 밖의 운영 실패는 ROLLOUT_RUN_FAILED_WORK_MAY_BE_NONZERO_DIRECTORY_MAY_EXIST/2다.
raw caller 경로나 예외 원문은 CLI 진단에 노출하지 않는다.

자동 삭제·retry·덮어쓰기를 하지 않는다. 실패하면 폴더가 없거나 빈/부분/완전 상태일 수 있다.
특히 저장 뒤 stdout 실패에도 완전한3파일이 남을 수 있고 이미 출력된 prefix는 회수할 수 없다.
오류가 곧 계산0·출력 없음이라는 뜻은 아니다. 실패 산출물은 조사용으로 보존한다.
동일 출력으로 재실행하면 모델 전에 거절한다. Shell redirection으로 원본을 덮어쓰는 위험은 별도다.

## 범위

CLI main은 parser부터 출력까지 bytecode 억제·원래 flag/path 복원,temp/cache/probe0이다.
초기 import는 caller-managed이므로 예제는 -I -B다. 저장3파일/폴더/검산은 명시적인 I/O다.
합성 model/quantizer 작업은 비영이며,전체 unit/gate fixture 작업은 별도로 비영이다.
기존 모델·CORE27·저장기·wheel은 변경하지 않는다. 첫 seed/이전 이력/출처/원래 산술/
실제 native replay/차량 동역학·성능·배포 적합성을 인증하지 않는다.
Cooperative Linux CPython3.12.13 범위이며 atomic/fsync/crash durability/atime/
적대적 hooks·동시 globals·경로 경쟁·다른 플랫폼 보장이 아니다.
실제 r/T2/scale=null,R_BUDGET=UNRESOLVED,Static Gate=FAIL,
Candidate/Runtime=NO_GO,F70UH/F70V/F71·실차 활성화 NOT_ALLOWED를 유지한다.
