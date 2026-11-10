# CORE34 — 운전자 토크·비대칭 invocation 제한의 public API 회귀

이 단계는 기존 모델의 검증 보강이다. runtime 계산식·API·wheel·CORE32/33 참조값을
바꾸지 않으며 새 실행 CLI나 차량 reader를 추가하지 않는다.
[테스트](../project/test_driver_rate_boundaries.py)는4개 unittest method 안의28개
고정 단일 호출 사례다. 28개의 unittest method라고 세지 않는다.

## 입력과 수동 기대값

모든 입력은 합성 요청±1.0,scale16,allowance7,factor1,multiplier3,active=true,
angle0.0이다. 이전 상태는 index1/previous_requested0/angle_counter0과 명시한
previous_applied를 선언한 seed다. 실제 연속 호출이나 seed의 도달 가능성·prehistory를
증명하지 않는다. scale16과 각 상수는 합성 fixture이지 차량 설정 authority가 아니다.

운전자10사례는 양쪽 부호의7-1/256,7,7+1/256 경계를 확인한다. cap에 정확히 닿으면
integer tag를 유지하고 바로 안쪽은4093/256,hex0x1.ffa0000000000p+3의 fractional
stage가 된다. 최종 반올림16과 그 전 fractional stage를 구별한다. 반대 부호도 같다.
opposing12.25는±0.25/float stage를 거쳐 integer0이 되고12.5는 integer0으로 clamp한다.
정확한 zero 경계7+16/3은 dyadic 입력이 아니므로 허용된 exact-boundary fixture라고
주장하지 않는다. 기대값은 모델·oracle·quantizer 반환값으로 생성하지 않았다.

기본 UP2/DOWN5의 rate14사례는 다음 각 seed에 요청±1을 각각 적용한다.

| previous_applied | rate lower | rate upper |
|---|---|---|
| -6 | -8 | -1 |
| -4 | -6 | 1 |
| -1 | -3 | 2 |
| 0 | -2 | 2 |
| 1 | -2 | 3 |
| 4 | -1 | 6 |
| 6 | 1 | 8 |

순차 clip2사례에서는 driver clip0 뒤에 이력 interval[1,8]/[-8,-1]이 적용되어 최종±1이
된다. UP/DOWN 모두0인 hold2사례도 driver clip0이 아니라 이전±6을 보존한다.
따라서 최종값이 새 driver interval 안에 항상 있다는 잘못된 불변식을 추가하지 않는다.
이는 기존 모델 순서의 기술이지 safety 권고나 production limiter 동치 증명이 아니다.
UP/DOWN0은 invocation 설정이며 F61 rate_budget_per_s=0 또는 fallback과 무관하다.

정확한 driver/rate lower·upper·result의 kind/value와 limited/final/projected integer,
quantized±16,previous request/applied,next index/counter와 active/fault flag를 확인한다.
전체 output serialization,일반 rounding,모든 domain 조합을 검증하는 oracle는 아니다.

## 실행과 검증 성격

기존 준비된 환경에서 repository root 기준:

```bash
tools/cyberlateral_dev/.venv/bin/python -B -m unittest discover -s tools/cyberlateral_dev/project -p test_driver_rate_boundaries.py
```

기대 literal과 테스트 SHA는 새 사례 실행 전에 AST로 freeze하고 커밋했다. 과거 모델
검토·baseline은 있었으므로 blind evaluation이나 외부 독립기관 승인이 아니다.
기존 정상 코드를 검증하므로 missing-feature RED를 만들었다고 표현하지 않는다.
별도 proof에서 driver부호,endpoint kind,UP/DOWN 교환,cross-zero cap 제거,raw request
rate 입력,최종 driver reclip의6개 in-memory 합성 코드 변형을 각각 탐지하고 정상
모델을 복원한다. 원본 소스 bytes를 수정하지 않는다. 이6개 변형 밖의 결함을 모두
탐지하는 mutation coverage라고 일반화하지 않는다. 진단 log의 시간은 재현 대상이
아니며 mutation 요약·observed JSON만 byte 비교한다.

실제 r/T2/scale=null,R_BUDGET UNRESOLVED,StaticGateFAIL,SOURCE_SCHEMA_UNQUALIFIED6000,
Candidate/Runtime NO_GO,D2 PERFORMANCE_NOT_EVALUATED,F19 LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY NOT_PROVEN,F70UH/V/F71·실차 활성화 NOT_ALLOWED.
실제 inputs/F61/Controller/Runtime/CAN/실제 r/dt0,합성 모델/검증 작업은 비영이다.
