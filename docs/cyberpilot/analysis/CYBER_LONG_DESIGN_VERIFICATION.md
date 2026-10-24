# Step 4 검증 기록 — Cyber Long 설계

상태: **PASS_STATIC_ONLY**. source/document 검증 성공, runtime는 **NOT RUN**.
작성일: 2026-09-29. 범위: 소스/문서 검증만; control 구현 및 runtime 검증 아님.

## 산출물과 재현

- [설계](../../CYBER_LONG_DESIGN.md)
- [파라미터 해설](CARROT_LONG_PARAMETERS.md)
- [고정 소스/파라미터 inventory](CARROT_LONG_SOURCE_INVENTORY.json)

로컬 제외 경로 work/step4/extract_sources.py는 git show + Python AST로 reference
source를 읽으며 reference 모듈을 import/execute하지 않는다.
work/step4/verify_design.py는 source blob/line, catalog coverage/classes,
문서 형식/상대 링크, baseline HEAD/branch, 이전 파일 hash와 gitlinks를 검증한다.
이 도구들은 commit 대상 runtime 파일이 아니라 로컬 분석 helper다.

실행 명령:

```powershell
python work/step4/extract_sources.py
python work/step4/verify_design.py
git diff --check
git diff --cached --check
git status --short --branch
git submodule status
```

## 실행 결과

extract_sources.py 최종 실행 exit=0, AST failures=0.
verify_design.py 검증 실행 exit=0, PASS_STATIC_ONLY:

| 검증 항목 | 결과 |
| --- | --- |
| Carrot Python source commit/blob/function anchor | 108개 확인 |
| 추가 schema/config source blob | 4개 확인 |
| Params read/write site / 고유 accessed key | 189개 / 115개 확인 |
| manager/UI/access 합집합 parameter catalog | 146개, 누락/중복 없음 |
| key 분류와 human table / AutoTune disabled | 146개 일치 |
| field assignment / numeric constant / core literal index | 330 / 162 / 2,428 |
| 기존 Step 2/3 파일 SHA-256 보존 | 5개 확인 |
| root submodule gitlink 보존 | 6개, 미초기화 유지 |
| HEAD / branch / tracked/staged diff | c8fb906815530460ed156f14e09e1f312bb0f851 / develop / 없음 |
| 최종 보고서 포함 상대 링크 / pinned source 링크 | 17개 / 115개 확인 |
| 검증 문서 수 | repository 문서 4개 + 로컬 handoff 1개 |
| 파일 형식 | UTF-8/no BOM/LF, trailing whitespace 없음 |

git diff --check 및 git diff --cached --check는 exit=0.
이번 문서는 untracked이므로 추가로 각 새 문서에 git diff --no-index --check -- NUL
<path>를 실행했다. repository 문서 4개와 로컬 보고서 모두 whitespace 진단 없이
exit=1이었다. 이는 새 파일 내용 차이를 뜻한다. exit=3과 whitespace 진단은 오류로
구분했다. JSON/검증 기록의 초기 EOF 빈 줄은 제거 후 재검사하여 해결했다.

문서 자체 검토에서는 default-off parity, min/stop-OR의 분리, trajectory 의미,
low-speed stop/resume 권한, emergency braking 우선, stale fallback, input/config
identity, 라이선스/evidence gate 및 각 expected file의 merge 위험을 확인했다.
독립 외부 review나 runtime 결과를 대신하지 않는다.

## 검증 범위와 한계

Step 3 frozen revisions를 사용했으며 Step 4 전체 remote fetch는 하지 않았다.
partial clone에서 git show가 필요한 개별 blob을 lazy-fetch할 수 있으나
remote-tracking branch update와 최신 HEAD 확인을 대신하지 않는다.

Carrot GM 파일 두 개는 UTF-8 BOM이 있어 초기 ast.parse가 거부했다.
분석 helper만 선행 BOM을 제거해 다시 parse했고 source blob 자체는 변경하지 않았다.
이 차이를 Carrot 제어 로직 오류라고 보고하지 않는다.

첫 draft 검증은 아직 생성 전인 검증 문서의 상대 링크에서 중단됐다. 문서를 생성한
뒤 동일 검증을 다시 실행해 통과했다. 데이터/소스/테스트 실패를 숨기거나 threshold를
완화한 것이 아니다.

process replay README 표현 대신 실제 argparse(nargs="*")를 확인해 계획 명령의
whitelist를 comma-separated가 아닌 공백 구분으로 기록했다. 명령은 아직 실행 안 했다.

runtime unit/build/process replay/closed-loop/shadow는 **NOT RUN**.
root 6개 submodule은 미초기화 상태이고 LFS/build/supported runtime는 이번 범위에서
준비/검증하지 않았다. Python 3.14는 AST 분석 도구일 뿐 openpilot 지원 환경 검증이 아니다.
설계의 expected behavior와 성능 개선 가설은 empirical evidence가 아니다.

control/config/schema/safety/CAN/device/vehicle/real Params 수정, commit/push,
merge/cherry-pick, deployment, log 업로드를 하지 않는다.
기존 Step 2/3 파일은 보존한다. .git/info/exclude의 로컬 work/step4 및
outputs/STEP4_REPORT.md 추가만 Git 로컬 설정 변경이다.
