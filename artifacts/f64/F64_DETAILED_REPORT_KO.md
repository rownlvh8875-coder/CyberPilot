# F-64 Controller 비호출 합성 계약 오라클 — 상세 보고서

## 1. 최종 STATUS
**F64_HOLDOUT_FAIL**

선택한 합성 Source·정수 시간·지표의 소프트웨어 검사는 통과했으나, 사전 등록한 유효 holdout Source와 공개 개발 Source의 바이트 중복 금지 기준이 실패했다. 전체 PASS 또는 r만 미해결인 PARTIAL PASS로 표시하지 않는다.

## 2. 작업 목적
Controller를 호출하지 않고 합성 Source 생성·단일 정수 시간축·독립 지표 오라클·절차적 분리·결정성을 검증했다. 신규 평가 기반시설에 한정된다.

## 3. 명시적 비목표
Controller import/초기화/호출, 모델·후보 개발, T2/T3, 실제 RLOG 분석, 기존6,000개 재평가, 기존 T1 결과 변경, 실제 조향·차량 성능·안전성·100Hz Deadline 주장은 수행하지 않았다.

## 4. 기준 저장소·브랜치·HEAD
- Repository: rownlvh8875-coder/CyberPilot
- 원본: feature/cyber-autotune, HEAD588d6b21c21089065a7d9165d6e7a438e8aa6297.
- 신규 격리 브랜치: feature/f64-synthetic-contract-oracle.
- PRE_HOLDOUT_COMMIT: ce8360d561cf85433fa2df072059c2bf887ee5b6.
- 1차 Commit은 신규48파일, 기존 Tracked 수정0이다.
- 최종 Commit SHA는 자기참조를 피하기 위해 Commit 밖 POST_COMMIT_RECEIPT.json과 최종 응답에 기록한다. 2차 Commit은 증거·실패 봉인 자료만 추가하며 Source/계약/테스트/Workflow는 변경하지 않는다.

## 5. F-63 기준점 검증
F-63 ZIP:
fcb3f8a0a235b94671fdd67ca80a738fb6ba31b5380944323e2b3ae38f0043b7
Python SHA256와 Windows .NET SHA256의 독립 재계산이 일치했다. F-63 보존 감사 V2도 재실행했고, 기존 Canonical5f4a95fc1dc8452ee93da06f579e5b3535b1d2269c8fbbbdb4e9b5f17a92a4c5와 일치했다. 원본 Tracked3,278파일, Untracked4파일, Index CLEAN을 확인했다.

## 6. 보호 대상 무결성
F-60/F-61/F-62/F-63 폴더 및 정확한 기존 F-10 A0/T1 압축 출력·설계·지표 계약 등308파일을 작업 전후 해시로 검사했다. 압축 출력을 해제하거나 재분석하지 않았다.
- 파일 바이트 변경0.
- before/after JSON Manifest SHA256:34972e7a9e115d4a8893ec6ba4b7af904dde1b2b3c6d92c7aaa544308782a68d.
- before/after SHA256SUMS 텍스트 SHA256:3913169bb42228e5e841dc5d1b5a21b78fadc8be3163f1f4ba7ad83d57ffd69e.
- 원본 작업 트리3,278 Tracked 및4 Untracked 보존.
- Submodule pin6, committed LFS pointer252 보존. 신규 worktree는 LFS smudge 및 submodule 다운로드 없이 만들었다.
- 기존 봉인 ZIP/Receipt/Manifest 수정·재압축 없음. 새 전달 ZIP은 F-64 자료다.

## 7. Source schema 계약
F64_SYNTHETIC_SOURCE_V1 / F64_CONTROLLER_FREE_SYNTHETIC_OBSERVATIONS_V1.
필드는 schema_version, source_identity, origin, unit, times_ns, numerators, denominator로 고정했다. 값은 정수 numerator/positive denominator의 정확한 합성 normalized_command 관측값이며 [-1,1] 범위다. 실제 Controller/액추에이터 출력이 아니다.
배열은 같은 길이1..8000, 정확한 int만 허용하고 bool/float·결측·추가 필드·잘못된 identity·중복 JSON key를 거부한다.8000은 기존 F-10 기술적 합성 horizon을 상속한 입력 크기 계약이며 물리 성능 한계가 아니다.
ASCII subset UTF-8, sorted keys, compact JSON, 단일 LF, 배열 순서 보존, NaN/Inf 금지. canonical byte와 다른 JSON도 암묵 보정하지 않는다.

## 8. 정수 시간 계약
canonical timestamp 및 interval은 signed-int64 범위의 ns다. timestamp는0..9223372036854775807, interval은1..10000000ns이다. 기존 F-10 time_ns/F-60 TIME_NS에서 ns 및10ms 상한을 가져왔다. F-64는 그 상한 이내의 불규칙 관측 간격을 명시적으로 허용하는 새 합성 계약이며 F-60 고정 grid를 변경하지 않았다.
시작점을 자동 이동하지 않고 입력 시각을 보존한다. 중복/역순/gap은 별도 고정 오류로 차단한다. Python의 넓은 정수에서 계산 후 범위를 검사하여 overflow를 숨기지 않는다. 센서 취득·실제 Runtime Deadline 계약이 아니다.

## 9. Source/time conversion 규칙
정확한 정수 ns/us/ms/s만 받는다. 변환 계수는1/1000/1000000/1000000000이며 float1.0조차 거부한다. 반올림 없음. 음수, overflow, 비정수 입력, 역변환의 나눠떨어지지 않는 tick을 거부한다.
현재 F-61의 float endpoint 계약을 바꾸거나 역사적 시각을 재작성하지 않았다. F-60 적격 pair0 및 실제 입력 미적격6,000개는 그대로다.

## 10. 지표 계약
선택 범위는 인접 N-1쌍 Rate의 RMS·절대 p95/p99·최대 Rate·최대 차분·support/count/duration이다.
rate=(num_i-num_prev)*1000000000/(denominator*delta_ns).
동일 pair weighting이며 irregular sampling도 시간 가중 평균으로 바꾸지 않는다. RMS는 정확한 유리수 mean-square의 제곱근(radical)으로 기록해 float 허용오차를 임의 도입하지 않았다. p95/p99는 기존 linear quantile의 정확한 유리수 interpolation이다.
initial0을 prepend하지 않아 F-60/F-62 N-1 계약과 일치한다. F-10의 별도 initial0/N 정의와 합치지 않는다. 한 샘플이면 pair 지표 null/INSUFFICIENT_PAIRS, empty는 거부한다.
추종·곡률·Position·Heading에는 이 scalar Source의 독립 reference 계약이 없으므로 구현하지 않았다. 절대 y/heading 또는 곡률 적분으로 대체하지 않았다.

## 11. r 정의와 사전 budget
R_BUDGET_UNRESOLVED.
기존 F-61의 rate_budget_per_s는 caller-declared synthetic constraint다. 새로운 평가의 독립적인 규범 r/budget 근거는 발견하지 못했다. budget=null을 유지한다. 관측값의 p95/max나 normalized domain의 자명한 상한으로 승인 예산을 만들지 않았다.
단위 comparator threshold1은 exact BELOW/EQUAL/ABOVE 구현의 교정 시험값이며 r·성능 합격기준·차량 한계가 아니다. 소프트웨어 합격기준은 오라클 exact equality다. 이번 최종 STATUS는 r만의 PARTIAL이 아닌 별도의 holdout 실패다.

## 12. 합성 Source 설계
constant, linear_ramp, piecewise_constant, piecewise_linear, deterministic_pulse, bounded_noise, irregular_valid의7 family와8개 invalid control을 고정했다.
seed0/1의 공개14 valid +8 rejection controls=22사례다. 최소 길이1, 최대8000 및0입력·closed-form ramp/step 등은 별도 unittest에서 확인했다.
bounded noise는 SHA256 counter bytes와 명시적 정수 modulo를 사용한다. OS random·wall clock·locale·실행 경로에 의존하지 않는다. 새로운 통계적/암호학적 품질 주장은 없다.
진폭 파라미터32+seed%32가 다수 seed를 같은 관측 파형으로 사상하는 문제가 최종 holdout 중복 실패의 원인이었다. 결과를 본 뒤 그 사상을 수정하지 않았다.

## 13. 독립 오라클 설계
새 production은 Fraction 연산, 독립 oracle은 integer gcd/lcm·공통분모 제곱합·정수 interpolation이다. Oracle은 json/math만 import하며 production/generator helper·Fraction을 공유하지 않는다.
uniform fixture는 검증된 F-60 attribute_samples의 exact MSE/support와도 비교했다. F-60 모듈은9ff1a333dcc45d14577246651f88b28d5935a6dce954b308bb90b1d3f4ccf018의 정확한 바이트를 신규 브랜치에 복사했다. 원래 Untracked 파일을 이동·수정하지 않았고 역사적 loader/CLI는 호출하지 않았다.
irregular grid는 기존 F-60 계약 밖이므로 명시적 NOT_APPLICABLE이며 새로운 F-64 production/oracle 비교는 수행했다. 이를 unittest SKIP이나 F-60 exact replay라고 표시하지 않는다.

## 14. Controller 정적 격리 증거
AST 기반 로컬 전이 import graph8모듈을 검토했다. forbidden dependency, unapproved import, unsafe dynamic call은0이다. 초기 package initializer와 정확히 고정된 역사적 dependency도 검토 범위에 포함했다.
Controller/system/car/submodule/simulator 경로와 Controller 결합 metric 경로를 차단했다. 단순 grep만으로 격리를 주장하지 않았다. 기존 Runtime에 Import/Hook을 연결하지 않았다.

## 15. Controller 동적 비호출 증거
애플리케이션 import 전에 Guard를 설치했다. import finder·builtin import wrapper·Python audit hooks로 Controller import, process/network/native-loader/private-log 접근을 차단한다. 실제 harmless socket/loader/존재하지 않는 private-canary 파일 접근과 합성 audit event 차단을 공개 시험에서 확인했다.
최종 두 테스트 실행과 holdout의 guard count는 모두0이며 실제 Controller import/초기화/호출은0이다.
0은 실제 Controller를 불러 profiler를 붙인 측정치가 아니다. 검토된 graph와 sentinel 아래 forbidden module load가 없었다는 불변조건 증거다. 의도적 음성시험의 거부된 시도는 실제 Controller 호출과 구분했다.
고정된 read-only Git proof 명령만 bootstrap 단계에서 strict process sentinel 이전에 실행했다. Python 계층의 검토된 코드 격리이며 악의적인 임의 Python·OS 전체 sandbox라는 주장은 하지 않는다.

## 16. 공개 fixture 테스트 결과
최종 신규 unittest55개 PASS ×2, FAIL/ERROR/SKIP/XFAIL/XPASS0. exact Test ID ledger가 일치했다.
공개 case22개/실행: valid14 production/oracle 일치, invalid8 정확한 오류 거부. 두 실행의 출력25파일 전체 Byte-identical이다.

## 17. PRE_HOLDOUT_COMMIT
ce8360d561cf85433fa2df072059c2bf887ee5b6
Source·테스트·의존성·기준·공개 증거53파일을 pre_holdout_source_manifest.json에 결속했다. Manifest 자체는 Git blob로 별도 고정했다.
Source Manifest SHA256:8d63245b2d62c7c6bba257e0fcf6d0aee1868c2e1aba7dec25344ebe98d8b36d.
실제 Commit 존재/ancestor/clean tree/현재 바이트·Git blob 일치를 확인한 owner-bound proof가 있어야 seed를 파생한다. 단순40hex 문자열·위조 dict·CLI 다른 표기로 우회할 수 없음을 시험했다.

## 18. holdout seed 파생 과정
정확한 ASCII "F64_HOLDOUT_V1:"+소문자 PRE_HOLDOUT_COMMIT, newline 없음.
SHA256:e19242ec1fb4fa20e52f34a5519abafcf7979fa8742a4014f421f60ce64b4cba.
첫8/다음8바이트 unsigned big endian:
16254127587045210656 / 16514476243234241276.
각 seed%32는0 /28이다. Commit 이후에만 계산했으며 seed 검색·선택·재시도는 없다.

## 19. holdout 단일 실행 결과
한 번의 판정 cohort 안에 사전 고정된 두 독립 reproduction pass를 실행했고, 두 pass가 모두 끝난 후 결과를 확인했다. 지표 실행 프로세스가 하나였다고 표시하지 않는다.
각 pass는 새 valid Source14개를 시도하고 공개 invalid control8개를 재사용했다.22개 case의 지표 비교·예상 오류 검사는 통과했다.
그러나 valid14개 중5개가 공개 valid Source와 정확히 byte-overlap했다.
- linear_ramp_0
- piecewise_constant_0
- piecewise_linear_0
- deterministic_pulse_0
- irregular_valid_0
사전 규칙은 valid source overlap0이므로 F64_HOLDOUT_FAIL이다. 공개 invalid control8개 중복은 애초 계획된 재사용이며 novelty 주장 밖이었다.
metric JSON SHA256:2ce508fcd9f423f1f5813ef61e288ed0c859badbf56d4e892b122d907f0cd7e0.
5개를 제외하거나 대체 seed를 만들지 않았다. 이 자료를 독립적인 개발 미노출 평가집으로 적격 판정하지 않는다.

## 20. 결과 확인 후 변경 여부
Source·계약·threshold·seed 규칙·test definitions·workflow·dependency pin 변경0, holdout 재시도0. first commit의53파일이 그대로다. 이후 추가한 것은 관측 결과·실패 판정·보존 감사·보고서·봉인 자료뿐이다.

## 21. 두 독립 재현성 결과
동일 PRE_HOLDOUT_COMMIT의 별도 clean worktree2개·새 프로세스·분리 출력 디렉터리를 사용했다. bytecode write 금지, 별도 cache prefix, 동일 dependency lock이었다.
공개 fixture25파일, holdout25파일,55 test ledger, contract, fixture/SHA Manifest 및 metric JSON이 각각 Byte-identical이다.
결정성이 통과해도 holdout 분리 실패는 해소되지 않는다. canonical 증거에는 실행 wall clock·임의 temp 경로가 없다. elapsed-time/개발 진단 로그는 외부에 보존하고 Canonical 대상에서 제외했다.

## 22. 전체 테스트 결과
신규55개와 관련 회귀263개는 서로 다른 ID다: Exact157=157(기존5개 포함), Exact27=27, F-60=41, F-61=38. 선택 범위의 고유 unit test는318개다.
신규55개는 최종 Commit 기준 독립2회 PASS. 관련 회귀는 각 검증된 실제 실행에서 PASS했다. 관련 결과를 두 번 실행했다고 합산하지 않았다.
Ruff/Ty/Codespell/compile/YAML 검사 통과. builtin import API의 필수 globals/locals 키워드 보존을 위한 A002 명명 예외만 문서화했으며 security/type 검사를 제거하지 않았다.
초기 RED·개발 오류·리뷰 보강 RED 및 환경 설정 오류는 기록을 보존했다. 실제 회귀 실행의 output-path/모듈 lookup 환경 오류는 수정한 환경에서 다시 실행했으며, 실패 실행을 PASS로 바꾸지 않았다.
Controller를 부르는 전체 upstream suite는 실행하지 않았다. 전체 저장소 CI 성공 또는 모든 실차 시험 통과라고 주장하지 않는다.

## 23. CI 결과
새 독립 Workflow/job f64-contract-oracle을 추가했고 기존 Workflow는 변경하지 않았다. ubuntu-24.04, Python3.12.13, 고정 Action SHA, contents:read, LFS/submodule/credential persistence 비활성이다.
CI_NOT_RUN_AUTHORITY_UNAVAILABLE. PUSH_NOT_RUN_AUTHORITY_UNCONFIRMED.
현재의 새 branch Push 권한을 과거 특정 Commit 승인에서 추정하지 않았다. 수동 dispatch/재실행도 하지 않았다.
Workflow의 테스트/Manifest 검증과 전체 F-64 적격 판정은 구별해야 한다. 현재 작성된 Workflow는 최종 F64_HOLDOUT_FAIL 자체를 독립 fail gate로 승격하는 검사가 부족하므로 향후 게시 전에 별도 수정·검증이 필요하다. 이번 holdout 이후에는 Workflow를 고치지 않았다.
CI는 원본 비공개 보호 archive를 가져오지 않는다. 공개된 before/after 해시 receipt와 local audit 봉인을 검증하는 범위이며 원본 archive 바이트의 재검사는 로컬 감사 증거다.

## 24. 변경 파일 목록
1차 Commit은 신규48파일·기존 수정0이다. 신규 Python 구현/시험 및 정확한 F-60 dependency copy, 계약·feature record2문서, 신규 Workflow, 공개 합성 fixture·Manifest를 포함한다.
정확한 목록은 Git pre-holdout Commit과 SOURCE_DIFF.patch, 최종 두 Commit별 목록은 POST_COMMIT_RECEIPT.json으로 확인한다. 2차에는 실패·검증·봉인 증거만 추가한다. 원본 브랜치4파일은 그대로 Untracked다.

## 25. 기존 봉인 파일 전후 비교
308개 모두 byte-identical. before/after JSON 및 sha256 텍스트도 동일하다. 원래4파일과 Tracked3,278파일 최종 감사도 시작 결과와 byte-identical이었다.
기존 T1 Rate RMS 악화+0.41860706477680765, tail/max 악화, 적격 pair0, NO_ADMISSIBLE_CANDIDATE를 재해석하지 않았다.

## 26. 한계와 미해결 항목
- holdout valid source5개 중복으로 개발 단계와의 요구된 분리를 입증하지 못했다.
- r/budget 미해결이며 fullPASS 불가.
- scalar rate 지표에 한정; curvature/pose/heading/실차 성능은 미평가.
- Python sentinel은 검토된 코드 경계의 증거이며 arbitrary hostile-code containment가 아니다.
- 실제 Controller를 호출해 측정한 call profiler가 아니다.
- 정상 비교 결과에는 실제/독립 기대값·단위가 보존되지만, CLI의 mismatch 실패는 고정 코드 중심이고 확장된 mismatch 진단 snapshot 기능은 제한적이다.
- 새 CI는 실행하지 않았고 최종 실패 STATUS gate 보강도 다음 단계다.
- 이 holdout 시도는 외부 비밀 데이터·실제 주행·Controller 성능·candidate generalization·Private E2/HOLDOUT 증거가 아니다.

## 27. 유지되는 기존 판정
SOURCE_SCHEMA_UNQUALIFIED=6000
D2 PERFORMANCE_NOT_EVALUATED
F19_LEGACY_UNRESOLVED
NATIVE_EXACT_REPLAY_NOT_PROVEN
NO_ADMISSIBLE_NEXT_CANDIDATE
Private E2 NOT_AUTHORIZED
HOLDOUT CLOSED
Vehicle authority NONE
selected_candidate=null
selected_policy=null
RUNTIME_NO_GO

## 28. 최종 ZIP SHA256
e4fb9c305b091cf146f143c23bcc9aa57737be1279b337fe445e448833391ce8
ZIP 자신을 포함하는 순환 해시를 피하기 위해 최종 해시가 기입된 보고서·최종 seal·ZIP SHA 파일은 ZIP 밖에 둔다. ZIP 내부에는 같은 본문의 해시 참조용 보고서와 모든 payload의 파일 Manifest를 포함한다. ZIP 멤버 순서·timestamp·권한은 고정하며 독립 재압축 및 .NET 바이트 검산을 수행한다.

## 29. 다음 단계 허용 여부
이번 F-64에서 코드·seed·기준을 변경하거나 holdout을 다시 실행하지 않는다.
후속으로 가능한 단일 과제는 새로운 버전에서 seed→실제 Source 배열의 다대일 사상과 공개/평가 분리 계약을 보강하는 작업이다. seed metadata만 추가해 hash를 바꾸는 것으로 독립성을 위장하면 안 된다. 새 사전등록과 별도 승인·평가가 필요하다.
T2/T3, 후보 admissibility, Controller·Runtime·차량 적용, prospective evaluation 전체 완료는 모두 허용되지 않는다. 실패를 봉인하고 STOP한다.
