"""Pure Korean reading aid for fresh R60 records, never a new observation/oracle."""

import json
import re
from html import escape

from browser_probe import PROFILES, WIDTHS

MISSING = object()
REASONS = {
    'PAGE_OVERFLOW': '페이지 폭 초과 또는 가로 이동',
    'DPR': '지정 DPR 불일치',
    'FOOTER': 'footer 글자/표시/제한 문구 불일치',
    'CHARTS': '실제로 보이는 그래프 수 불일치',
    'CHART_FONT': '축/범례 글자 크기 또는 표시 불일치',
    'CSP': 'CSP 표시 누락',
    'ACTIVE_ASSETS': '허용하지 않은 활성 요소',
    'TABLE_SCROLL': '사용자 표 스크롤 또는 표시/CSS 불일치',
    'RESUMED_POINT': '재개 단일 점/중앙 index 표시 불일치',
    'INVALID_OBSERVATIONS': '관측값 누락 또는 유효하지 않은 값',
    'UNEXPECTED_BROWSER_REQUEST': '허용 목록 밖 브라우저 요청',
}


def _need(condition):
    if not condition:
        raise ValueError('BROWSER_SUMMARY_INVALID')


def _cell(value):
    if value is MISSING:
        return '미관측'
    # JSON preserves null/bool/numeric kinds and escapes control/bidi characters.
    text = escape(json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False), quote=False)
    return '`' + text.replace('`', '&#96;').replace('|', '&#124;') + '`'


def render_summary(result: dict, file_sha256: dict[str, str]) -> bytes:
    _need(type(result) is dict and type(file_sha256) is dict)
    cases, failures = result.get('cases'), result.get('failures')
    if type(cases) is not list or type(failures) is not list:
        raise ValueError('BROWSER_SUMMARY_INVALID')
    _need(result.get('status') in ('R60_BROWSER_SMOKE_PASS', 'R60_BROWSER_SMOKE_FAIL'))
    _need(len(cases) == len(PROFILES) * len(WIDTHS))
    for row in cases:
        _need(type(row) is dict and type(row.get('width')) is int and type(row.get('metrics')) is dict)
        _need(type(row.get('failures')) is list)
    _need([(r.get('profile'), r['width']) for r in cases] == [(p, w) for p in PROFILES for w in WIDTHS])
    for codes in [*(r['failures'] for r in cases), *(f.get('codes') if type(f) is dict else None for f in failures)]:
        _need(type(codes) is list and all(type(c) is str and re.fullmatch('[A-Z][A-Z0-9_]{0,79}', c) for c in codes))
    _need((result['status'] == 'R60_BROWSER_SMOKE_FAIL') == bool(failures))
    _need(not any(r['failures'] for r in cases) or bool(failures))
    captures = result.get('captures')
    allowed = {f'{p}-{w}-{s}.png' for p in PROFILES for w in (390, 1440) for s in ('top', 'charts', 'footer')}
    if type(captures) is not dict or not set(captures) <= allowed:
        raise ValueError('BROWSER_SUMMARY_INVALID')
    _need(all(type(v) is str and re.fullmatch('[0-9a-f]{64}', v) for v in captures.values()))
    for name, digest in captures.items():
        if 'captures/' + name in file_sha256:
            _need(file_sha256['captures/' + name] == digest)

    parts = ['# 브라우저 관측 요약', '',
             '이 요약만으로 완료를 판정하지 마세요. RESULT.json이 존재하고 SHA256SUMS.txt의 전체 검산이 통과해야 완료입니다.',
             '기록 중 실패한 폴더에는 부분 요약만 남을 수 있습니다. 아래는 저장한 관측이며 새 브라우저/모델 계산이 아닙니다.', '',
             '기록 상태: ' + _cell(result['status']),
             'Browser: ' + _cell(result.get('browser_version', MISSING))
             + ' · Playwright: ' + _cell(result.get('playwright_version', MISSING)),
             f'기록한 case: {len(cases)} · 개별 FAIL: {sum(bool(r["failures"]) for r in cases)} · 전체 실패 기록: {len(failures)}', '',
             '## 화면별 관측', '',
             '| 프로필 / 폭(px) | 기록 판정 | 문서 폭 / 페이지 이동(px) | 보이는 그래프 / 최소 글자(px) | 표 wheel 이동 여부 / 위치(px) | 이유 |',
             '|---|---|---|---|---|---|']
    for row in cases:
        m = row['metrics']
        reason = '; '.join(c + ': ' + REASONS.get(c, '추가 관측 오류') for c in row['failures']) or '없음'
        parts.append(f'| {row["profile"]} / {row["width"]} | {"FAIL" if row["failures"] else "PASS"} | '
                     + _cell(m.get('document_width', MISSING)) + ' / ' + _cell(m.get('pan', MISSING)) + ' | '
                     + _cell(m.get('visible_chart_count', MISSING)) + ' / ' + _cell(m.get('min_chart_font', MISSING)) + ' | '
                     + _cell(m.get('table_user_scrolled', MISSING)) + ' / ' + _cell(m.get('table_position', MISSING)) + ' | ' + reason + ' |')
    parts.extend(['', '표 wheel 요구는 모바일 네 폭에 한정됩니다. 1440px의 false/0은 실패를 새로 계산한 값이 아닙니다.',
                  'null은 저장된 null, 미관측은 해당 field 누락입니다. 둘 다 임의의 0으로 바꾸지 않았습니다.', '',
                  '## 전체 실패 기록', ''])
    for failure in failures:
        parts.append('- ' + _cell(failure))
        if failure['codes']:
            reason = '; '.join(c + ': ' + REASONS.get(c, '추가 관측 오류') for c in failure['codes'])
            parts.append('  - 설명: ' + reason)
    if not failures:
        parts.append('기록 없음. 개별 case와 원래 RESULT를 함께 확인하세요.')
    parts.extend(['', '## 연결 가능한 리포트·선택 캡처', '',
                  '390/1440px의 top/charts/footer만 캡처 대상입니다. 실제 소유한 파일 목록에 있는 고정 상대 경로만 연결합니다.', ''])
    for profile in PROFILES:
        for name in ('index.html', 'VIEW.json', 'SHA256SUMS.txt'):
            path = f'reports/{profile}/{name}'
            if path in file_sha256:
                parts.append(f'- [{profile} / {name}]({path})')
        for name in sorted(captures):
            path = 'captures/' + name
            if name.startswith(profile + '-') and path in file_sha256:
                parts.append(f'- [{name}]({path})')
    parts.extend(['', '## 범위와 제한', '',
                  '선택 source 전후 불변 기록: ' + _cell(result.get('source_selected_files_unchanged', MISSING)),
                  '새 모델/F61/실제 r·dt/native/차량 실행 기록: ' + _cell(result.get('model_F61_r_dt_native_vehicle_executions', MISSING)),
                  'fixture runtime attestation 기록: ' + _cell(result.get('fixture_runtime_attestation', MISSING)),
                  '일반 CI의 PASS는 이 브라우저 실행을 대신하지 않습니다. 기존 unit/gate의 합성 작업은 별도 NONZERO/미집계입니다.',
                  '이는 한정된 저장 합성 화면 관측입니다. 출처 인증·독립 수치 정답·모든 브라우저/글꼴/접근성/touch 검증이 아닙니다.',
                  'R_BUDGET=UNRESOLVED · Static Gate=FAIL · 실제 r/T2/scale=null · Candidate/Runtime NO_GO.',
                  'F70UH/F70V/F71 및 실차 활성화 NOT_ALLOWED.', ''])
    return '\n'.join(parts).encode('utf-8')
