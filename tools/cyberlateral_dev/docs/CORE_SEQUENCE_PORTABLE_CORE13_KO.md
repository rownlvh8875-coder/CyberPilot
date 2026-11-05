# CORE13 — 저장된 세 case 묶음의 portable ZIP

CORE12가 이미 저장한 `sign-cycle`, `declared-difference`, `late-invalid` 폴더를
모델 재실행 없이 한 ZIP으로 옮길 수 있다. 원본9파일의 bytes는 그대로다.
저장-only 요약과 Manifest를 추가하며 ZIP 생성·검증의 신규 모델/reference 실행은0이다.
원래 기록된 MATCH/DIFFERENT/REJECTED를 성공으로 승격하지 않는다.

## 사용

프로젝트 폴더에서 기존 개발 Python으로 실행한다. 입력은 기존 CORE12 suite이고
출력은 checkout·입력 폴더 밖의 **아직 없는 파일**이어야 한다. 부모는 미리 있어야 한다.

```bash
.venv/bin/python -I -B tools/core_sequence_portable.py export \
  --input-root /external/saved-suite --output /external/new-suite.zip
.venv/bin/python -I -B tools/core_sequence_portable.py verify \
  --archive /external/new-suite.zip --sha256 FULL_LOWERCASE_SHA256_FROM_EXPORT_RECEIPT
```

위 SHA 자리에는 신뢰하는 인계 경로에서 받은 전체64hex 소문자 값을 넣는다.
검증하려는 ZIP 자체에서 SHA를 새로 계산하는 것만으로 독립적인 원본 인증이 되지 않는다.
API는 `integration_tools.core_sequence_portable`의 `export_saved_suite(Path, Path)`와
`verify_suite_archive(Path, str)`이다. stdout은 canonical JSON receipt뿐이다.
exit0은 custody 검사를 마쳤다는 뜻이고, exit2는 오류다. run/extract/upload 명령은 없다.
별도 sidecar 파일을 자동 생성하지 않으므로 receipt의 전체 SHA를 함께 보관한다.

## 정확한 형식과 검사

ZIP에는 다음11개 regular file만 있다. 폴더 entry는 없다.

```text
SHA256SUMS.txt                   # 나머지10개 전체 SHA
SUITE_REPORT.json                # 같은 원본 bytes에서 재생성한 CORE12 check 요약
suite/<각 세 case>/INPUT.json
suite/<각 세 case>/RESULTS.json
suite/<각 세 case>/SHA256SUMS.txt
```

이름 정렬, ZIP_STORED, 1980-01-01 시각, Unix0644 member mode, comment/extra 없음으로
같은 입력은 출력 경로·실행 시각과 무관하게 같은 ZIP bytes가 된다. ZIP 파일 자체의
게시 권한은0600이다. 기록된 과거 작업량과 신규 작업량은 별도 필드다.
baseline을 비교하지 않으므로 차이 개수는null, NOT_REQUESTED는3이다.

검증은 압축을 풀지 않는다. 외부 SHA 형식을 파일 접근 전에 검사하고 전체 SHA·CRC·
길이·고정 이름·중복·각 Manifest·원본 schema/닫힌 Gate/case label·저장-only 요약을
검사한다. 마지막에는 canonical ZIP 재생성 bytes와 exact 비교한다. 전체 ZIP 한도는
2,000,000bytes, 중앙 디렉터리는4096bytes/11entry다. 입력별 한도는 기존 CORE9와 같고
추가 보고서는65536bytes, root Manifest는4096bytes다. symlink/FIFO/경로 링크·추가 파일·
압축·암호화·다른 순서/metadata·앞뒤 덧붙임은 거절한다.

## 파일 보호와 실패

원본9개를 한 번씩 캡처하고 검증한 뒤에만 output을 exclusive/no-follow로 만든다.
부분 쓰기를 처리하고 close 후 실제 게시 파일을 한 번 bounded readback하여 검산한다.
쓰기·close 실패는 PARTIAL_FILE_POSSIBLE, readback 실패는 FILE_MAY_EXIST 또는
PUBLISHED_ARCHIVE_MISMATCH 계열 오류를 반환한다. 성공 receipt는 그 뒤에만 출력한다.
실패한 파일은 남을 수 있으며 덮어쓰기·삭제·자동 재시도하지 않는다.

부모 경로를 바꾸는 악의적 동시 작업에 대한 race-free 증명, atomic snapshot,
fsync/durability, 현재 소스/빌드/실제 배포본의 인증은 제공하지 않는다. 협력적인 로컬
개발 파일시스템을 전제로 한다. 일관되게 조작된 기록과 Manifest를 모두 새로 만든 경우는
통과할 수 있다. SHA 검증은 서명·소유자 승인·산술 재계산·차량 안전 인증이 아니다.

## 유지되는 제한

실제 r/T2/차량 scale=null, R_BUDGET=UNRESOLVED, Static Evidence Gate=FAIL이다.
F61·Controller·Runtime·CAN·실제 r 계산은 실행하지 않는다. 실차 활성화 및
F70UH/F70V/F71은 NOT_ALLOWED다. 단위 테스트가 만드는 합성 fixture 실행량은
전체 테스트 작업이며 export/verify 자체의 신규 실행0과 혼동하지 않는다.

다음 독립 범위는 portable archive를 입력으로 받는 명시적 저장-only 비교 설계다.
이 기능에는 archive unpack/복원·모델 재실행·policy 확정·배포를 추가하지 않았다.
