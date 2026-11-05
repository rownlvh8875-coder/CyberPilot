# R68 — 고정된 개발판을 한 명령으로 클라우드 복구

노트북 파일이나 채팅 별첨 helper 없이 기존 private HF의 DEV와 R67 도구·합성 저장
예제를 새 폴더에 복구합니다. HF는 읽기 전용입니다. 업로드·공개 전환·차량 설치는 없습니다.
복구에는 R41 합성 모델/참조 실행이 포함되며, 브라우저 검사를 다시 하는 명령은 아닙니다.

## 전제와 도구 revision 구분

`cloud_start.py`가 포함된 검증된 R68 Git checkout에서 실행합니다. 아래 profile의
source commit은 보관된 R67 source identity이지, 새 R68 도구 commit이 아닙니다.
그 source commit만 checkout하면 이 새 명령은 없습니다. 실제 실행한 도구 revision은
`git rev-parse HEAD`로 별도 기록하고, archive pins를 main/latest로 바꾸지 마세요.

Linux Git·uv0.12.23·미리 준비된 Python3.12.13과 별도 HF SDK2.4.0이 필요합니다.
SDK interpreter는 기존 venv 경로를 그대로 지정하며 symlink를 base Python으로 바꾸지 않습니다.
Git root에는 고정 source commit의 object가 있어야 합니다. shallow clone에서 없으면
신뢰하는 origin에서 정확한 아래 commit을 먼저 fetch하세요. 도구가 자동으로 clone/
checkout/fetch/login하거나 기존 branch를 바꾸지 않습니다.

HF_TOKEN은 기존 secret binding으로만 사용합니다. token을 명령 인자·문서·로그에 넣지 않습니다.
기존 proxy/CA/TLS/auth를 유지합니다. DEV 의존성은 새 출력 폴더의 locked venv에만
sync하며 전역 설치·기존 환경 덮어쓰기·암묵적 Python 다운로드는 하지 않습니다.

## 먼저 profile 확인

이 명령은 SDK·인증·네트워크·Git 조회 없이 실행됩니다.

```bash
python -B tools/cyberlateral_cloud/cloud_start.py profile
```

R67_MAIN_V1 profile:

- Source: `f562377abefdc5796f54b4f98c0c3ded9a5a4a3e`
- Source tree: `6b42352b0ee2a2a5259837a4df779d47c7b7c54a`
- Private Dataset: `jjuinho/cyberpilot-evidence`
- DEV SHA: `adeaf66e4212ffa350c5b851c684153eac0f5953716f9e9449afd22d5c031c22`
- DEV revision: `5916191894529c579451b21c7f3f18b9f5eee2ed`
- Tools SHA: `c7ca0b6fd9ed46cd31d3456b39536b35203799070dfee0e89ed485eb7004723d`
- Tools revision: `9d41b3cccacc25fa7c4843b1a1a44f23a33ed16e`

사용자 profile 파일·환경 변수·latest override는 제공하지 않습니다. source와 role별
SHA/revision을 서로 바꾸거나 임의 archive를 DEV API로 변환하지 않습니다.
이전 [R64 고정 복구 안내](RECOVERY_R64_KO.md)의 pins는 원래대로 보존합니다.

## 실행

아래 HF-SDK 경로는 자신의 **기존 SDK interpreter**로 바꾸고, 출력 부모가 존재하며
NEW-cloud-start 경로는 아직 없어야 합니다. 두 경로 모두 실제 absolute 경로를 사용합니다.

```bash
/workspace/HF-SDK/bin/python -B tools/cyberlateral_cloud/cloud_start.py run \
  --hf-python /workspace/HF-SDK/bin/python \
  --output /workspace/NEW-cloud-start
```

기본 Git root는 이 도구의 checkout입니다. 필요한 경우 `--repo-root`로 같은 고정
source object를 보유한 기존 Git root를 명시할 수 있습니다. 입력 repo 안의 출력,
기존 경로·broken symlink·symlink parent는 거절합니다. 자동 덮어쓰기나 재시작은 없습니다.

순서: 고정 profile/Git/SDK 확인 → 기존 DEV 복구·새 locked 환경·R41 → 고정 tools
다운로드 → Git과 supplementary source 집합/bytes/blob/mode 일치 확인 → saved3묶음
검산 → one/two와 fail/fail 비교·한국어 요약 → 최종 완료 표시.

DEV441 source와 cloud tooling/docs35 source는 서로 다른 범위입니다. SOURCE는 원본
bytes/mode로 복구하고 새 파일로만 기록합니다. DRIVER나 복구한 cloud SOURCE를 실행하지
않습니다. DEV SOURCE는 Git 검산 후 R41에서 실행하며, saved 비교는 실행 중인 신뢰된 Git
도구로 수행합니다. 전체 repo/submodule/native/차량 환경 복구나 모델 실행0을 주장하지 않습니다.

## 완료와 실패

exit0 / `R68_PINNED_CLOUD_START_PASS`와 유효한 **root START_RESULT.json**이 전체 완료입니다.
`START_KO.md`는 DEV 실행 정보, source 복구 기록, 비교 JSON/한국어 요약으로 연결됩니다.
자식 `dev/RESTORE_RESULT.json`이나 `dev/DEV_START.json`만 성공해도 전체 완료는 아닙니다.
pending 파일은 완료 표시가 아닙니다. 최종 JSON은 pending 기록 후 새 이름으로
exclusive hard link를 만들어 게시하며 기존 이름을 덮어쓰지 않습니다. 이는 전체
venv/폴더를 원자적으로 봉인하거나 concurrent writer를 막는 기능은 아닙니다.

오류는 exit2와 안전한 code입니다. 출력 생성 후 오류이면 root FAILURE.json에 stage와
outputs_preserved=true가 남고, 자식 결과/로그/부분 파일은 보존합니다. syntax 오류는
argparse stderr입니다. disk/출력장치 오류 때 부분 파일만 보고 완료라 판단하지 마세요.
자동 repair/fallback/삭제/부분 폴더 재사용은 하지 않으며 새 출력 경로로 원인을 해결한 뒤 재실행합니다.

전체 복구가 성공해도 `comparisons/different.json`은 의도적으로 DIFFERENT입니다.
`comparisons/same_fail.json`은 MATCH이지만 양쪽 원래 화면 기록은 FAIL입니다.
이 둘은 복구 회귀 예제의 기대 결과이며 새 화면·성능·차량 PASS가 아닙니다.

R41은 명시적 synthetic model972/reference972 step입니다. 전체 DEV883/wheel gate를
이 명령이 새로 실행하지는 않습니다. cloud unit/gate의 별도 합성 작업은 NONZERO/미집계입니다.
같은 host의 논리 복구와 pinned bytes/record 일치이지 물리 머신 독립성·원격 발행자 인증은 아닙니다.

## 유지 제한

rate policy나 실제 차량 설정을 입력받거나 결정하지 않습니다. r=0 fallback도 없습니다.
R_BUDGET UNRESOLVED · Static Gate FAIL · 실제 r/T2/scale=null · Candidate/Runtime NO_GO.
F70UH/F70V/F71 및 실차 활성화 NOT_ALLOWED.
