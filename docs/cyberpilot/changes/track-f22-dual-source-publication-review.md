# Dual Source Publication — UNAPPLIED_REVIEW_ONLY

이 다섯 파일은 정식 반영 전 검토안이다. F22는 원본 작업 트리를 바꾸지 않았다.
기존 Source A verifier, receipt, test_source_binding과 Source Pin은 그대로 유지한다.

새 driver는 --prepare로 명시적인 저장소를 읽어, 계약에 있는 정확한 Git/submodule
객체의 A와 현재 바이트가 승인된 Pin과 일치하는 B를 저장소 밖 별도 capsule에 쓴다.
둘은 sparse 선언 파일 집합이다. 전체 과거 Runtime/CI 재현이 아니다.
--run은 각각 별도 프로세스에서 기존 7개 시험을 실행하고 B 전용 F21 검증을 수행한다.

A: legacy 7 PASS.
B: legacy 6 PASS / 1 ERROR(INJECTION_SOURCE_DRIFT), F21 STRUCTURALLY_VALID.
오류는 예상된 negative observation으로 기록하지만 기존 오류를 PASS로 재분류하지 않는다.
정식 Source Publication, Runtime, 차량 측정 및 성능 승인은 여전히 없다.
publication_admitted=false, effective=false, runtime_authorized=false를 유지한다.

~~~bash
python3 -B tools/cyberpilot/dual_source_publication_v1.py --prepare \
  --source-root /absolute/CyberPilot --evidence-root /outside/new-capsules
python3 -B tools/cyberpilot/dual_source_publication_v1.py --run \
  --evidence-root /outside/new-capsules --output /outside/new-result.json
~~~

이 driver의 --prepare는 Git 객체와 계약 Pin을 실제로 대조한다.
계약 문자열만으로 외부 독립 인증을 주장하지 않는다.
검토된 driver와 계약의 배포 Identity가 신뢰의 뿌리다.
원본 Source B의 SHA가 바뀌면 기존 계약을 단순 치환하지 말고 새 버전 검토가 필요하다.

신규 workflow는 독립적인 수동 diagnostic job 제안이다.
기존 Upstream Unit, Full CI V2, Legacy V2를 대체하거나 Required Check를 변경하지 않는다.
따라서 기존 B worktree의 Legacy Publication ERROR와 기존 CI의 실패 가능성은 남는다.
Source-aware Full CI를 공식 지원하려면 exact Test-ID/Source Lock/Receipt를 보존하는
새 버전 CI 계약의 별도 설계·승인이 필요하다. 기존 runner/test를 skip/xfail하거나
Frozen Source Pin을 바꿔서 해결할 수 없다.

Local-only 구현, commit/push, workflow 실행, Required Check 변경, Runtime 통합은
서로 다른 승인이다. 이 미적용 Diff는 어느 승인도 제공하지 않는다.

## 필수 Source B 배포 전제조건 — 별도 승인 필요

위 신규 다섯 파일만 Git에 올리면 깨끗한 checkout은 현재 로컬 Source B가 아니다.
다음 기존 로컬 일곱 경로의 정확한 바이트가 별도로 승인되어 배포돼야 한다.
기존 파일을 새로 수정하라는 뜻은 아니며 F22에서는 commit/delivery를 수행하지 않는다.

- docs/cyberpilot/changes/capture-only-source-version-v1.json
- docs/cyberpilot/changes/track-f21-source-version-migration.md
- openpilot/selfdrive/controls/controlsd.py
- openpilot/selfdrive/controls/lib/cyber_lateral/diagnostic_capture.py
- tools/cyberpilot/source_version_contract_v1.py
- tools/cyberpilot/tests/test_native_diagnostic_capture_v1.py
- tools/cyberpilot/tests/test_source_version_contract_v1.py

향후 Git checkout 기반 진단 job에는 보존된 위 7개와 신규 제안 5개, 총 12개 경로의
정확한 Source 전달이 필요하다. 로컬 신규 5개 구현 승인과 12개 경로의 commit/push 승인은
별개다. 현재는 모두 미승인이다. Source 전달 preflight는 누락/다른 바이트이면 capsule을
만들기 전에 차단한다. 원래 HEAD의 Source A 파일만 가진 입력은 예상 거부된다.
이 negative control은 완전한 clean-checkout CI 실행 성공을 주장하지 않는다.
