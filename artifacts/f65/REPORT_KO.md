# F-65 실제 Source 분리 및 최종 상태 Gate — 한국어 보고서

## A. 최종 판정
F65_SOURCE_SEPARATION_PARTIAL_PASS_R_BUDGET_UNRESOLVED

Controller 비호출 합성 Source 분리·지표 계약·최종 상태 Gate는 검증 범위에서 통과했다. r 예산은 미해결이며 prospective evaluation 전체, candidate admissibility, 실제 성능·안전성·Runtime을 승인하지 않는다. F-64의 F64_HOLDOUT_FAIL은 그대로 유지한다.

## B. 기준 및 Git Identity
- Base:04ae0f6644c7e94b8ed601c46fc45ccff03d0476.
- Branch:feature/f65-source-separation-contract.
- PRE_HOLDOUT_COMMIT:687d0efe213b3825993cf48849a8a6dab0584364.
- 부모는 F-64 최종 Commit이며 기존 파일 변경0, 신규31파일로 계약·코드·테스트·공개 증거를 고정했다.
- Source/tests/criteria/dependency/공개 증거136파일 및 Manifest Git blob를 결속했다.
- Manifest SHA256:2978225981e3b62e78771387f44a7ba5fae1a083a134608f119f6b9d9395f01b.
- 최종 증거 Commit SHA는 자기참조를 피하기 위해 외부 POST_COMMIT_RECEIPT.json 및 최종 응답에 기록한다.
- 원격 Push/PR/CI 수동 실행은 하지 않았다. 원래 feature/cyber-autotune의 HEAD588d6b21c21089065a7d9165d6e7a438e8aa6297도 변경하지 않는다.

## C. 기존 실패 원인과 보존
F-64는 seed를32개 amplitude class로 축소해, 유효 평가 Source14개 중5개가 개발 자료와 같았다. 해당 결과·기준·ZIP을 수정하거나 새 결과로 재분류하지 않았다.
F-64 ZIP SHA256:
e4fb9c305b091cf146f143c23bcc9aa57737be1279b337fe445e448833391ce8
시작 시 Python 및 Windows .NET 재검산이 일치했다.
이전 F-60~F-64 봉인 자료·Source·참조413파일이 작업 전후 정확히 동일했다.
보호 Manifest 공통 SHA256:
7b7e6db192fc5778cdfcb9dc8975f06d5388672ec4f719430f3edc4bf603c1bc
원본 Tracked3278 및 Untracked4도 별도 F-63 감사로 확인했다. 원본 RLOG·T1 분석을 재실행하지 않았다.

## D. 메타데이터가 아닌 실제 관측값 분리
저수준 데이터 형식·단위·int64 ns 검증은 기존 F64_SYNTHETIC_SOURCE_V1을 그대로 쓴다. Generator provenance만 F65_SEPARATED_ACTUAL_SIGNAL_V1로 새로 부여했다. 역사적 차량 Source를 이름만 바꾼 것이 아니다.

D=2^63-1
A=2^62+(seed>>2)
첫 실제 관측값: PUBLIC은+A/D, EVALUATION은-A/D.
첫 실제 간격:10000000-(seed&3)ns.

D는 signed-int64의 최대 양수다.0.5<A/D<=1이며, 실제 관측값·시간으로 seed의 high62/low2 bits를 복원한다.
같은 family/count에서 실제 첫 값과 첫 간격이 같으면 seed64bit 전체가 같다. 같은 split 내부의 seed→실제 배열 사상은 이 범위에서 injective하다.
PUBLIC과 EVALUATION은 첫 관측값 부호가 달라 어떤 seed/family/count에서도 배열이 같을 수 없다.
기존 F-64 관측값은 magnitude<=63/1024이므로 새로운 EVALUATION 첫 magnitude>0.5와 같을 수 없다.

이 분리는 의도적으로 구성한 소프트웨어 시험 분포다. 통계적 독립성·현실 대표성·candidate generalization의 증거가 아니다. 작은 seed label·filename·header만 바꿔 hash를 달리하는 방식도 아니다.
Fingerprint는 모든 절대 time_ns와 모든 gcd-reduced rational value로 계산하며 filename/provenance를 제외한다. 같은 값을 다른 분수표현으로 쓴 경우도 동일 fingerprint다.

## E. Source·시간·지표 범위
7개의 순수 합성 family를 유지하되 새 생성 규칙을 명시했다: constant, integer-quantized linear_ramp, piecewise_constant, piecewise_linear, deterministic_pulse, bounded_noise, irregular_valid.
Source count2..8000, exact uint64 seed, canonical timestamp/interval은 int64 ns, float time 거부. 기존 F-64의 단일 샘플 입력 의미는 변경하지 않았다. F-65는 seed 복원에 필요한 두 관측점 이상만 생성한다.
r·물리 limit·모델·tuning 값은 추가하지 않았다. 진폭의 bit 분할은 정수 저장 폭과 Source 분리 목적이며 차량 gain이 아니다.

지표는 기존 F-64 production Fraction 연산과 독립 integer oracle을 수정 없이 재사용한다. 인접 N-1 Rate RMS의 정확한 유리수 radicand, p95/p99, 최대 Rate/차분 등 같은 계약이다. 실제 곡률·Position·Heading·물리 조향 지연을 계산하거나 추정하지 않는다.

## F. 사전 노출 자료와 새 평가
공개 fixture는 seed0/1,7family,count17의14개다.
공개 unit test가 사용한 EVALUATION 모양의 Source도 노출로 처리했다. 선언된10개 seed×7family×2split의140개 기록과 기존 F-64 실제 valid28개 기록을 비교 대상에 포함했다. 중복이 있는 노출 기록을168개의 서로 독립적인 데이터라고 주장하지 않는다.
시험한 다른 길이2/8000은 length 자체가 새 평가 count17과 달라 동일 배열이 될 수 없다.

평가 seed는 코드/계약 Commit 이후에만 생성했다.
SHA256(ASCII "F65_HOLDOUT_V1:"+lowercase PRE_HOLDOUT_COMMIT), newline 없음:
74e2caf97180f8aba430e82478490835de005868430ec9c8c6c15be1f3b1dec2
첫8/다음8바이트 big-endian uint64:
8422517425836193963 /11831211464436811829

고정된 두 reproduction pass를 모두 마친 후 한 번 판정했다. 각 pass는 생성과 봉인 bundle 검증을 포함한다. Bundle verifier는 같은 Source/지표를 재계산해 무결성을 확인하지만 seed 선택이나 새 판정 기회를 만들지 않는다.
결과 확인 이후 Source/기준/seed/테스트/Workflow 수정·재시도0회다.

## G. 실제 평가 결과
| 항목 | 결과 |
|---|---|
| 새 평가 Source |14개/실행 |
| 공개·개발 노출·F-64 기록과 실제 배열 중복 |0 |
| production/독립 oracle 불일치 |0 |
| Controller 호출 |0 |
| 최종 bundle Gate 종료 코드 |0,0 |
| 신규 테스트 |28 PASS×2 |
| 공개 산출물 |18파일×2 Byte-identical |
| 평가 산출물 |18파일×2 Byte-identical |
| 최종 결과 JSON SHA256 |65139bddb3297965e28521a458133f5e508e6e640d18621bf6842cf6f08ffc35 |

Source 분리 및 정확한 지표 계산이 입증된 범위다. T1 악화 해결이나 실제 차량 출력 개선이 아니다.

## H. 보안·상태 Gate
Source Manifest는 모든 승인 신규 파일, F-64의100파일, 유지할 설정·의존성까지 정확한 필수 집합을 검사한다. 비어 있거나 모듈이 누락된 Manifest를 성공 처리하지 않는다. bytes/SHA256와 Git blob를 대조한다.
Bundle은 정확한17개 inventory 항목 및 실제18개 파일을 검증한다. 단순 파일 개수만 맞춰 통과할 수 없다. 각 fixture는 spec에서 다시 생성하고 실제 값·시간 fingerprint 및 metric 결과까지 비교한다.
reader는 dir_fd/O_NOFOLLOW로 모든 경로 구성요소의 symlink 우회를 거부한다.

최종 Gate는 F65의 Source-only partial status만 수용한다. 실제 F-64 실패 seal, FAIL/BLOCKED/PENDING/UNKNOWN/누락 상태는 거부한다.
실제 CLI에 F-64 실패 seal을 넣은 시험은 exit1이었다. 기존 단위 테스트가 통과했다는 이유로 실패한 최종 상태가 CI 성공으로 포장되지 않도록 새 job에 terminal --verify-bundle 단계가 있다.
Controller guard를 application import 전에 설치하고 기존 F-64 전이 graph 및 새 두 모듈을 확인했다. 동적 import/process/network/native-loader/private-log sentinel의 검토 범위에서 호출0이다. 실제 Controller를 불러 profiler를 붙인 증거나 적대적인 임의 Python에 대한 OS sandbox라는 주장은 하지 않는다.

## I. 회귀·독립 검산
고유 unit test 총346개:
- 신규 F-65:28
- 기존 F-64:55
- Exact157:157(기존5개 포함)
- Exact27:27
- F-60:41
- F-61:38

신규28개는 최종 source commit의 두 독립 환경에서도 모두 PASS였다. 관련318개는 실제 실행 결과 PASS이며 두 번 실행했다고 합산하지 않았다.
Ruff/Ty/Codespell/Compile/YAML 통과. Source·원시 데이터·기존 테스트를 수정해 통과시키지 않았다.
초기 missing-API RED, 최소 길이 carrier 반례, 불완전 manifest·symlink 반례를 재현하고 사전 Commit 이전에 수정했다. 개발 진단 로그는 외부에 유지하며 elapsed-time/path처럼 변하는 값은 canonical 봉인 대상에서 제외했다.
두 clean worktree·분리 프로세스·출력 폴더·bytecode write 금지·동일 환경으로 재현했다. 원본413파일에는 Python과 독립 Windows .NET 해시 검산을 적용했다.

## J. 변경 및 CI
신규 Python3파일, 계약/feature record2문서, 신규 독립 Workflow와 증거만 추가했다. 기존 F-64 및 Exact157/Exact27 Workflow를 변경하지 않았다.
새 job: f65-source-contract; ubuntu-24.04, Python3.12.13, SHA-pinned Actions, contents:read, LFS/submodule/credential persistence 비활성.
CI_NOT_RUN_AUTHORITY_UNAVAILABLE
PUSH_NOT_RUN_AUTHORITY_UNCONFIRMED
로컬 Gate 검증과 실제 GitHub 실행은 별개다. 기존 전체 CI 실패를 성공으로 바꾸거나 Required Check를 우회하지 않았다.

## K. 한계와 유지 판정
r budget은 R_BUDGET_UNRESOLVED다. Source의 수학적 분리는 전체 prospective 평가의 완료나 Controller 입력 자격을 입증하지 않는다.
새 Source는 의도적으로 설계한 정수·유리수 시험용 파형이다. 실제 주행 로그·독립 실차 holdout·candidate generalization 자료가 아니다.
F-64 실패, T1 Rate RMS 악화+0.41860706477680765, 기존 적격 pair0을 그대로 보존한다.

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

## L. 전달 및 다음 단일 과제
코드 Diff·preregistered contract·실제 fixture/metric·상태 Gate·보존 및 재현성 증거·SHA256 Manifest를 제공한다.
ZIP 순서·timestamp1980-01-01·regular0644를 고정하고 독립 재압축 및 .NET 멤버 해시를 확인한다. ZIP 자신과 최종 ZIP SHA/seal은 ZIP 밖에 둔다.
최종 ZIP SHA256:
9941a124a1ecbc49b897df47adecd658a1b239ba21f065a6967156db8cbfce14

다음 단일 실행 과제는 별도 승인 후 이 정확한 F-65 브랜치를 게시하여 새 Source 계약 job의 GitHub 자동 실행을 검증하는 것이다. 현재는 로컬 봉인까지만 수행한다. r 미해결·후보·Runtime NO-GO는 해제하지 않는다.
