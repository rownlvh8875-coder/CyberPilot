# R62 main + 기존 R61 HF DEV 복구

새 한국어 전체 실패 설명은 R62 main 도구에서 제공합니다. DEV/context441파일은 R61과
같으므로 기존 비공개 HF archive를 읽기 전용으로 사용합니다. 새 HF archive/guide 게시가
아니며 과거 안내도 변경하지 않습니다. 두 identity를 구분하세요.

- Tool commit: `1b244fe8e2dee8636ce7811529978d9499cfedc8` / tree `f855cbc1f4ba2841521fc8f522a4afe4420d0e6b`
- Archive source commit: `e5b76678cff4d45a4915da0f9b26982711167b1d` (R61, 새 main으로 relabel하지 않음)
- Archive SHA256: `e1021b2d6c9f729402ab0f57805c8209d3cc3e06a94f7d0751c5ec71e82729d2`
- Archive revision: `aa393167a37fff42eef9ce8940faa8413c798f15`
- HF Dataset: `jjuinho/cyberpilot-evidence` (private 필수)

전체 source는 Git authority입니다. HF는 DEV/context/R41만 보관하며 HF DRIVER는 실행하지
않습니다. 기존 Linux Git/sha256sum/uv0.12.23/CPython3.12.13, secret binding HF_TOKEN과
proxy/CA/TLS가 필요합니다. 새 SDK2.4.0/app은 분리됩니다. host의 기존 Playwright/Chromium을
사용하며 브라우저/전역 설치나 정책 우회를 하지 않습니다. 없으면 중단합니다.

```bash
set -eu
cyberpilot_recovery_root="$(mktemp -d /workspace/cyberpilot-r62-recovery-XXXXXX)"
export GIT_LFS_SKIP_SMUDGE=1
export UV_PYTHON_DOWNLOADS=never
export UV_LINK_MODE=copy
export UV_CACHE_DIR="$cyberpilot_recovery_root/sdk-cache"
git clone --depth 1 --filter=blob:none --no-checkout https://github.com/rownlvh8875-coder/CyberPilot.git "$cyberpilot_recovery_root/repository"
git -C "$cyberpilot_recovery_root/repository" fetch --depth 1 origin 1b244fe8e2dee8636ce7811529978d9499cfedc8
git -C "$cyberpilot_recovery_root/repository" fetch --depth 1 origin e5b76678cff4d45a4915da0f9b26982711167b1d
git -C "$cyberpilot_recovery_root/repository" -c advice.detachedHead=false checkout --detach 1b244fe8e2dee8636ce7811529978d9499cfedc8
test "$(git -C "$cyberpilot_recovery_root/repository" rev-parse HEAD)" = 1b244fe8e2dee8636ce7811529978d9499cfedc8
test "$(git -C "$cyberpilot_recovery_root/repository" rev-parse 'HEAD^{tree}')" = f855cbc1f4ba2841521fc8f522a4afe4420d0e6b
git -C "$cyberpilot_recovery_root/repository" diff --raw --exit-code --no-ext-diff --no-textconv e5b76678cff4d45a4915da0f9b26982711167b1d 1b244fe8e2dee8636ce7811529978d9499cfedc8 -- tools/cyberlateral_dev README.md .github/workflows/cyberlateral-dev.yaml
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
printf 'R62_RECOVERY_ROOT=%s\n' "$cyberpilot_recovery_root"
```

RESTORE_RESULT의 source commit이 R61인 것이 정확합니다. CLI의 --commit은 HF 경로도
선택하므로 기존 source commit을 유지하세요. 별도 검증에서는 원본 archive bytes를
recover_source API에 새 tool commit으로 전달해 SOURCE_IDENTITY_MISMATCH 거절을 확인합니다.
이는 source-stage API 검증이며 잘못된 CLI 호출의 exit/stage를 주장하지 않습니다.
Git diff는 두 commit의 DEV/context가 동일함을 확인하며 실제 복구는441source bytes를
보존·검산합니다. source의 옛 commit과 새 tool commit은 합치거나 숨기지 않습니다.

기본 복구는 R41 합성 portable 검증이며 전체883tests를 다시 실행하지 않습니다. 새 main
전체DEV CI와 cloud122 CI는 별도 전달 증거입니다. Browser의 RESULT와 전체 checksum이
완료 근거이고 SUMMARY_KO만으로 완료를 판단하지 마세요. 부분 폴더는 보존하고 새 경로로
재시도합니다. R41/unit/CI 합성 작업은 NONZERO, browser의 모델/F61/실제r/dt/차량 작업은0입니다.
같은 host에서 두 논리적 환경을 재생성한 검증이며 물리 머신 독립성·모든 browser/font/
접근성/touch·출처 인증·실차 적격성이 아닙니다. R_BUDGET unresolved·Static Gate FAIL,
실제r/T2/scale null·Candidate/Runtime NO_GO·F70UH/F70V/F71 및 실차 활성화 NOT_ALLOWED 유지입니다.
