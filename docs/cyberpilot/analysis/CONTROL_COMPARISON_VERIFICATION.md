# Step 3 검증 기록

기준일: 2026-09-29. 대상은 같은 디렉터리의
[분석 문서](CONTROL_COMPARISON.md)와 [고정 소스 목록](CONTROL_COMPARISON_SOURCES.json)이다.
runtime 테스트 결과가 아니다.

## 확인 항목

| 확인 | 결과 | 근거 / 범위 |
| --- | --- | --- |
| Remote 실제 기본 브랜치 확인 | 확인 | 각 remote에서 `git ls-remote --symref <remote> HEAD`; OpenPilot/Sunny master, Carrot carrot2-v6 |
| 세 remote fetch | 성공 | `git fetch --prune openpilot`, Sunny/Carrot 기본 브랜치 filter=blob:none fetch, 종료 0 |
| 고정 SHA와 root remote-tracking ref 일치 | 확인 | source manifest의 O/S/C commit과 `git rev-parse remote/branch` 일치 |
| Source JSON 구조/소스 객체 | 확인 | 35 groups, 75개 source file의 pinned `git show` 성공; missing path 0 |
| 함수/클래스 anchor | 확인 | 94개 symbol 문자열의 해당 group 소스 내 존재 확인; 미존재 0. 실제 call/data-flow 분석을 대체하는 semantic proof가 아니라 참조 오타 검사 |
| opendbc dependency identity | 확인 | OD/SD의 parent `git ls-tree` mode 160000 및 SHA와 isolated fetched commit 일치 |
| Source key 참조 | 확인 | 본문에서 사용한 35개 O/S/C group key가 모두 manifest에 존재 |
| 비교표 요구사항 | 확인 | 종방향 16 + 횡방향 15 = 31 rows; 두 표 모두 요구한 11 columns |
| JSON/문서 encoding | 확인 | UTF-8 strict decoding, CR 없음, LF final newline; trailing whitespace 검사 |
| 문서 링크/경로 | 확인 | 문서 내 local 링크 대상 존재; 고정 GitHub source 링크를 manifest 경로/commit과 대조. 네트워크 HTTP 전체 링크 검사는 하지 않음 |
| 기존 tracked 파일/인덱스 보존 | 확인 | `git diff --exit-code`와 `git diff --cached --exit-code` 모두 종료 0 |
| History/root submodule 보존 | 확인 | root `--is-shallow-repository`는 false; 기존 여섯 uninitialized gitlink 동일 |
| 기존 Step 2 문서 | 보존 | AGENTS.md와 FEATURE_CHANGE_TEMPLATE.md를 수정/commit하지 않음 |
| Build/unit/safety/replay/simulation/shadow | **미실행** | 준비된 Linux 환경/모델/주행 입력에 대한 실행이 없음. 이번 작업은 문서와 정적 분석 |
| 실제 차량 개선/안전/도로 사용 | **미검증** | runtime/empirical evidence 및 적용 권한을 확보한 단계가 아님 |

## 참조 검사를 재현하는 PowerShell 예시

repository root에서 실행한다. reference DB가 없다면 manifest의 OD/SD URL과
정확한 commit을 별도 디렉터리에 fetch한다. root submodule pin을 변경해서
Sunny 코드로 대체하지 않는다. 아래 검사는 문서 anchor/객체 확인만 한다.

```powershell
$manifest = Get-Content -Raw docs/cyberpilot/analysis/CONTROL_COMPARISON_SOURCES.json | ConvertFrom-Json
$problems = @()
$fileCount = 0
$symbolCount = 0
foreach ($group in $manifest.sources) {
  $repo = $manifest.repositories.($group.repo)
  $gitDir = switch ($group.repo) {
    'OD' { 'work/reference-opendbc-openpilot' }
    'SD' { 'work/reference-opendbc-sunnypilot' }
    default { '.' }
  }
  $combined = ''
  foreach ($path in $group.paths) {
    $lines = & git -C $gitDir show ($repo.commit + ':' + $path)
    if ($LASTEXITCODE -ne 0) { $problems += "unreadable: $($group.id) $path" }
    else { $fileCount++; $combined += ($lines -join "`n") + "`n" }
  }
  foreach ($symbol in $group.symbols) {
    $symbolCount++
    if (-not $combined.Contains($symbol)) { $problems += "missing symbol: $($group.id) $symbol" }
  }
}
[pscustomobject]@{ files=$fileCount; symbols=$symbolCount; problems=$problems }
if ($problems.Count -gt 0) { throw 'Source reference check failed' }
```

추가 확인 명령:

```powershell
git rev-parse HEAD openpilot/master sunnypilot/master carrotpilot/carrot2-v6
git rev-parse --is-shallow-repository
git ls-tree HEAD opendbc_repo panda
git submodule status
git diff --exit-code
git diff --cached --exit-code
git status --short --branch
git diff --no-index --check -- NUL docs/cyberpilot/analysis/CONTROL_COMPARISON.md
git diff --no-index --check -- NUL docs/cyberpilot/analysis/CONTROL_COMPARISON_SOURCES.json
git diff --no-index --check -- NUL docs/cyberpilot/analysis/CONTROL_COMPARISON_VERIFICATION.md
```

마지막 세 명령은 새 파일 전체를 검사하기 위해 NUL과 비교한다. `--no-index`는
파일 차이가 존재할 때 **종료 1이 정상**일 수 있다. whitespace 오류 메시지와
종료 2 이상을 별도로 확인하고, trailing whitespace/CR/UTF-8/final LF를 직접
검사했다. tracked diff만 검사하면 untracked 신규 문서가 누락되므로 충분하지 않다.

## 발견 및 정정한 조사 도구 문제

- 초기 manifest에서 `ModeManager`, `TorqueEstimatorSP`를 참조했으나 실제
  클래스는 `ModeTransitionManager`, `TorqueEstimatorExt`였다. 첫 anchor 검사
  종료 1을 유지한 뒤 두 문서 참조를 정정하고 94개 anchor를 다시 확인했다.
- 초기 whitespace wrapper는 `--no-index --check`의 종료 1을 모두 실패로
  간주했다. 실제 Git 출력에는 whitespace 진단이 없었고 NUL과 신규 파일의
  차이만 있었다. source code 수정 없이 진단 출력과 직접 byte/line 검사를
  사용해 재확인했다. 검증 기준을 완화하거나 실패를 삭제한 것이 아니다.
- Partial-fetch source 조회 중 일부 Carrot blob에 대해 다른 promisor remote가
  `not our ref`를 반환한 뒤 해당 remote에서 blob을 얻은 경우가 있었다. 최종
  확인은 branch 이름을 추정하지 않고 manifest의 고정 SHA와 75개 source 객체를
  다시 읽어 모두 성공했음을 확인했다. 초기 stderr를 숨겨 fetch가 모두 실패했거나
  반대로 필요한 코드가 없는 채 분석을 끝낸 것으로 보고하지 않는다.
- 조사 중 잘못 시도한 두 경로(`controls/lib/controlsd_ext.py`,
  `controls/lib/carrot_functions.py`)는 실제 tree 목록으로 바로잡았다.
  최종 경로는 각각 Sunny `controls/controlsd_ext.py`, Carrot
  `selfdrive/carrot/carrot_functions.py`이며 manifest path 검사에서 확인했다.

## 변경/권한 범위

Step 3의 commit 대상은 세 분석 문서다. Step 2 기존 두 파일은 별도 변경으로
남아 있다. 로컬 reference DB와 `.git/info/exclude`는 공유 commit 대상이 아니다.
commit/push/merge, 제어 코드·스키마·안전 한계·gitlink/LFS 변경과 기기/차량 쓰기는
하지 않았다. 연구 후보의 성능/라이선스/모델/신뢰 경계는 본문의 미확인 항목을 따른다.
