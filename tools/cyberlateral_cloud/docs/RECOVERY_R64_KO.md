# R64 도구 고정 — 클라우드 복구·브라우저 검사·저장 결과 검산

노트북 없이 DEV component를 복구하고 실제 브라우저 검사 뒤 저장 묶음을 읽기 전용으로
검산하는 절차입니다. 새 HF archive/guide 게시나 차량 설치가 아닙니다.

- Tool commit: `af4523c05c24ea2c9368a869c0cf9f4df0f54590`
- Tool tree: `a2cab555bc0e74c633aa7d118c15f8f307d59dde`
- Archive source commit: `e5b76678cff4d45a4915da0f9b26982711167b1d`
- Archive source tree: `5e890731b54b5534faf93c2a5a6d9b1f3762a72c`
- Archive SHA256: `e1021b2d6c9f729402ab0f57805c8209d3cc3e06a94f7d0751c5ec71e82729d2`
- Archive revision: `aa393167a37fff42eef9ce8940faa8413c798f15`
- HF Dataset: `jjuinho/cyberpilot-evidence` — private 필수

이 문서의 revision, 실행 tool commit, archive source는 서로 다릅니다. 고정 tool checkout에
이 새 문서가 없거나 README가 옛 안내를 보여도 정상입니다. 문서 revision·main/latest로
tool/source pin을 대체하지 마세요. 원래 archive identity를 새 tool로 relabel하지 않습니다.

## 전제

기존 Linux Git·sha256sum·uv0.12.23·CPython3.12.13, secret binding HF_TOKEN과
설정된 proxy/CA/TLS를 사용합니다. Host Python의 Playwright와 기존 Chromium
`/usr/lib/chromium/chromium`이 필요합니다. 다른 host interpreter면
CYBERPILOT_BROWSER_PYTHON을 그 경로로 미리 지정하세요. browser/global install,
새 login, 정책 우회나 암묵적 Python 다운로드는 하지 않습니다. SDK2.4.0과 app은 분리됩니다.

## 새 폴더에서 실행

```bash
set -eu
cyberpilot_recovery_root="$(mktemp -d /workspace/cyberpilot-r64-recovery-XXXXXX)"
printf 'R64_RECOVERY_WORKDIR=%s\n' "$cyberpilot_recovery_root"
export GIT_LFS_SKIP_SMUDGE=1
export UV_PYTHON_DOWNLOADS=never
export UV_LINK_MODE=copy
export UV_CACHE_DIR="$cyberpilot_recovery_root/sdk-cache"
git clone --depth 1 --filter=blob:none --no-checkout https://github.com/rownlvh8875-coder/CyberPilot.git "$cyberpilot_recovery_root/repository"
git -C "$cyberpilot_recovery_root/repository" fetch --depth 1 origin af4523c05c24ea2c9368a869c0cf9f4df0f54590
git -C "$cyberpilot_recovery_root/repository" fetch --depth 1 origin e5b76678cff4d45a4915da0f9b26982711167b1d
git -C "$cyberpilot_recovery_root/repository" -c advice.detachedHead=false checkout --detach af4523c05c24ea2c9368a869c0cf9f4df0f54590
test "$(git -C "$cyberpilot_recovery_root/repository" rev-parse HEAD)" = af4523c05c24ea2c9368a869c0cf9f4df0f54590
test "$(git -C "$cyberpilot_recovery_root/repository" rev-parse 'HEAD^{tree}')" = a2cab555bc0e74c633aa7d118c15f8f307d59dde
git -C "$cyberpilot_recovery_root/repository" diff --raw --exit-code --no-ext-diff --no-textconv e5b76678cff4d45a4915da0f9b26982711167b1d af4523c05c24ea2c9368a869c0cf9f4df0f54590 -- tools/cyberlateral_dev README.md .github/workflows/cyberlateral-dev.yaml
uv venv --python 3.12.13 "$cyberpilot_recovery_root/hf-sdk"
uv pip sync --python "$cyberpilot_recovery_root/hf-sdk/bin/python" --require-hashes "$cyberpilot_recovery_root/repository/tools/cyberlateral_cloud/hf-requirements.lock"
"$cyberpilot_recovery_root/hf-sdk/bin/python" -B "$cyberpilot_recovery_root/repository/tools/cyberlateral_cloud/cloud_restore.py" run \
  --repo-root "$cyberpilot_recovery_root/repository" --commit e5b76678cff4d45a4915da0f9b26982711167b1d \
  --archive-sha e1021b2d6c9f729402ab0f57805c8209d3cc3e06a94f7d0751c5ec71e82729d2 --revision aa393167a37fff42eef9ce8940faa8413c798f15 --hf-repo jjuinho/cyberpilot-evidence \
  --hf-python "$cyberpilot_recovery_root/hf-sdk/bin/python" --output "$cyberpilot_recovery_root/restored"
"${CYBERPILOT_BROWSER_PYTHON:-python}" -B "$cyberpilot_recovery_root/repository/tools/cyberlateral_cloud/browser_smoke.py" \
  --component "$cyberpilot_recovery_root/restored/source/tools/cyberlateral_dev" \
  --app-python "$cyberpilot_recovery_root/restored/dev-venv/bin/python" \
  --browser /usr/lib/chromium/chromium --output "$cyberpilot_recovery_root/browser"
(cd "$cyberpilot_recovery_root/browser" && sha256sum --strict -c SHA256SUMS.txt)
"$cyberpilot_recovery_root/restored/dev-venv/bin/python" -B "$cyberpilot_recovery_root/repository/tools/cyberlateral_cloud/browser_verify.py" \
  --input "$cyberpilot_recovery_root/browser" > "$cyberpilot_recovery_root/SAVED_BROWSER_VERIFY.json"
(cd "$cyberpilot_recovery_root/browser" && sha256sum --strict -c SHA256SUMS.txt)
printf 'R64_RECOVERY_ROOT=%s\n' "$cyberpilot_recovery_root"
```

## 완료와 실패

처음 WORKDIR은 부분 결과의 위치일 뿐 성공 표시가 아닙니다. 모든 명령이 exit0이어야
마지막 R64_RECOVERY_ROOT가 출력됩니다. 브라우저 FAIL/오류 또는 reader의 exit1/2는
중단하며 완료로 처리하지 않습니다. 부분 폴더와 원래 RESULT/FAILURE를 보존하고,
자동 overwrite·repair·fallback 없이 새 폴더로 재시도하세요.

RESTORE_RESULT의 source가 옛 R61 e5인 것이 정확합니다. --commit은 HF namespace도
선택하므로 새 tool commit으로 바꾸지 않습니다. Git diff는 DEV/context 동일성을,
restore는 기존 archive의441source bytes/Git records와 R41 portable을 검산합니다.
전체 repository/native/submodule/차량 환경을 HF만으로 설치하는 절차는 아닙니다.
HF DRIVER bytes는 실행하지 않고, Git에서 고정한 도구만 사용합니다.

Browser의 RESULT와 전체 checksum이 완료 근거입니다. SUMMARY만으로 판단하지 마세요.
SAVED_BROWSER_VERIFY.json은 browser/ 밖에 있습니다. 그 안에 추가하면 R64의
38파일 closed-layout 계약을 위반합니다. 이 새 JSON은 무결성 VALID와 원래
R60_BROWSER_SMOKE_PASS/10cases/38files를 기록하며 새 화면 관측을 수행하지 않습니다.
source_identity_reauthenticated=false이며 원본 source를 다시 인증하지 않습니다.
그 역할은 앞선 Git/archive 복구 검사와 구분합니다. 일관된 위조·재봉인은 배제하지 못합니다.

기본 restore의 R41은 명시적 합성 모델/참조 작업입니다. Browser와 passive reader의
새 모델/F61/실제r·dt/차량 작업은0이고, R41/unit/CI 합성 작업은 별도 NONZERO/미집계입니다.
전체 DEV883/wheel을 이 절차가 새로 실행·빌드하지 않습니다. 고정 도구의 cloud141
CI와 기존 DEV 증거는 별도 전달 자료입니다. 같은 준비된 host의 두 논리 환경 검증이지
물리 머신 독립성·모든 browser/font/접근성/touch·수치 정답·발행자 인증·실차 적격성이 아닙니다.

[원래 R62 고정 안내](RECOVERY_R62_KO.md)와 [R64 reader 범위](SAVED_BROWSER_VERIFY_R64_KO.md)를
보존합니다. 기존 checkout/환경/STEP7/증거는 바꾸거나 삭제하지 않습니다.
R_BUDGET UNRESOLVED · Static Gate FAIL · 실제r/T2/scale null · Candidate/Runtime NO_GO,
F70UH/F70V/F71 및 실차 활성화 NOT_ALLOWED를 유지합니다.
