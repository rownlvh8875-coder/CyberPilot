# R60 — 명시적 클라우드 브라우저 회귀 검사

노트북·과거 evidence 폴더 없이 보존된 sign/resumed 합성 리포트 두 개를 재검사하는
개발 명령입니다. 계산 결과를 새로 만들거나 F61·차량 데이터를 실행하지 않습니다.
기본 DEV/cloud CI의 PASS는 **이 브라우저 검사를 실행했다는 뜻이 아닙니다**.

## 전제와 실행

Git checkout의 `tools/cyberlateral_cloud`와 전체 `tools/cyberlateral_dev` component가
필요합니다. HF의 DEV-only 복구본을 쓰면 cloud 도구는 별도의 Git checkout에서 실행하고,
`--component`에 복구된 component를 지정합니다. 과거 복구본도 허용하므로 오래된 CSS는
실제로 화면 검사에서 FAIL할 수 있습니다. source SHA 기록을 함께 확인하세요.

- Host Python에 Playwright와 Chromium이 이미 설치돼 있어야 합니다.
- `--browser`는 사용할 기존 Chromium 실행 파일입니다. 실제 버전은 결과에 기록됩니다.
- `--app-python`은 고정 DEV 환경의 CPython3.12.13 interpreter입니다. venv의 symlink
  경로를 base Python으로 바꾸지 마세요. app에 Playwright를 설치할 필요는 없습니다.
- 브라우저 정책이 loopback HTTP를 허용해야 합니다. file URL·정책 수정·TLS/proxy
  우회는 사용하지 않습니다. 자동 다운로드·global install·새 로그인도 없습니다.
- 출력 부모는 존재하고 마지막 폴더는 새 외부 경로여야 합니다. component/checkout
  내부, 기존 경로, symlink 출력은 거절하며 원래 파일은 덮어쓰거나 삭제하지 않습니다.

다음 경로는 실제 환경에 맞게 바꿉니다. launcher는 Playwright가 준비된 **host** Python입니다.

```bash
python -B tools/cyberlateral_cloud/browser_smoke.py \
  --component "$PWD/tools/cyberlateral_dev" \
  --app-python "$PWD/tools/cyberlateral_dev/.venv/bin/python" \
  --browser /usr/lib/chromium/chromium \
  --output /workspace/NEW-r60-browser-check
```

## 무엇을 확인하는가

기존 `project/fixtures/r31_report`의 portable 결과 bytes를 그대로 복사하고,
기존 test utility로 **명시적 test receipt**를 구성합니다. 실제 실행 환경의 인증서가
아닙니다. app의 기존 R32 reader/renderer가 여섯 파일 기록을 검산해 HTML을 만듭니다.
새 모델 호출은0입니다. integer/hex 표시는 물리 torque나 실제 시간 증거가 아닙니다.

sign/resumed ×320/360/390/425/1440px, DPR1의 총10건에서 다음을 관찰합니다.

- document 폭=viewport와 실제 가로 이동0. 1px 차이도 허용하지 않습니다.
- footer 제한 문구·16px·보임, 실제 보이는 양수 크기 그래프2개·보이는 축/범례 최소14px.
- 모바일 표에 실제 가로 wheel 입력 후1초 이내의 내부 이동, user-scrollable CSS,
  resumed 단일 점5개가 실제 보이고 중앙에 배치됨·index5 표시.
- CSP 존재·active/external asset 부재, VIEW/checksum 링크 실제 탐색4회.

390/1440px의 top/charts/footer 캡처12개를 남깁니다. 모든 글꼴·브라우저·화면 크기의
가독성이나 전체 접근성을 보장하지 않으므로 필요하면 캡처를 직접 확인하세요.
wheel 검사는 마우스 입력에 대한 한정 검사이지 모바일 touch 기기 적격성 검사가 아닙니다.
실행 host의 Playwright/browser는 app 복구와 별개 전제입니다. 다른 물리 머신이나
브라우저를 독립 설치했다는 증거가 아닙니다.

HTTP는 임시 loopback 포트에서 **메모리로 소유한** HTML/VIEW/checksum 여섯 경로만
제공합니다. receipt·fixture·source root·디렉터리 목록은 제공하지 않습니다.
브라우저의 나머지 요청은 차단하고 FAIL로 기록합니다. DOM/CSS는 수정하지 않습니다.

## 판정과 증거

- exit0 / `R60_BROWSER_SMOKE_PASS`: 명시한10건의 검사가 완료·통과했습니다.
- exit1 / `R60_BROWSER_SMOKE_FAIL`: 검사 완료, 실제 화면 계약 위반이 있습니다.
- exit2: prerequisite/경로/렌더링/브라우저/소스 변경/기록 오류입니다. 성공이 아닙니다.

완료한 검사는 `RESULT.json`, `captures/`, `reports/`, `fixture-inputs/`, 제한된 child
로그와 전체 파일을 닫아 검산하는 `SHA256SUMS.txt`를 남깁니다. RESULT는 checksum
기록 뒤에 생성하는 완료 표시입니다. 기록 실패·crash의 atomic OS 복구 보장은 아닙니다.

R61부터 완료 출력에 `SUMMARY_KO.md`도 남깁니다. 열 개 화면의 **저장된** 판정·측정값·
실패 이유와 실제로 연결 가능한 리포트/캡처 경로를 한국어로 모읍니다. 별도 실행 옵션이나
새 브라우저 검사는 없습니다. 전체 실패 기록은 개별 case가 PASS여도 표시합니다.
null과 field 누락은 구분하며, 누락을 0으로 추정하지 않습니다. 이 요약은 source/수치/
출처/차량 검증을 추가하지 않으며 원래 RESULT V1·stdout·exit0/1/2는 그대로입니다.
요약은 checksum과 RESULT보다 먼저 기록되고 같은 closed checksum에 포함됩니다.
따라서 부분 실패 폴더의 요약만 보고 완료로 쓰면 안 됩니다. RESULT 존재와 전체 검산이
필요합니다. 이 파일은 fresh producer 결과의 표시용이며 임의 저장 JSON을 여는 reader가 아닙니다.

안전한 출력 생성 뒤 실패하면 부분 결과와 `FAILURE.json`을 보존합니다. 권한/디스크
오류로 실패 기록 자체가 불가능할 수도 있으므로 RESULT 없이 성공으로 쓰지 마세요.
preflight 거절은 출력 폴더를 만들지 않습니다. 재시도는 반드시 새 경로를 사용합니다.

고정 fixture/renderer source16개와 입력·리포트의 전후 SHA를 비교합니다. 전체 checkout/
venv snapshot, concurrent writer 방어, 출처 인증은 아닙니다. 저장값의 checksum 일치는
독립 수치 참조·실차 성능·배포 승인으로 승격되지 않습니다. 출력에는 로컬 환경 경로가
포함될 수 있으므로 자동 업로드하지 말고 공유 전에 점검하세요.

R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제r/T2/scale=null,
Candidate/Runtime NO_GO, F70UH/F70V/F71 및 실차 활성화 비허용을 유지합니다.
기본 unit/gate의 추가 합성 계산은 별도 NONZERO/미집계이며 이 명령의 모델0과 구분합니다.
