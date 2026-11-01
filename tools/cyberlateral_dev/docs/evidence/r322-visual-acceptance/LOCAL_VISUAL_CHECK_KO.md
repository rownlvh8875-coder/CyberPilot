STATUS: R322_LOCAL_VISUAL_CHECK_PASS

수정된 두 리포트를 격리된 Chrome에서 직접 열고 1440×1250 및 390×844, DPR 1의 네 화면 조합을 실제 검사했다. 캡처 12개를 생성해 원본 크기로 열어 확인했다. 모바일 축 눈금과 호출 index 설명을 읽을 수 있었고, 범례는 항목 단위로 줄바꿈됐다. 이번 화면 검사에서 표시 문제는 발견하지 않았다.

입력 검산
R322_LOCAL_RECHECK_KIT.zip은 32,251 bytes이며 SHA256은 2e75a224226146d74d4067b5df57e7798d115c88c35b35e6f4e716fca07fccc0이다. 외부 sidecar의 파일명·SHA와 일치한다. ZIP 15개 member CRC, root KIT_SHA256SUMS의 14개 항목 전체 coverage, 리포트별 nested Manifest의 6개 항목을 검산했고 불일치는 0개다. 중복·대소문자 충돌·절대 경로·경로 탈출·symlink entry는 없었다. 새 저장소 외부 evidence 폴더로 안전하게 추출했으며 기존 ZIP이나 저장소 파일은 덮어쓰지 않았다.

검사한 HTML identity
- sign: b8535cde724968f3877b83cb893ba75d9a0b4bf96db2e0ca9e9f487bbf041eea
- resumed: 5a0b6507c26e04fd767356d85facf49fa749aa3cfbbc0a360b614b0488150122
문서에 지정된 SHA와 일치한다. report-local-*/index.html만 화면 대상으로 열었다. local-visual-input 폴더의 이전 VIEW는 byte 비교용으로만 읽었다. sign VIEW 7,505 bytes 및 resumed VIEW 6,331 bytes는 이전 VIEW와 각각 byte-identical이다.

문서와 사용자 요청의 구분
사용자가 요청한 START_HERE_KO.md의 화면 검사 절차를 현재 요청 범위 안에서 적용했다. 문서에 있는 과거 PASS·출처·코드·배포 주장은 이번 결과의 권한 또는 화면 판정으로 사용하지 않았다. 보조 검사 문서가 원래 전체 Evidence 파일명을 언급하지만 실제 입력은 사용자가 지정한 RECHECK_KIT과 sidecar다. 제공되지 않은 원본 전체 Evidence를 찾거나 검증했다고 주장하지 않는다. KIT Manifest 무결성은 출처 인증·실차 적격성 증명이 아니다.

실제 브라우저 환경
OS Microsoft Windows 10.0.26300, PowerShell 7.6.5, 검산 Python 3.14.7. 설치된 Chrome 156.0.8078.79와 기존 번들 Playwright Core 1.62.1을 사용했다. 새 브라우저 프로세스·새 컨텍스트·임시 프로필, headless, sandbox 활성화, locale ko-KR, DPR 1이다. 사용자 기존 탭·로그인 세션·프로필을 사용하지 않았다. file://로 직접 열렸고 관리자 차단은 없었다. 정책·보안 설정 변경, HTTP 미러, 의존성 설치는 0이다. 만든 브라우저만 종료했다.

검사별 관찰
- 축 가독성: 네 조합에서 .y-ticks, .x-ticks, .axis-caption, .legend의 computed font-size는 14px다. 요소와 자식의 실제 bbox를 JSON에 기록했다. 390px 화면의 tick 자식 bbox 높이는 약 16.8px이며 원본 캡처에서 숫자와 NOT seconds 설명을 읽을 수 있다. 14px 조건만으로 PASS를 정하지 않고 실제 캡처를 직접 확인했다.
- 배치: 축 글자·제목·선·범례가 겹치거나 잘리는 현상은 보이지 않았다. 모든 조합의 document scrollWidth가 viewport 폭과 같아 페이지 전체 가로 overflow가 없다. 좁은 화면은 그래프가 세로로 배치된다.
- 범례: .legend-entry의 white-space는 nowrap이고 각 텍스트는 한 줄 fragment다. 모바일에서는 integer_request / previous_applied와 limited_command / final_command가 항목 단위 두 줄로 배치된다. 단어 일부가 다음 줄로 끊기지 않는다.
- 그래프: 각 리포트에서 2개를 확인했다. sign 부호 전환이 보이고, resumed 단일 샘플 점과 중앙 index 5가 두 그래프에서 보인다. resumed의 limited/final 값은 둘 다 -2여서 동일 위치의 점이 겹치며, 이를 누락으로 오인하지 않았다.
- 표: previous_requested와 previous_applied가 별도 열이다. 실제 horizontal wheel 이동과 두 열을 함께 보이게 한 캡처를 확인했다. 네 조합 모두 모든 셀이 VIEW.json과 일치한다.
- 스크롤: 표 가로 스크롤과 문서 세로 스크롤은 네 조합 모두 실제 wheel 동작으로 확인했다. 표 내부 세로 스크롤은 NOT_APPLICABLE이다. sign 4행, resumed 1행이 이미 모두 보이며 clientHeight=scrollHeight다. CSS나 행을 인위적으로 바꾸지 않았다.
- 한글·제한: 한글 깨짐이나 사각형 문자는 보이지 않는다. 호출 순서가 실제 초·10ms·주기가 아니라는 문구, NOT seconds, 정규화 표현/정수 명령의 단위 구분, Static Gate FAIL 및 R_BUDGET UNRESOLVED 제한이 유지된다.

수치 대조
sign은 4행이며 integer_request=[4,-4,4,4], limited_command=[2,-2,2,2], final_command=[2,-2,0,2]다. resumed는 1행, index=5, angle_counter_before=89, angle_counter_after=90, final_command=-2, steer_request=false다. 저장된 VIEW와 DOM 표 및 실제 화면을 대조했으며 공식 재계산이나 모델 재실행은 하지 않았다.

캡처와 보존
각 리포트의 desktop, mobile, mobile-charts, mobile-full, desktop-table-previous, mobile-table-previous를 보존했다. 총 12개이며 모두 직접 열어 확인했다. viewport 캡처는 정확히 1440×1250 또는 390×844다. mobile-full은 동일한 390×844 viewport의 전체 문서 캡처로 sign 390×2755, resumed 390×2662다. 캡처를 합성·편집하지 않았고, 브라우저 주소창·개인 경로·계정·기존 탭을 포함하지 않는다.

리포트 8개 파일(index.html, VIEW.json, RECEIPT.json, SHA256SUMS.txt 각 2개)의 검사 전후 SHA와 크기가 모두 일치한다. 결과 JSON에는 체크별 PASS/NOT_APPLICABLE, 실제 viewport, font-size/bbox, 스크롤 이동, 수치 대조, PNG 크기/SHA를 기록했다. 미확인 필수 화면 항목과 표시 문제는 0개다. 다른 브라우저·OS·DPR·실제 장치 동작은 검사 범위 밖이다.

금지 동작과 한계
코드·리포트 수정, 모델/F61/calculator import·실행·compile, Controller·Runtime·CAN, 실제 차량·주행 로그, r/dt 계산, benchmark, 설치·배포, 저장소 쓰기·Commit·Push·CI는 모두 0이다. 저장소 HEAD/index/untracked bytes는 이번에 조회하지 않았다. 결과는 지정된 정적 리포트의 표시 검증이며 모델 산술·물리 안전·실차 성능·배포 승인이 아니다.

R_BUDGET=UNRESOLVED, Static Gate=FAIL, actual r/T2/vehicle scale=null, Candidate/Runtime=NO_GO, 실제 활성화 및 F70UH/F70V/F71=NOT_ALLOWED를 유지한다.
