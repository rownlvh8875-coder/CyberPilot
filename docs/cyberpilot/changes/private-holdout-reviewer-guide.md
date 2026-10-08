# Private holdout: 사람이 먼저 차선 경계를 찍는 방법

LOCAL PRIVATE ONLY / PIXEL REFERENCE / NO METER OR VEHICLE QUALIFICATION

원래 정해진 60장을 그대로 검토합니다. 검출 결과를 보고 쉬운 사진으로
교체하거나 어려운 사진을 제외하지 마세요. 이 도구는 검출선, confidence,
AI 설명, model/planner/candidate, approximate geometry를 보여주지 않습니다.
같은 holdout의 결과를 미리 봤다면 blind 확인란을 체크하지 마세요.

## 시작

로컬 launcher를 실행하고 안내된127.0.0.1 주소를 브라우저에서 여세요.
서버는 localhost만 사용합니다. 원본 이미지/좌표/경로를 GitHub나 외부에
보내지 마세요. 이름 대신 개인 정보 없는 reviewer ID를 직접 입력합니다.

## 사진마다

1. 원본을 보고 현재 차량이 주행하는 lane의 보이는 좌/우 경계를 판단합니다.
   인접 차선 내부선, 갓길, 합류 유도선을 자동으로 ego 경계로 삼지 않습니다.
   애매하면 EGO_BOUNDARIES_AMBIGUOUS, 교차로/합류면 INTERSECTION_OR_MERGE.
2. 둘 다 명확하면 BOTH_EGO_BOUNDARIES_VISIBLE.
   한쪽만 보이면 LEFT_ONLY_VISIBLE 또는 RIGHT_ONLY_VISIBLE.
   명확한 표시가 없으면 NO_CLEAR_LANE_MARKINGS; 검토 불가능하면 UNREVIEWABLE.
3. Left 또는 Right를 선택해 각 보이는 경계 위에 3–12개 점을 찍습니다.
   화면 아래쪽(가까운 곳)부터 위쪽(먼 곳) 순서입니다. 보이는 범위만 표시하고
   horizon이나 안 보이는 부분까지 강제로 연장하지 마세요.
   가려진 긴 구간을 하나의 선으로 이어 근거를 만들어내지 마세요.
   불확실한 경우 점을 강제하지 말고 ambiguous 상태를 사용합니다.
4. Zoom과 Pan mode를 써서 확인하세요. 저장 좌표는 원본 pixel 좌표입니다.
   Undo last point, Clear left/right로 저장 전 위치를 고칠 수 있습니다.
   한쪽 상태에서는 다른 쪽 점이 없어야 합니다. Ambiguous/교차로/없음/검토불가
   상태에서는 양쪽 점을 비웁니다.
5. Save editable draft는 나중에 고칠 수 있는 초안입니다. 완료 수에는 포함되지
   않습니다. 새로고침해도 초안이 유지됩니다.
6. 원본과 내가 찍은 선만 다시 확인한 뒤, 실제로 detector/AI/model 결과를
   보지 않았다는 확인란을 직접 체크하고 Save immutable first decision을 누릅니다.
   최초 판단은 덮어쓸 수 없습니다. 오류 정정은 별도 correction receipt로
   남겨야 하며 최초 blind 판단을 지우지 않습니다.
7. Next로 다음 사진을 검토합니다. 진행률 N/60, Previous, frame selector,
   Jump to unreviewed를 사용할 수 있습니다.

## 단축키

L / R: 왼쪽/오른쪽 선택
U: 마지막 점 취소
P: Pan mode
← / →: 이전/다음
J: 미검토 사진 이동

입력 필드에 focus가 있으면 키보드 단축키가 적용되지 않습니다.
Shift+drag 또는 오른쪽 버튼 drag도 pan입니다.

## 완료 이후

이 작업에서는 60/60 first decisions가 모두 저장되고 annotation set이
freeze되기 전에는 어떤 사진의 검출 결과도 볼 수 없습니다.60장 완료 후에도
detector inference는 별도 다음 단계이며 현재 comparison gate는 NOT_RUN을
표시합니다. 도구가 사람 대신 라벨이나 검출 결과를 생성하지 않습니다.

두 경계가 보이는 경우에만 공통 관찰 범위에서 pixel midpoint를 정의할 수
있습니다. 한 경계/가정한 차선 폭/모델 경로로 중심선을 채우지 않습니다.
Pixel GT는 meter truth가 아니며 physical calibration과 독립 검증은 여전히
필요합니다. 기존 public 29 assisted review의 독립성도 이 작업으로 바뀌지 않습니다.

콘솔에서 Enter를 누르면 로컬 서버를 종료합니다.

CALIBRATION_MEASUREMENT_PENDING / INDEPENDENT_CALIBRATION_VALIDATION_PENDING
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE / sealed reference NOT_GENERATED
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED
