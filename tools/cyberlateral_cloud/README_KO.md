# 클라우드 검증·비공개 보관 — 명시적 한 명령

차량 코드가 아닌 개발용 orchestration입니다. 기존 CyberLateral 계산기·wheel0.3.0·
app lockfile·R41 API는 변경하지 않습니다. 자동 상시 실행/CI 업로드/기기 설치가 아닙니다.

## 현재 고정 복구 안내

노트북 없이 시작하는 현재 검증 경로는
[R64 도구 + 기존 R61 DEV 복구·검산 안내](docs/RECOVERY_R64_KO.md)입니다.
복구·실제 브라우저 검사 뒤 새 R64 reader로 저장 묶음을 검산합니다. reader JSON은
closed browser 폴더 밖에 저장합니다. 안내 문서 revision, 실행 tool commit,
archive source는 다릅니다. 문서는 R64 도구
`af4523c05c24ea2c9368a869c0cf9f4df0f54590`과 원래 identity의 R61 archive를 고정합니다.
고정 도구 checkout에는 이 새 안내 파일이 없을 수 있습니다. 문서의 최신 revision이나
main/latest를 고정 tool/source commit 대신 넣지 마세요.
이전 [R62 고정 안내](docs/RECOVERY_R62_KO.md)는 원래 bytes로 보존합니다.
아래의 고정 R48 안내·링크·명령도 과거 기준이며 현재 R64 절차와 동일시하지 않습니다.
아래 실행/backup 예시는 보관 도구 사용법이고, 현재 읽기 전용 복구 절차는 위 안내입니다.

브라우저가 이미 준비된 cloud host에서는 별도의 명시적
[R60 모바일/PC 리포트 회귀 검사](docs/BROWSER_SMOKE_R60_KO.md)를 실행할 수 있습니다.
기본 CI나 HF 복구 PASS가 브라우저 검사 PASS를 대신하지 않습니다.

이미 저장한 결과는 [R64 읽기 전용 묶음 검산](docs/SAVED_BROWSER_VERIFY_R64_KO.md)으로
브라우저·모델 재실행 없이 확인할 수 있습니다. 무결성 VALID와 원래 화면 PASS/FAIL은
다르며, 새 명령은 고정 R62 tool checkout이 아닌 새 Git 도구 revision에 있습니다.

저장 묶음 두 개는 [R66 정확한 바이트 비교](docs/SAVED_BROWSER_COMPARE_R66_KO.md)로
비교할 수 있습니다. 양쪽 무결성을 먼저 검산하고 변경 파일의 SHA/크기를 보고합니다.
동일한 FAIL도 MATCH일 수 있으며 새 화면 품질 판정이나 브라우저 실행은 아닙니다.

## 실행

기존 Git checkout에서 사용합니다. 새 worktree를 만들거나 사용자 변경을 reset하지 않습니다.
프로젝트 환경은 기존 uv0.12.23·CPython3.12.13·고정 DEV 의존성으로 준비합니다.
HF는 app 환경과 분리해 SDK2.4.0을 사용합니다. 필요 시 새 전용 환경에만 다음을 실행합니다.

```bash
uv venv --python 3.12.13 /workspace/.cache/cyberpilot-hf-client
uv pip sync --python /workspace/.cache/cyberpilot-hf-client/bin/python --require-hashes tools/cyberlateral_cloud/hf-requirements.lock
```

기존 도구 환경이 있으면 덮어 만들지 말고 먼저 버전·설치 상태를 확인합니다. HF_TOKEN은
환경의 secret binding으로만 제공합니다. 값을 명령 인자·채팅·파일·로그·Git에 쓰지 않습니다.
proxy·CA/TLS 검증을 유지합니다. 코드의 출처는 명시한 전체 Git commit SHA입니다.

```bash
tools/cyberlateral_dev/.venv/bin/python -B tools/cyberlateral_cloud/cloud_run.py run \
  --repo-root "$PWD" \
  --commit ee5189bd0f266e5f846ac571556a3896ab9dd0f3 \
  --project-python "$PWD/tools/cyberlateral_dev/.venv/bin/python" \
  --hf-python /workspace/.cache/cyberpilot-hf-client/bin/python \
  --hf-repo jjuinho/cyberpilot-evidence \
  --output /workspace/NEW-cloud-run
```

출력 부모는 존재하고 `NEW-cloud-run`은 아직 없어야 합니다. Git checkout 내부·기존 경로·
broken symlink는 거절합니다. 프로젝트 Python 경로는 venv 안의 interpreter를 그대로
전달해야 합니다. symlink를 실제 base Python으로 바꾸면 DEV 도구를 찾지 못할 수 있습니다.

실행 순서: 비공개 저장소 인증/소유 namespace 확인 → 해당 commit의 component만 export →
기존 전체 gate → R41 정상2회/완전한 첫 batch baseline1회 → saved typed literal/VIEW/참조/
Manifest/portable 비교 → 결정적 ZIP 봉인 → 비공개 업로드 → 정확한 원격 commit에서2파일
강제 재다운로드·bytes/SHA·ZIP 재검증. 기본 target은 이미 만들어진 private Dataset이며
repo를 생성하거나 visibility를 변경하지 않습니다. Public·잘못된 계정은 거절합니다.
Component의 CI 계약 검사에 필요한 원형 루트 README.md와
.github/workflows/cyberlateral-dev.yaml도 같은 commit에서 함께 내보냅니다.
기타 루트 파일·사용자 변경·untracked는 포함하지 않습니다.

## 결과·실패·재시도

`LOCAL_VERIFIED.json`은 로컬 gate/봉인 완료만 뜻합니다. `FINAL_RESULT.json`은 정확한 원격
재다운로드까지 끝난 경우에만 생성됩니다. stdout은 요약 JSON, 상세 로그는 로컬에 보존됩니다.
실패는 exit2와 `FAILURE.json`의 stage/code로 기록하며 source·부분 결과를 삭제하지 않습니다.
기존 성공·실패 기록을 덮어쓰지 않습니다. 의도적인 로컬 전용 검증은 `--local-only`로
선택하며 그 상태는 `LOCAL_VERIFIED_NOT_UPLOADED`이지 원격 보관 PASS가 아닙니다.

업로드/다운로드만 실패했다면 모델·전체 테스트를 재실행하지 않고 다음으로 재시도합니다.

```bash
tools/cyberlateral_dev/.venv/bin/python -B tools/cyberlateral_cloud/cloud_run.py backup \
  --run-dir /workspace/EXISTING-cloud-run \
  --hf-python /workspace/.cache/cyberpilot-hf-client/bin/python \
  --hf-repo jjuinho/cyberpilot-evidence
```

원격 경로는 `runs/<source SHA>/<archive SHA>/`입니다. 같은2파일이면 새 commit 없이 정확한
revision에서 다시 검산합니다. 다른 bytes나 일부 파일만 존재하면 덮어쓰지 않고 거절합니다.
동시 원격 변경은 parent-commit 검사로 거절합니다. 완료 후 재검사는 별도 BACKUP_RECHECK
기록으로 남깁니다. 공급자의 private 상태를 전후 확인하지만 타인이 동시에 visibility를
바꾸는 행위를 atomic하게 잠그는 서비스는 아닙니다. 이런 변경은 성공 처리하지 않습니다.

## 보관 범위

ZIP은 원형 committed component source·Git blob/mode/SHA provenance·실행 driver bytes·
경로 없는 acceptance·R41 portable26파일·별도 baseline 비교2파일·root sums만 포함합니다.
개인 receipt/전체 로그/venv/cache/전체 workspace/원본 차량 로그는 포함하지 않습니다.
portable subset은 R34/R39의 완전한 입력이 아닙니다. 원형 HTML의 checksum 링크는 해당
portable subset에 없을 수 있습니다. 원래 전체 결과와 Manifest는 로컬에 그대로 보존합니다.
기본 R41 3회는 모델972·선택-source 참조972호출이며 unit/gate의 추가 합성 작업은 NONZERO,
총합 미집계입니다. 호출 순서는 실제 시간·100Hz·주행 성능 증거가 아닙니다.

Checksum/재다운로드는 내용 일관성이지 임의 local receipt의 출처 인증이나 차량 승인 증명이
아닙니다. credential-shape 검사는 제한된 패턴 탐지이며 모든 비밀 부재 보증은 아닙니다.
Driver identity는 봉인 시점의 파일 bytes 기록입니다. 검증 도중 도구 코드를 동시에 편집하지
마세요. 시작 시점 driver snapshot/원자적 실행 attestation은 현재 제공하지 않습니다.

## 클라우드에서 읽기 전용 복구

### 고정 R48 복구 기준

노트북 없이 개발을 이어갈 수 있는 검증 기준은 다음과 같습니다. 이는 움직이는 main/
latest 포인터가 아니라 고정 기록입니다. R49는 안내만 갱신하며 이 archive를 새로 만들거나
덮어쓰지 않습니다. GitHub에서 source commit을 먼저 확보하고 기존 private Dataset
접근 권한을 사용합니다. token을 문서·명령 인자·Git에 넣거나 새 login을 요구하지 않습니다.

- Source: `d599d53c96dd965545da368ea699b661d1d07907`
- Archive SHA256: `82e3f0865d5981eb7ada41b20c9daf392b16e284b95362d04ff655c047b48fc7`
- Archive revision: `959c8876a65839729855712c5ca59df05dacea4f`
- [실제 실행을 검증한 한국어 복구 안내](https://huggingface.co/datasets/jjuinho/cyberpilot-evidence/blob/d5da1d916b5dd54e7768d2d65ce2e760203f9e11/restore-guides/d599d53c96dd965545da368ea699b661d1d07907/82e3f0865d5981eb7ada41b20c9daf392b16e284b95362d04ff655c047b48fc7/RESTORE_KO.md)

별도 SDK/app/cache를 쓰는 같은 host의 두 새 환경에서 source434파일을 검산한 기록입니다.
기본 restore의 R41과 별도로 guide는 R43/R44/R46 및 R44 41개·R46 38개 표적 unit을
실행합니다. 전체804 gate 재실행이나 별도 물리 머신 독립성으로 확대하지 않습니다.
HF는 DEV component/context/합성 evidence 보관소이며 native 저장소·차량 설치본이 아닙니다.
등록 restore snapshot은 수정하지 않고 Git checkout의 새 branch에서 개발합니다.
기존 checkout/venv/cache/STEP7/과거 evidence는 보존하며 새 output 경로만 사용합니다.

### 기본 복구 명령

노트북 없이 시작하려면 GitHub 소스를 먼저 clone하고 정확한 source commit을 확보합니다.
아래 명령은 그 Git object를 authority로 사용해 HF의 고정 archive와 SOURCE 전체를 비교한
뒤, **새 외부 폴더에 DEV component만** 복구합니다. 원래 Git checkout의 dirty/untracked
파일은 실행하거나 바꾸지 않습니다. 새 전체 Git repository/native/submodule/차량 환경을
HF만으로 설치하는 명령이 아닙니다.

uv0.12.23·CPython3.12.13과 위 전용 HF SDK2.4.0 환경이 필요합니다. 기존 Python을
찾지 못하면 실패하며 암묵적 Python 다운로드·global install·환경 configuration 게시를
하지 않습니다. orchestrator는 stdlib만 사용하므로 전용 SDK Python으로 시작할 수 있고,
실제 합성 모델/참조는 새 app venv의 Python으로만 실행합니다.

다음은 위 고정 R48 archive를 사용하는 기본 명령입니다. 전체 SHA/revision을 그대로
지정하며 `main`/`latest`/short SHA로 대체하지 않습니다. 출력 부모는 존재해야 하고
`NEW-cloud-restore`는 없어야 합니다.

```bash
/workspace/.cache/cyberpilot-hf-client/bin/python -B tools/cyberlateral_cloud/cloud_restore.py run \
  --repo-root "$PWD" \
  --commit d599d53c96dd965545da368ea699b661d1d07907 \
  --archive-sha 82e3f0865d5981eb7ada41b20c9daf392b16e284b95362d04ff655c047b48fc7 \
  --revision 959c8876a65839729855712c5ca59df05dacea4f \
  --hf-repo jjuinho/cyberpilot-evidence \
  --hf-python /workspace/.cache/cyberpilot-hf-client/bin/python \
  --output /workspace/NEW-cloud-restore
```

동작: own private Dataset/pinned revision 검사 → archive+checksum bounded 강제 다운로드 →
CRC/Manifest/SHA 검산 → SOURCE_IDENTITY/member/Git blob/mode/size/bytes 전부 비교 →
검증된 SOURCE만 복구 → 새 venv/cache와 unchanged app lock → dependency/module origin/
HF SDK 분리 확인 → R41 두 회차+완전한 첫 batch baseline 회차 → 기존 saved literal/VIEW/
reference/Manifest 검증 → portable26파일의 HF 결과와 exact 비교 → source 불변 재검산.
다운로드된 DRIVER는 실행하지 않습니다. 원격 쓰기/업로드는0입니다.

완료 receipt는 `RESTORE_RESULT.json`의 `PRIVATE_HF_DEV_RESTORE_SYNTHETIC_PASS`입니다.
`DEV_START.json`에서 복구 source/component/Python 경로를 확인합니다. source 하위는
Git working tree가 아닌 고정 DEV snapshot입니다. 제품 변경은 원래 Git checkout의
별도 개발 branch에서 진행하세요. `RESTORE_RESULT.json`이 없거나 FAIL이면 부분 결과를
성공 환경으로 사용하지 마세요. 실패는 exit2와 `FAILURE.json` stage/code로 남으며,
출력 충돌/입력 형식 오류는 기존 폴더에 실패 파일조차 쓰지 않습니다. 실패 폴더를 자동
삭제/reset/덮어쓰지 않으므로 재시도는 새 출력 경로를 사용합니다.
복구 명령 자체가 정상 실행된 뒤 `--hf-python` worker 경로가 없거나 실행 불가하면,
안전하게 검증·생성한 새 출력 폴더에 `FAILURE.json`만 남깁니다. stage는 `SDK_PREFLIGHT`,
code는 `HF_INTERPRETER_REQUIRED`입니다. HF에 접속하지 않으며 소스·app venv·성공
receipt도 생성하지 않습니다. 명령을 시작할 launcher Python 자체가 실행되지 않는
경우는 shell 오류이므로, 실행되지 않은 도구가 실패 파일을 남길 수는 없습니다.

명시적 R41 모델972·선택-source 참조972호출을 실행합니다. unit test의 추가 합성 작업은
NONZERO이며 별도 미집계입니다. 기본 복구는 새 venv의 전체 DEV gate 재실행이나
별도 물리 머신/실시간/차량 qualification이 아닙니다. F61·실제 r/dt·Controller·차량
Runtime·CAN·실차 input/설치/활성화는0이고, 기존 gate는 그대로 닫혀 있습니다.

## 개발 검사

`CyberLateral Cloud Tooling`은 cloud 도구·DEV component·관련 workflow/root README 변경의
main push/PR에서 자동 실행됩니다. 기존 app DEV workflow는 변경하지 않습니다.
read-only contents 권한과 pinned actions/Python3.12.13/uv0.12.23을 사용하며,
runner 임시 폴더에 app/SDK 환경을 각각 만듭니다. 이 job에 HF_TOKEN이나 HF secret을
전달하지 않습니다. HF_HUB_OFFLINE=1이며 실제 private HF backup/restore integration을
실행하지 않습니다. 패키지 설치의 PyPI/GitHub 네트워크와 live HF API를 구분합니다.

로컬에서도 같은 공통 검증 명령을 사용할 수 있습니다. 앱 DEV 환경에서 실행하고,
SDK2.4.0 전용 Python을 별도로 지정합니다. output 부모는 존재하고 마지막 경로는 새 경로여야 합니다.

```bash
tools/cyberlateral_dev/.venv/bin/python -B tools/cyberlateral_cloud/ci_verify.py \
  --hf-python /workspace/.cache/cyberpilot-hf-client/bin/python \
  --output /workspace/NEW-cloud-verification
```

전체 cloud unittest, Ruff/Ty/Codespell, cloud-owned Python compile을 실행하고 source
bytes 불변을 재검산합니다. 테스트 수는 실제 ledger에서 읽으며 기존 baseline70보다
적거나 실패/skip/중복/잘린 기록이면 거절합니다. 성공 후에만 SUMMARY.json과 closed
SHA256SUMS.txt를 만듭니다. 출력은 worktree 검사 기록이지 committed archive나 출처 인증이 아닙니다.
실패는 exit2와 새 output의 FAILURE.json stage/code로 남기며, CI는 always() artifact로
생성된 진단 로그를 보존합니다. bootstrap 자체가 실패하면 GitHub job 로그를 확인하세요.
각 명령의 로그는 최대1MiB이며 초과 시 거절하고, timeout 전까지 받은 내용을 보존합니다.
명령별30초(전체 unittest180초), 전체 명령 budget240초로 CI job 종료 전에 실패를 기록합니다.
합성 모델/참조 unit 작업은 NONZERO/총합 미집계이며 차량 Gate를 열지 않습니다.

```bash
tools/cyberlateral_dev/.venv/bin/python -B -m unittest discover -s tools/cyberlateral_cloud/tests -v
tools/cyberlateral_dev/.venv/bin/ruff check --isolated --select E4,E7,E9,F,I,B,UP tools/cyberlateral_cloud
tools/cyberlateral_dev/.venv/bin/ty check --config-file tools/cyberlateral_dev/ty.toml --python /workspace/.cache/cyberpilot-hf-client/bin/python --extra-search-path tools/cyberlateral_cloud tools/cyberlateral_cloud
```

새 tests의 real R41 검사도 합성 모델·참조 계산을 수행합니다. HF unit transport는 인메모리
모의 서비스이며 실제 SDK/API 권한 검증은 별도 end-to-end 실행으로 판정합니다.

F61·실제 r/dt·Controller·차량 Runtime·CAN·실차 데이터·차량 활성화·후보 성능 평가는0입니다.
R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제 r/T2/scale=null, Candidate/Runtime=NO_GO,
F70UH/V/F71=NOT_ALLOWED 유지. GPU·Spaces·유료 job·GitHub push/merge/CI·환경 게시를 하지 않습니다.
