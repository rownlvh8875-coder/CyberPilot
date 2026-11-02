# 클라우드 검증·비공개 보관 — 명시적 한 명령

차량 코드가 아닌 개발용 orchestration입니다. 기존 CyberLateral 계산기·wheel0.3.0·
app lockfile·R41 API는 변경하지 않습니다. 자동 상시 실행/CI 업로드/기기 설치가 아닙니다.

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

## 개발 검사

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
