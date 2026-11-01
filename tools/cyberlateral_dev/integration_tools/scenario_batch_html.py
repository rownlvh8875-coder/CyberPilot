"""Escaped static batch index; links point only to generated case paths."""

from html import escape


def render_index(record: dict) -> bytes:
    parts = ['<!doctype html><html lang="ko"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             ('<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; '
              'base-uri \'none\'; form-action \'none\'">'),
             '<title>CyberLateral · 합성 시나리오 일괄 결과</title><style>',
             '*{box-sizing:border-box}body{margin:0;background:#eef2f7;color:#20304a;font:16px/1.7 system-ui,sans-serif}',
             'main{max-width:1000px;margin:auto;padding:20px 12px}header,article,footer{background:white;border:1px solid #d7e0ec;',
             'border-radius:12px;padding:20px;margin-bottom:16px;overflow-wrap:anywhere}h1{font-size:26px}h2{font-size:20px}',
             'dl{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:6px 14px}dt{font-weight:600}dd{margin:0}',
             'a{color:#225ab0}nav{display:flex;flex-wrap:wrap;gap:8px 18px}.state{font-weight:700}',
             '@media(max-width:500px){header,article,footer{padding:16px}dl{display:block}dd{margin-bottom:8px}}</style>',
             '</head><body><main><header><h1>합성 시나리오 일괄 결과</h1>',
             '<p>파일별 상태는 독립적입니다. COMPLETE는 실행·리포트 생성 완료이며 계산의 독립 검증이나 실차 PASS가 아닙니다.</p>',
             (f'<p>전체 {record["input_count"]}개 · 완료 {record["completed"]}개 · 입력 거절 {record["rejected"]}개 · '
              f'합성 모델 호출 {record["total_model_steps"]}회 · 리포트의 새 모델 호출 0회</p>'),
             '<p>호출 index는 순서이며 실제 초·10ms·제어 주기를 뜻하지 않습니다. SYNTHETIC_ONLY는 출처 인증이 아닌 사용자 선언입니다.</p>',
             '<p><strong>R_BUDGET=UNRESOLVED · Static Evidence Gate=FAIL · 실제 r/T2/scale=null · 실차 활성화 금지</strong></p>',
             '<nav><a href="BATCH.json">정확한 일괄 기록 JSON</a><a href="SHA256SUMS.txt">전체 checksum</a>',
             '<a href="PORTABLE_SHA256SUMS.txt">환경 제외 portable checksum</a></nav></header>']
    for row in record['cases']:
        def text(key, r=row):
            return escape(str(r[key]), quote=True)
        parts.extend(['<article><h2>' + text('case_id') + ' · ' + text('input_name') + '</h2>',
                      '<p class="state">' + text('status') + '</p><dl>',
                      '<dt>시나리오 ID</dt><dd>' + text('scenario_id') + '</dd>',
                      '<dt>입력 거절 코드</dt><dd>' + text('rejection_code') + '</dd>',
                      '<dt>모델 호출</dt><dd>' + text('model_steps') + '</dd>',
                      '<dt>소유한 입력 SHA256</dt><dd>' + text('input_sha256') + '</dd></dl><nav>'])
        if row['snapshot'] is not None:
            parts.append('<a href="' + text('snapshot') + '">소유한 원본 입력</a>')
        if row['report'] is not None:
            parts.append('<a href="' + text('report') + '/index.html">개별 그래프·상태 표</a>')
            parts.append('<a href="' + text('data') + '/RESULTS.json">저장된 모델 결과</a>')
        parts.append('</nav></article>')
    parts.append('<footer>checksum은 보존 bytes의 일관성 검산이며 출처 인증·독립 수치 oracle이 아닙니다. '
                 'Controller/Runtime/CAN/F61/실차 실행 없음. Candidate/Runtime=NO_GO · F70UH/F70V/F71 NOT_ALLOWED. '
                 'JavaScript·외부 자산 없음. BATCH.json과 전체 checksum 검산 전에는 불완전 출력일 수 있습니다.</footer></main></body></html>\n')
    return ''.join(parts).encode()
