# F70U-A 정적 context 결정 요청

현재 상태: CONTRACT_SCHEMA_VALID / STATIC_CONTEXT_INSTANCE_UNRESOLVED.
이는 차량 결속 완료, r 예산 승인 또는 Runtime 허가가 아닙니다.

확인된 사용자 설명: Hyundai / 더뉴싼타페 TM / 2021년식 / 2.2 디젤 / Prestige. 지역은 미확인입니다.
기계 판독 요청서는 artifacts/f70u/owner_static_context_decision_request.json입니다.

필요한 것은 기존에 보유한 정적 차량 사양·적용 지역·플랫폼 대응 근거와 버전이 고정된 설정 승인입니다.
정확한 platform, firmware/fingerprint 권위, CAN/SCC/HDA 구성, safety 설정, flags와 제어 모드는 미결정입니다.
생산 신호의 단위·부호·전후 처리 단계·시간 의미를 F61 합성 입력과 연결하는 별도 정적 근거도 필요합니다.
값을 추천하거나 차량별 설정을 차용하지 않았습니다. Template의 null은 승인이 아닙니다.
추가 실차 데이터 수집은 요청하지 않으며 CAN 수집·차량 연결·RLOG 분석도 허용하지 않습니다.
기존 정적 자료만으로 결정할 수 없는 항목은 unresolved로 유지합니다.
데이터 수집 없이 가능한 범위는 schema·provenance·모순 검증입니다. F71은 비허용입니다.
