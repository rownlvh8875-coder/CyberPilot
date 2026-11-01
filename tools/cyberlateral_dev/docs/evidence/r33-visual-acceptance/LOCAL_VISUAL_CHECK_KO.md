STATUS: R33_LOCAL_VISUAL_CHECK_PASS

첨부된 저장 출력 전용 묶음의 5페이지를 PC·모바일에서 실제 확인했다. 1440×1250 및 390×844, DPR 1·zoom 100%의 총 10개 case이며, 각 case에서 full-page와 focus를 별도로 캡처해 PNG 20개를 만들고 파일을 직접 열어 확인했다. 표시·탐색 문제와 미확인 필수 항목은 0개다. 제품 계산이나 기존 테스트를 재실행하지 않았고 과거 523 tests/CI/R32.2 PASS를 이번 결과로 재사용하지 않았다.

입력 custody
- R33_LOCAL_VISUAL_KIT.zip: 78,559 bytes.
- SHA256: 8e1ac69e16e0ef164f401d73abd2d1bc5b55956755bc79f7dfb17f60824e2d28. 전달 프롬프트의 canonical 값과 일치.
- ZIP 60개 member CRC 검산 PASS. 중복·대소문자/Unicode 별칭 충돌·Windows 예약 이름·절대/상위 경로·symlink 문제 없음.
- 루트 SHA256SUMS와 reports 아래 모든 SHA256SUMS/PORTABLE_SHA256SUMS, 총 13개 Manifest의 165개 항목을 각 manifest 디렉터리 기준으로 검산했다. 루트는 자신을 제외한 59개 member 전체를 포함한다.
- 새 evidence 폴더의 input에만 추출했다. 캡처·결과는 input 바깥에 저장했다.
- 검사 후 원본 60파일의 전체 SHA·크기·파일 집합을 비교했고 모두 불변이다. 원본 ZIP의 전체 SHA도 동일하며 Manifest 165개 항목의 사후 재검산도 통과했다.
- 과거 RECEIPT의 source/input/output 경로는 따라가지 않았다. 공유 custody에는 상대 경로와 hash만 기록하며 원본 실제 경로·사용자명은 포함하지 않는다. 전후 관찰은 atomic snapshot이나 출처 인증을 뜻하지 않는다.

실제 환경
Microsoft Windows 10.0.26300, 설치된 Chrome 156.0.8078.79, 기존 번들 Playwright Core 1.62.1 및 Node REPL을 사용했다. 새 브라우저 프로세스·새 컨텍스트·임시 프로필, headless, sandbox 활성화, locale ko-KR이다. 사용자 기존 탭·계정·프로필과 기존 WSL 개발판·STEP7·SOURCE·venv·Git 저장소를 열거나 변경하지 않았다. 설치·환경 재설정·정책 변경·HTTP 미러는 없었다. file:// 직접 접근이 허용됐고, 검사 후 만든 브라우저만 종료했다.

각 case의 innerWidth/innerHeight, devicePixelRatio=1, visualViewport.scale=1, document/body CSS zoom=1을 기록했다. 새 프로필의 기본 100% zoom을 사용했다. 페이지에 앱 JavaScript와 외부 자산이 없음을 확인했다. DOM/CSS나 저장 파일을 수정하거나 script를 주입하지 않았다. 읽기 전용 DOM 평가, 뷰포트 변경, 스크롤과 로컬 링크 탐색만 수행했다.

목록 화면의 실제 대조
| 페이지 | 보존된 전체/완료/거절 | 보존된 모델 호출 | 카드 순서 |
| --- | --- | --- | --- |
| success | 2 / 2 / 0 | 5 | COMPLETE, COMPLETE |
| mixed | 3 / 1 / 2 | 1 | REJECTED, COMPLETE, REJECTED |
| rejected | 2 / 0 / 2 | 0 | REJECTED, REJECTED |

이 숫자는 저장된 과거 기록이며 이번 화면 검사의 새 모델 호출은 0이다. 각 PC·모바일 화면에서 요약, 카드 개수·순서·입력 이름·시나리오 ID·입력 SHA·거절 코드를 BATCH.json/TARGETS와 대조했다. 잘못된 JSON은 SCENARIO_JSON, 미존재 입력은 SCENARIO_INPUT_FILE로 구분된다. 미존재 입력의 input_sha256/snapshot은 null이며 원본 snapshot 링크와 성공 report 링크가 없다. COMPLETE 카드의 거절 코드 null이 None으로 표시되는 현재 동작은 프로토콜대로 정상으로 구분했다.

한글·긴 파일명·SHA·링크가 모바일 폭 안에서 줄바꿈되며 겹침·잘림·깨진 문자나 사각형 문자는 보이지 않았다. 10개 case 모두 document scrollWidth=clientWidth로 의도하지 않은 페이지 가로 넘침이 없다. COMPLETE가 실행·리포트 생성 완료일 뿐 독립 수치 검증이나 실차 PASS가 아니라는 상단 설명도 확인했다.

실제 링크 확인
success의 개별 report 2개와 mixed의 COMPLETE report 1개를 각 viewport에서 직접 클릭해 총 6회 탐색하고, 기대한 로컬 member·시나리오 제목·표 행·그래프 수를 확인한 뒤 원래 목록으로 돌아왔다. REJECTED 카드에는 성공 report 링크가 없다. JSON/checksum/snapshot/result를 포함한 총 48회 링크 검사는 현재 input 내부 파일로만 해석해 존재와 SHA를 확인했다. 과거 receipt 경로나 외부 URL을 열지 않았다.

개별 리포트 화면
- sign: 4행, integer_request=[4,-4,4,4], limited_command=[2,-2,2,2], final_command=[2,-2,0,2]. 그래프 2개와 부호 전환이 보인다.
- resumed: 1행, index=5, previous_requested=2, previous_applied=2, final_command=-2, counter=89→90, steer_request=false. 단일 샘플 점과 가운데 index 5가 두 그래프에서 보인다. limited/final=-2의 동일 위치 점 겹침은 저장된 동일 수치와 일치한다.
- 모든 표 셀은 VIEW.json과 일치한다. previous_requested와 previous_applied는 별도 열이며 실제 가로 스크롤 후 두 열이 viewport 안에 들어오는 것을 확인했다.
- 축·범례를 원본 크기에서 읽을 수 있으며 호출 index가 초·10ms·실제 주기가 아니라는 문구와 요청 정규화/정수 명령의 단위 구분이 유지된다. 수치나 limiter를 재계산하지 않았다.
- 표 내부 세로 스크롤은 N/A(4행/1행 모두 표시)다. 페이지 세로 스크롤과 혼동하지 않았다. 페이지가 viewport보다 긴 case는 실제 wheel 이동으로 검증했고, 전체가 들어오는 desktop 목록은 N/A(페이지 overflow 없음)로 기록했다.

캡처 20개와 판정 근거
각 success/mixed/rejected/sign/resumed 페이지의 desktop/mobile별 full·focus PNG를 모두 직접 열었다. 목록 focus는 첫 카드·긴 입력 이름·상태를, 개별 report focus는 그래프를 확인하도록 했다. PNG의 실제 크기·SHA·capture 종류, focus 스크롤 위치와 요청 viewport를 JSON에 구분해 기록했다. full-page 이미지 높이는 문서 길이와 같고 focus는 정확히 1440×1250 또는 390×844다. 문서 전체가 desktop viewport 안에 들어오는 success/rejected에서는 두 독립 캡처의 픽셀이 동일할 수 있다. 실제 20회 캡처했으며 이미지 편집·합성·복사로 증거를 대신하지 않았다. 개인 탭·주소창·계정·개인 경로가 캡처에 들어가지 않는다.

범위와 유지 판정
모든 페이지에서 R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제 r/T2/scale 미정 또는 null과 실차 금지를 확인했다. 개별 report의 미정 문구는 VIEW의 actual_r/T2/vehicle_scale=null과 함께 대조했다. SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO, D2 PERFORMANCE_NOT_EVALUATED, F19 LEGACY_UNRESOLVED, NATIVE_EXACT_REPLAY NOT_PROVEN, 실제 활성화/F70UH/F70V/F71 NOT_ALLOWED를 유지한다.

이번 작업의 새 모델·F61·계산 입력·r/dt·Controller·차량 Runtime·CAN·실차 입력·native qualification·배포·성능 평가·제품 build/compile·기존 테스트 실행은 모두 0이다. Git/Commit/Push/CI는 NOT_RUN이다. 이전 작업에서 준비한 WSL 환경은 이번에 접근하지 않았다. 기준 commit 3783461edcf0fa921adab92c8d1959c5a7262ebb는 인계 자료의 선언값이며 로컬 checkout을 조회해 증명한 값으로 승격하지 않는다.

PASS는 지정된 정적 저장 출력의 화면·링크·보존 검증만 뜻한다. 다른 브라우저/OS/DPR, 출처 인증, 모델 산술·물리 안전·성능·배포 적격성은 검증 범위 밖이다. 결과 ZIP에는 이 보고서·결과 JSON·입력 custody·실제 PNG 20개·새 검산 Manifest만 담으며 원본 kit/과거 환경 receipt는 재전송하지 않는다.
