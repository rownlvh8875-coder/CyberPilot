# CORE3 — 명시적 합성 요청 snapshot과 pair

`integration_tools.request_snapshot`은 공급받은 counterfactual 요청 bytes·flag·context를
보존하고, 인접한 두 snapshot의 일관성을 검사하는 순수 DEV 경계다. 실제 source를
관측하는 코드, UGY 기록 reader, V4 bridge, 모델/F61 계산기, public wheel API가 아니다.

## 사용과 의미

```python
from integration_tools.request_snapshot import (
    SyntheticRequestContextV1, SyntheticRequestSnapshotV1, prepare_request_pair,
)

context = SyntheticRequestContextV1(
    schema_version=1,
    scope='COUNTERFACTUAL_REQUEST_SNAPSHOT_ONLY',
    source_profile='CORE3_COUNTERFACTUAL_REQUEST_SOURCE_V1',
    capture_epoch_id='fixture-capture',
    controller_instance_id='fixture-controller',
    configuration_epoch_id='fixture-config',
    clock_domain='DECLARED_LIVE_MONOTONIC_NS',
    control_mode='DECLARED_TORQUE_CONTROL',
    request_stage='REQUESTED_NORMALIZED_BEFORE_INTEGER_LIMITER',
    reset_generation=0,
    loss_generation=0,
)
previous = SyntheticRequestSnapshotV1(
    context, 0, 1_000_000_000, bytes.fromhex('be800000'), True, False, False,
)
current = SyntheticRequestSnapshotV1(
    context, 1, 1_010_000_000, bytes.fromhex('3f000000'), True, False, False,
)
pair = prepare_request_pair(previous, current)
```

이는 새로 작성한 합성 fixture다. source_profile은 production commit·coherent STEP7
snapshot·실제 build/deployment identity를 나타내지 않는다. `DECLARED_` clock/mode도
호출자 선언이며 실제 clock·차량 control mode의 인증이 아니다. 실제 자료를 synthetic
으로 재라벨링해서 사용하면 안 된다. label만으로 진위를 검증할 수 없다.

Context11개와 snapshot7개 입력은 모두 필수다. active/override/reset을 기본 False로
채우지 않는다. 입력 생성자는 immutable carrier일 뿐 값 검증을 주장하지 않는다.
factory와 `PreparedSyntheticRequestPairV1` 직접 생성자는 같은 검사를 실행한다.
검증 실패는 `RequestSnapshotError.code`로만 반환하며 부분 결과나 입력값을 출력하지 않는다.

## 검사·보존 범위

- exact built-in type만 허용하며 bool→int, float→int, subclass coercion을 하지 않는다.
- raw request는 MSB-first binary32 word의 immutable bytes4개다. finite [-1,1] 범위만
  bit 검사하며 native float를 만들지 않는다. signed zero·subnormal bytes를 보존한다.
- sequence와 두 generation은 uint64, timestamp는 signed int64다. ID3개는 ASCII
  `[A-Za-z0-9_-]{1,64}`다. 이 상한은 새 합성 문법이지 production 전체 domain 주장이 아니다.
- pair의 source/profile/mode/stage/clock/capture/controller/configuration/reset/loss
  context가 모두 같아야 하며 sequence는 wrap 없이 인접해야 한다.
- 시각은 current>previous 비교만 한다. dt/seconds/주기나 r을 계산하지 않는다.
  1ns/10ms/17ms도 order-only 수용 가능하며 V4 exact-seconds 검증을 통과한 것은 아니다.
- current.reset_since_previous=true는 같은 generation이라도 거절한다.
  previous.reset_since_previous=true는 이 pair보다 이전 구간을 설명하므로 허용한다.
  generation 변화는 별도로 context 불일치로 거절한다. no-reset을 추정하지 않는다.
- inactive/override flag는 그대로 보존한다. feasibility·명령 생성·활성화 판정을 하지 않는다.

반환 pair는 같은 immutable snapshot을 참조한다. mutable bytes buffer나 외부 source
getter를 받아들이지 않는다. 다만 이는 실제 Controller에서 추가 reread 없이 소비값을
확보했다는 증명이 아니다. source capture/atomicity/단일 read/noninterference·지연·
손실·지속적인 replay는 구현·측정하지 않았다. cooperative Python 경계이며
`object.__setattr__` 같은 악의적 bypass·동시 변경을 막는 보안 sandbox가 아니다.

고정 출력 claim/permission은 constructor 인자로 덮어쓸 수 없다.
`source_identity_reauthenticated`, `v4_payload_allowed`, `f61_input_allowed`,
`actual_activation_allowed`는 항상 false다. `contract_id`는
`CORE3_COUNTERFACTUAL_REQUEST_PAIR_V1`이고 V4/F61 계약 ID와 다르다.

## 아직 연결하지 않은 항목

이전 제한 출력·angle counter·실제 소비 설정은 요청 snapshot과 다른 역할이다.
이번 요청-only carrier에는 넣지 않았다. 이를 이전 요청값으로 대체하거나 raw word를
integer STEER_MAX로 역산하지 않는다. 다음 state/settings 경계는 별도 명시적 carrier와
source/단위/context 규칙을 설계한 뒤 검증해야 한다.

기존 [CORE2 대응표](F61_OBSERVATION_BINDING_CORE2_KO.md)의 source/flag 미결속은 실제
기록에 관해 그대로 남는다. 이 fixture에 flag를 명시한 것은 기존 UGY 기록에 실제
flag가 있었다는 뜻이 아니다. UGY schema·V4 source pin/API·공개0.3.0 모델은 바꾸지 않는다.

## 검증과 사용 제한

locked venv에서 `python -B -m unittest discover -s project -p test_request_snapshot.py -v`.
전체 DEV gate도 별도로 실행한다. 신규 seam의 모델/native/dt/r/adapter/F61 연산은0이며,
기존 전체 unit/gate에서 수행하는 합성 모델/reference/time 연산은 NONZERO_NOT_AGGREGATED다.

R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제 r/T2/scale=null,
SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO,
D2=PERFORMANCE_NOT_EVALUATED, F19=LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY=NOT_PROVEN, F70UH/F70V/F71·실차 활성화=NOT_ALLOWED.
