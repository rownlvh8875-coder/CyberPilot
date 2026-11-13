# CORE70 — 참조 대조 결과와 한국어 요약을 한 번에 저장

[CORE69 참조 검사](RECORDING_DIAGNOSTICS_REFERENCE_CORE69_KO.md)를 정확히 한 번
실행하고 전체 JSON·한국어 요약·체크섬을 새 외부 폴더에 저장하는 개발 tree 명령이다.
모델 산술·참조 helper·입력 검증이나 기존 API를 변경하지 않는다.

## 사용

`tools/cyberlateral_dev`에서 [CORE61 입력 예제](RECORDING_INPUT_CLI_CORE61_KO.md)의
첫 Python block으로 새 외부 폴더의 INPUT.json을 만들고,
[CORE64 저장 명령](RECORDING_INPUT_WORKFLOW_CORE64_KO.md)으로 saved 두 파일을 만든다.
이 예제의 입력 생성은 모델0이며 CORE64는 명시적 합성 모델1step이다.
이어서 다음을 실행한다. reference_report는 아직 존재하지 않아야 한다.

```bash
core70_input_sha=$(sha256sum "$CORE61_EXAMPLE_DIR/INPUT.json" | cut -d ' ' -f 1)
core70_diagnostic_sha=$(sha256sum "$CORE61_EXAMPLE_DIR/saved/DIAGNOSTICS.json" | cut -d ' ' -f 1)
.venv/bin/python -B tools/recording_reference_workflow.py --run \
  --input-file "$CORE61_EXAMPLE_DIR/INPUT.json" --expected-input-sha256 "$core70_input_sha" \
  --diagnostics-root "$CORE61_EXAMPLE_DIR/saved" --expected-diagnostics-sha256 "$core70_diagnostic_sha" \
  --output-root "$CORE61_EXAMPLE_DIR/reference_report"
```

예제는 exit0,새 모델0·참조1step이며 helper compile1회/선택 정의2개·limiter1회·
fault1회·clip2회다. 전체 Controller나 원래 helper 모듈을 실행하지 않는다.
참조/helper·양자화·검증 작업은 비영이다. 위 직접 SHA 계산은 사용법이며 원래
출처 인증은 아니다. 전달받은 expected SHA는 신뢰할 경로로 확보해야 한다.

완료 후 reference_report에는 정확히 다음 세 파일이 생긴다.

- REFERENCE_AUDIT.json: CORE69의 완전한 canonical JSON 그대로. 모든 행·차이·관찰 identity.
- SUMMARY_KO.md: 저장 진단/참조 진단/대조 판정,과거·신규 작업량,두 source SHA와 차이 요약.
- SHA256SUMS.txt: 위 두 파일의 정렬된 체크섬.

```bash
(cd "$CORE61_EXAMPLE_DIR/reference_report" && sha256sum -c SHA256SUMS.txt)
cat "$CORE61_EXAMPLE_DIR/reference_report/SUMMARY_KO.md"
```

stdout은 세 파일의 SHA·크기를 포함한 canonical 저장 영수증이다. receipt 계약은
CORE70_REFERENCE_AUDIT_WORKFLOW_V1이다. 목적지 경로나 시각을 넣지 않으므로 같은
입력/source/runtime으로 다른 새 목적지에 명시 실행하면 세 파일과 영수증 bytes가
같다. 이때 참조 작업은 매 실행 새로 수행된다. 전체 테스트2회 재현성은 아니다.

## 판정 읽기

exit0은 **참조 대조 일치와 저장 완료**다. 저장 진단과 참조 진단 자체가 DIFFERENT여도
그 DIFFERENT가 그대로 재현되면 대조는 일치할 수 있다. 이를 모두 성공한 진단으로
해석하지 않는다. exit1은 유효한 참조 대조 차이를 저장한 경우다. exit2는 입력/
무결성/사용법/운영/출력 오류이며 성공 영수증이 아니다.

요약은 모든 header 차이와 저장/참조 진단의 차이 전이 index를 보인다. 대조가 다른
전이는 처음20개를 양쪽 entry/next/saved 정수 상태·다른 필드명과 함께 보이며 전체/
표시/생략 개수를 구분한다. 없는 행은 행 없음으로 표시한다. 모든 행은 JSON에 남는다.
상태는 정수 명령 단위다. 물리 torque·실제 sample 시간·10ms 주기의 뜻이 아니다.

## 저장·실패 경계

두 SHA 문법→새 외부 목적지 사전검사→CORE69 단일 캡처/전체 admission/worker→
전체 JSON·요약·영수증 직렬화/크기 검사→exclusive 쓰기/전체 readback 순서다.
기존 목적지·없는 부모·symlink·checkout 내부는 참조 작업 전에 거절한다.
원본 diagnostics-root 내부의 출력 경로도 거절한다. 그 안에 새 폴더를 만들면
원본의 정확한 두 파일 구조가 깨지므로 sibling 외부 폴더를 사용한다.
일반적인 `..` 경로도 양쪽을 resolve해 같은 중첩 관계로 검사한다. 악의적인 경로
교체에 대한 atomic 보호를 뜻하지 않는다.
입력/저장 진단을 복사하거나 기존 bytes를 덮어쓰지 않는다. JSON은2097152bytes,
요약은65536UTF8bytes,영수증은16384bytes 이하이며 잘라서 성공시키지 않는다.

directory0700/files0600을 요청하고 기존 publisher를 그대로 재사용한다. 늦은 저장/
readback 실패에는 일부 폴더·파일이 남을 수 있다. stdout 실패에는 완전 파일이나
출력 prefix가 남을 수 있어도 exit2다. 자동 삭제·repair·재시도·참조 재실행은 없다.
fsync/전원 장애 내구성·atomic transaction·hostile host/race 보장은 아니다.
CLI는 각각1회의 명시 flag만 받으며 축약/중복/r/dt/context override를 거절한다.
도움말·잘못된 사용법은 project import 전 처리하고 path/bytecode 설정을 복원한다.

새 wrapper/formatter/CLI의 hash를 기존 CORE69 reference_identity 목록에 추가하지
않는다. 그 목록은 CORE69가 명시한 source bytes 관찰이며 전체 dependency/build나
서명 인증이 아니다. 새 결과의 SHA도 무결성 확인이지 출처 인증이 아니다.
입력 admission 공유,선언 state feed,첫 anchor/prehistory·전체 trace/숫자 영역의
미검증 범위는 그대로다. HTML/browser 시각 검사나 새 untrusted JSON reader는 없다.

R_BUDGET=UNRESOLVED,Static Gate=FAIL,실제 r/T2/scale=null,
SOURCE_SCHEMA_UNQUALIFIED6000,Candidate/Runtime NO_GO,D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED,NATIVE_EXACT_REPLAY NOT_PROVEN,F70UH/F70V/F71·실차 활성화
NOT_ALLOWED 유지. 실제 Controller/Runtime/CAN/F61/차량 input·capture/actual r·dt/
install/deploy0. 전체 unit/gate의 합성 모델·reference·숫자 작업은 비영·미집계다.
