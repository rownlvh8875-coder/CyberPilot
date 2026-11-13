# CyberPilot 모바일 실시간 상태 웹

개발 호스트의 실제 상태를 폰 브라우저로 확인하는 읽기 전용 웹입니다.
오픈파일럿 환경에서는 deviceState, selfdriveState, carState, managerState만
구독하도록 준비했습니다. 제어·CAN 송신·설정 변경 API는 없습니다.
차량 메시지가 없으면 차량 상태는 `—`입니다. 호스트 값은 서버가 실행되는
컴퓨터의 값이며 콤마의 값이라고 가정하지 않습니다.

## 개발 호스트에서 실행

Python 3.12 이상, Linux 기준입니다. 추가 실행 패키지는 필요 없습니다.
저장소 루트에서 실행하거나 source bundle을 풀어 그 폴더에서 실행합니다.
토큰은 저장소 밖의 전용 비공개 폴더에 생성합니다.

```bash
python3 -m openpilot.system.cyberpilot_web init --token-file "$HOME/.cyberpilot-web/token"
python3 -m openpilot.system.cyberpilot_web serve --token-file "$HOME/.cyberpilot-web/token"
```

같은 컴퓨터에서는 `http://127.0.0.1:8099/`를 엽니다. 토큰 파일 내용을
자신의 브라우저 토큰 칸에 입력합니다. 토큰은 명령 로그·스크린샷·공유 ZIP에
넣지 마세요. 세션 저장소는 해당 탭 범위이며 연결 해제로 삭제합니다.

동일한 신뢰 네트워크의 휴대폰으로 볼 때만 `--host <서버 LAN IP>`를
추가하고 폰에서 `http://<서버 LAN IP>:8099/`에 접속합니다. 클라우드의
127.0.0.1 주소는 휴대폰에서 접근되지 않습니다. 외부 접근은 별도 터널이나
접근 제어가 필요하며 이 도구가 공인 주소를 자동 발급하지 않습니다.
HTTP는 암호화되지 않습니다. 신뢰할 수 없는 네트워크에서는 인증서와 키를
`--tls-cert /private/server.crt --tls-key /private/server.key`로 지정하고 HTTPS를
사용하세요. 외부 포트 공개는 자동 수행하지 않습니다.

## 오픈파일럿 연결

완전히 준비된 오픈파일럿 Python/native 환경에서만 `--source openpilot`을
명시합니다. 구독 라이브러리가 없으면 화면에 소스 연결 불가를 표시합니다.
실제 장치 메시지 구독은 이번 클라우드 검증에서 실행하지 않았습니다.

관리자 자동 시작은 기본 꺼짐입니다. 이후 장치 검증 시 관리자 프로세스에
다음 환경을 명시적으로 전달할 수 있습니다. 이 문서는 설치 승인이 아닙니다.

```text
CYBERPILOT_WEB=1
CYBERPILOT_WEB_TOKEN_FILE=/private/absolute/path/token
CYBERPILOT_WEB_HOST=127.0.0.1
CYBERPILOT_WEB_PORT=8099
# 선택: CYBERPILOT_WEB_TLS_CERT / CYBERPILOT_WEB_TLS_KEY
```

LAN에서 볼 경우 검증된 인터페이스 IP를 HOST로 지정해야 합니다. 토큰 폴더는
소유자 전용 0700, 파일은 0600 권한이어야 합니다. 파일 내용 변경 후 서버를
재시작하면 이전 토큰은 무효가 됩니다. 환경 설정을 제거하면 관리자 등록이
꺼집니다. 저장소나 launch 스크립트에 토큰을 하드코딩하지 마세요.

## 표시 계약

1초 polling / 수신 후 5초 freshness는 화면 정책입니다. 제어 주기·실제 dt·r
정책이 아닙니다. 각 topic의 최신성은 따로 판단하고 유효하지 않거나 오래된
데이터는 숨깁니다. 소스 타임스탬프는 JSON 문자열로 보존하며 실제 apply 시각으로
주장하지 않습니다. 연결이 끊기면 브라우저도 이전 값을 숨깁니다.
소스가 재시작되어 시각이 역행하는 경우 서버를 재시작하여 구독 세대를 바꾸세요.

버전은 서버 시작 시 소스 체크아웃의 브랜치/커밋입니다. Git 없는 source bundle은
버전을 미확인으로 표시합니다. 배포 빌드·실제 실행 이미지의 증명은 아닙니다.

## 검증과 배포 묶음

```bash
uv sync --locked --project tools/cyberpilot_web
uv run --locked --project tools/cyberpilot_web python tools/cyberpilot_web/verify.py --output /tmp/web-verification-new
python3 tools/cyberpilot_web/distribute.py --output /tmp/cyberpilot-web-source-new.zip
python3 -m openpilot.system.cyberpilot_web readiness
```

검증 출력 폴더와 ZIP은 새 경로를 사용합니다. readiness는 정적 경로 존재 여부만
검사하며 실제 설치 적합성은 항상 미검증으로 반환합니다(exit 2). bundle은
읽기 전용 상태 웹의 소스 묶음이고 콤마용 OS/차량 설치 이미지가 아닙니다.

## 최종 장치 검증까지 남은 일

- 1차 대상은 콤마4 / 더 뉴 싼타페 TM 2021년식 디젤로 지정됨. 실제 장치 식별·연결은 미검증.
  [대상과 소스 근거](CYBERPILOT_TARGET_PROFILE_KO.md)를 참조.
- native 의존성/submodule 전체 빌드, 기기 시작·업데이트·복구 검증.
- 실제 기기의 상태 구독, 휴대폰 인증·네트워크·연결 끊김 검증.
- 제어 Adapter의 실제 입력 결속, 별도 rate 정책과 static 차량 근거 해결.
- 위 조건 충족 후에만 설치용 브랜치/URL과 실제 차량 적용 범위 확정.

현재는 R_BUDGET=UNRESOLVED, Static Evidence Gate=FAIL, 실제 r/T2/vehicle scale=null,
실차 제어 활성화 금지를 유지합니다. 웹 화면 PASS는 이 조건을 변경하지 않습니다.
