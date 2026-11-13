# 콤마4 장치 정보 확인 도구

CyberPilot을 아직 설치하지 않은 기기에서도 실행할 수 있는 읽기 전용 도구다.
Python 기본 기능만 사용하며 Cereal/native 패키지·uv·CyberPilot 설치가 필요 없다.
Python3.8 이상 문법을 사용하는 Linux용 도구이며 현재 검증은 Python3.12.13에서 수행했다.
실제 장치의 Python 호환성은 별도로 확인해야 한다. 소프트웨어 설치·빌드·Controller·CAN·차량 로그 수집은 하지 않는다.

현재 대상은 콤마4 / 더 뉴 싼타페 TM 2021 디젤이다. 이 도구는 기기 공개 정보만
관찰하며 차량 모델·펌웨어·하네스·조향 한계·r/T2/scale을 판정하지 않는다.

## 실행

전달된 ZIP을 별도 폴더에 풀고 기기에서 다음을 실행한다.

```bash
python3 -S -B device_probe.py
```

표준 출력으로 JSON만 내보낸다. 필요할 때 기존에 설치된 오픈파일럿/당근 소스의
정확한 root를 직접 지정할 수 있다. 현재 CyberPilot이 설치되어 있어야 하는 것은 아니다.
root를 모르면 이 옵션 없이 실행해도 장치 관찰은 가능하다.

```bash
python3 -S -B device_probe.py --source-root /data/openpilot
```

`/data/openpilot`은 예시다. 실제 경로가 맞는 경우에만 지정한다. root의 하위 폴더나
상위 저장소의 Git 정보를 빌려오지 않는다. 소스가 dirty인지/빌드와 같은지/실제 배포본인지
판정하지 않으며 Git HEAD·브랜치 metadata만 기록한다. 원격 주소나 Git 설정은 수집하지 않는다. 하위 Git 명령의 trace 출력을 끄므로
상속된 trace 환경이나 global/system Trace2 설정으로 로그 파일이 생성되지 않게 한다.
기존 Git 설정 파일과 인증·proxy 설정은 수정하지 않는다.
필요하면 셸에서 표준 출력을 새 JSON 파일로 저장한다. 도구 자체는 파일을 쓰지 않는다.

## 읽는 범위

- `/sys/firmware/devicetree/base/model`: 수용 한도4096 bytes, NUL 제거 후 모델 문자열.
- `/VERSION`: 수용 한도4096 bytes의 공개 OS 버전 파일. 원본 bytes SHA도 함께 기록.
- `/AGNOS`: 존재·파일 종류 metadata만 관찰하며 내용을 읽지 않는다.
- OS·아키텍처·Python 버전, 선택한 소스 root의 Git metadata.

초과 감지를 위해 프로세스 read 호출로 최대4097 bytes를 받으며, 한도를 넘으면 값과 전체 SHA를 반환하지 않는다.
읽지 못한 값은 MISSING/EMPTY/UNREADABLE/TOO_LARGE와 null로 표시한다.
마지막 파일 symlink·FIFO·디렉터리는 읽지 않는다. 환경 변수 전체, Params,
VIN·serial·인증 정보·raw 로그는 수집하지 않는다. 네트워크 서비스나 차량 프로세스를 시작하지 않는다.

모델에서 device code를 얻는 규칙은 봉인한 소스의 get_device_type에 따른다.
`mici`이면 comma four 힌트를 표시하지만 실제 장치 인증이나 설치 적합성 승인이 아니다.
출력의 source authority는 규칙을 가져온 저장소 소스이며 기기에서 그 파일이
실행 중이거나 CyberPilot이 배포되어 있다는 증명이 아니다.

시뮬레이션 filesystem 테스트는 FILESYSTEM_FIXTURE로 명시한다. SYSTEM_ROOT는
프로그램이 실제 실행된 호스트의 공개 경로를 읽었다는 뜻으로, 그 호스트가
콤마4라는 보증은 아니다. 어느 경우에도 device_installation_qualified와
actual_activation_allowed는 false다. 별도 빌드·시작·업데이트·복구·폰·차량 검증이 필요하다.

클라우드 실행에서는 콤마 장치 경로가 없을 수 있다. 이를 장치 근거로 바꾸지 않는다.
현재 클라우드에는 실제 콤마4 접근 경로가 연결되어 있지 않다.

## 클라우드에서 ZIP 재현

저장소 root에서 새 외부 경로를 지정한다.

```bash
python3 tools/cyberpilot_web_native/device_probe_bundle.py --output /tmp/device-probe-new.zip
```

ZIP은 probe·이 안내문·모델 규칙 출처·Manifest의4파일이며 설치 이미지가 아니다.
각 파일 SHA와 ZIP SHA를 확인한 뒤 사용한다. 외부 native build SDK나 기존 개발 환경은 바꾸지 않는다.
R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제 r/T2/vehicle scale=null과 실차 활성화 금지는 유지된다.

`--release-dir /tmp/device-probe-release-new`를 사용하면 ZIP·호스트 관찰 JSON·
체크섬·Manifest를 새 외부 폴더로 내보낸다. HOST_OBSERVATION.json은 도구가
실행된 클라우드/CI 호스트의 값이며 실제 콤마의 값으로 해석하지 않는다.
