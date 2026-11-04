"""Literal test observations, not an actual browser run or runtime attestation."""


def result_fixture():
    rows = []
    for profile in ['sign', 'resumed']:
        for width in [320, 360, 390, 425, 1440]:
            rows.append({'profile': profile, 'width': width, 'failures': [],
                         'metrics': {'document_width': width, 'pan': 0, 'visible_chart_count': 2,
                                     'min_chart_font': 14, 'table_user_scrolled': width != 1440,
                                     'table_position': 500 if width != 1440 else 0}})
    captures = {f'{p}-{w}-{s}.png': 'a' * 64 for p in ['sign', 'resumed']
                for w in [390, 1440] for s in ['top', 'charts', 'footer']}
    return {'status': 'R60_BROWSER_SMOKE_PASS', 'cases': rows, 'failures': [],
            'browser_version': '154.0.8037.57', 'playwright_version': '1.62.0',
            'actual_local_link_navigations': [{'profile': p, 'target': t}
                                             for p in ['sign', 'resumed'] for t in ['VIEW.json', 'SHA256SUMS.txt']],
            'captures': captures, 'source_selected_files_unchanged': True,
            'fixture_runtime_attestation': False, 'model_F61_r_dt_native_vehicle_executions': 0}


def file_fixture():
    files = {'captures/' + name: digest for name, digest in result_fixture()['captures'].items()}
    files.update({'reports/' + p + '/' + n: 'b' * 64 for p in ['sign', 'resumed']
                  for n in ['index.html', 'VIEW.json', 'SHA256SUMS.txt']})
    return files
