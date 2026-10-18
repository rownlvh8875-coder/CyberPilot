# E 시작 준비 수정 — 과학적 규칙을 보존하는 controlled repair

E protocol V1의 exact-head CI는 [f75023904 / run39091121882](https://github.com/rownlvh8875-coder/CyberPilot/actions/runs/39091121882)에서 SUCCESS였다. 첫 실제 실행은 완료0 jobs, metadata4 files / 1,242,951 bytes와 TRAIN3 array files / 2,575,042 bytes를 읽은 뒤 runtime firewall에 의해 중단됐다. DEV, 모델 loading, one-step, rollout에는 도달하지 않았다. Source writes는0이다. 원래 V1 code/protocol/실패 receipt는 변경하지 않고 보존한다.

새 Python process의 synthetic 재현에서 NumPy `unique` → `numpy.ma` lazy import → 공개 package finder의 `os.listdir`가 같은 firewall rejection을 일으켰다. 저장 증거의 hash/schema 충돌은 관측되지 않았다. 실패 receipt 자체에는 차단 event 종류가 없으므로 공개 package import event와 stack은 synthetic 재현에서 확인한 진단이다.

[Protocol V2](empirical-hurdle-stage1-v4-e-execution-protocol-v2.json)는 원본 입력 접근 전에 공개 NumPy dependency를 준비한다. Runtime firewall의 directory scan·source write·민감 import 차단은 완화하지 않는다. 추가로 pickle load/loads/Unpickler/dump/dumps와 NumPy load/save를 차단한다. 새 cold-process 테스트는 원래 실패를 재현하고, 준비 후 TRAIN 선택·score 진단·projection·모든 horizon·drift·32 clauses 계산이 같은 firewall 아래 통과하는지 확인한다.

D0/D1, 32 jobs, TRAIN-only 선택, 기존44 source pins, 입력 범위, resource 상한, 모든 지표, 32 clauses, 22 domains, 공개 억제 규칙은 V1과 동일하다. 테스트로 이 동일성을 확인한다. 새 threshold recipe, model, candidate, calibration, acceptance cutoff는 도입하지 않는다. 실제 성능 결과를 보고 유리하게 조정한 변경이 아니다.

재실행 전에 새 exact-byte 독립 검토, commit, exact-head CI SUCCESS를 요구한다. V2의 별도 exclusive private output root에서 두 fresh repeats를 수행한다. 원래 중단은 성공이나 completed repeat에 포함하지 않고, 최종 source read totals와 blocked attempt에 포함한다. 추가적인 무제한 retry는 허용하지 않는다.

HOLDOUT CLOSED / vehicle authority NONE / no policy adoption / no V5는 유지한다.
