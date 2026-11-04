"""Explicit real-browser observations; pure classification imports no browser."""

import importlib
import importlib.metadata
import math
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PROFILES = ('sign', 'resumed')
WIDTHS = (320, 360, 390, 425, 1440)
PUBLIC_NAMES = ('index.html', 'VIEW.json', 'SHA256SUMS.txt')
CSP = "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"


def assess_case(profile, width, metrics) -> list[str]:
    """Judge actual observations, including the historical one-pixel overflow."""
    numeric = ('viewport', 'document_width', 'pan', 'dpr', 'footer_font', 'chart_count',
               'visible_chart_count', 'min_chart_font', 'active_assets', 'table_position',
               'single_circles', 'visible_single_circles')
    boolean = ('footer_visible', 'csp', 'chart_labels_visible', 'table_visible',
               'table_user_scrolled', 'single_point_centered')
    if (profile not in PROFILES or width not in WIDTHS
            or any(type(metrics.get(k)) not in (int, float) or not math.isfinite(metrics[k]) for k in numeric)
            or any(type(metrics.get(k)) is not bool for k in boolean)
            or type(metrics.get('table_overflow')) is not str
            or type(metrics.get('footer_text')) is not str or type(metrics.get('single_ticks')) is not list):
        return ['INVALID_OBSERVATIONS']
    checks = {
        'PAGE_OVERFLOW': metrics['viewport'] == width and metrics['document_width'] == width and metrics['pan'] == 0,
        'DPR': metrics['dpr'] == 1,
        'FOOTER': (metrics['footer_font'] == 16 and metrics['footer_visible']
                   and 'SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE' in metrics['footer_text']
                   and 'F70UH/F70V/F71 NOT_ALLOWED' in metrics['footer_text']),
        'CHARTS': metrics['chart_count'] == metrics['visible_chart_count'] == 2,
        'CHART_FONT': metrics['min_chart_font'] >= 14 and metrics['chart_labels_visible'],
        'CSP': metrics['csp'],
        'ACTIVE_ASSETS': metrics['active_assets'] == 0,
        'TABLE_SCROLL': (metrics['table_visible'] and (width == 1440 or
                         (metrics['table_overflow'] in ('auto', 'scroll') and metrics['table_user_scrolled']
                          and metrics['table_position'] > 0))),
        'RESUMED_POINT': profile != 'resumed' or (metrics['single_ticks'] == ['5', '5']
                         and metrics['single_circles'] == metrics['visible_single_circles'] == 5
                         and metrics['single_point_centered']),
    }
    return [code for code, passed in checks.items() if not passed]


@contextmanager
def preview(payloads):
    """Serve immutable owned bytes, never filesystem roots or environment receipts."""
    allowed = {'/' + p + '/' + n for p in PROFILES for n in PUBLIC_NAMES}
    if not payloads or not set(payloads) <= allowed or any(type(raw) is not bytes for raw in payloads.values()):
        raise ValueError('PREVIEW_SCOPE')
    owned = dict(payloads)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            raw = owned.get(self.path)
            if raw is None:
                self.send_error(404)
                return
            self.send_response(200)
            kind = 'text/html' if self.path.endswith('/index.html') else 'text/plain'
            self.send_header('Content-Type', kind + '; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Content-Security-Policy', CSP)
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.1}, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def browser_library():
    """Optional host prerequisite, never installed or silently skipped by us."""
    try:
        module = importlib.import_module('playwright.sync_api')
        return module.sync_playwright, importlib.metadata.version('playwright')
    except (ImportError, importlib.metadata.PackageNotFoundError):
        raise ValueError('PLAYWRIGHT_REQUIRED') from None


METRICS = '''()=>{
    window.scrollTo(1000,0);
    const f=document.querySelector('footer'), table=document.querySelector('.scroll');
    const visible=e=>{
        const r=e.getBoundingClientRect();
        if(r.width<=0 || r.height<=0) return false;
        for(let n=e;n;n=n.parentElement){
            const s=getComputedStyle(n);
            if(s.display==='none' || s.visibility!=='visible' || Number(s.opacity)===0) return false;
        }
        return true;
    };
    const labels=[...document.querySelectorAll('.y-ticks,.x-ticks,.axis-caption,.legend')];
    const fonts=labels.map(e=>parseFloat(getComputedStyle(e).fontSize));
    const charts=[...document.querySelectorAll('.charts svg')];
    const circles=[...document.querySelectorAll('.charts circle')];
    return {viewport:innerWidth, document_width:document.documentElement.scrollWidth, pan:scrollX,
        dpr:devicePixelRatio, footer_font:parseFloat(getComputedStyle(f).fontSize),
        footer_visible:f.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})
            && getComputedStyle(f).overflowX==='visible', footer_text:f.innerText,
        chart_count:charts.length, visible_chart_count:charts.filter(visible).length,
        chart_labels_visible:labels.length>0 && labels.every(visible),
        min_chart_font:fonts.length?Math.min(...fonts):null,
        csp:!!document.querySelector('meta[http-equiv="Content-Security-Policy"]'),
        active_assets:document.querySelectorAll('script,iframe,object,embed,img,form,link,audio,video,source').length,
        table_position:table.scrollLeft, table_overflow:getComputedStyle(table).overflowX,
        table_visible:visible(table),
        single_ticks:[...document.querySelectorAll('.x-ticks.single')].map(e=>e.innerText),
        single_circles:circles.length, visible_single_circles:circles.filter(visible).length,
        single_point_centered:circles.length===5 && circles.every(e=>visible(e) && Number(e.getAttribute('cx'))===375)};
}'''


def run_browser(reports, captures, executable) -> dict:
    launch, library_version = browser_library()
    payloads = {'/' + p + '/' + n: (reports / p / n).read_bytes() for p in PROFILES for n in PUBLIC_NAMES}
    cases, failures, navigations, blocked = [], [], [], []
    captures.mkdir()
    with preview(payloads) as base, launch() as driver:
        browser = driver.chromium.launch(executable_path=str(executable), headless=True)
        try:
            version = browser.version
            for profile in PROFILES:
                for width in WIDTHS:
                    context = browser.new_context(viewport={'width': width, 'height': 1250 if width == 1440 else 844},
                                                  device_scale_factor=1, service_workers='block')
                    try:
                        def route(request):
                            url = request.request.url
                            if url.startswith(base) and '/' + url.removeprefix(base) in payloads:
                                request.continue_()
                            else:
                                blocked.append(url)
                                request.abort()

                        context.route('**/*', route)
                        page = context.new_page()
                        page.set_default_timeout(10_000)
                        page.set_default_navigation_timeout(15_000)
                        page.goto(base + profile + '/index.html', wait_until='load')
                        page.evaluate('document.fonts.ready')
                        table = page.locator('.scroll')
                        if width < 1440 and table.is_visible():
                            table.scroll_into_view_if_needed()
                            table.evaluate('e=>{e.scrollLeft=0}')
                            table.hover()
                            page.mouse.wheel(500, 0)
                            # wait_for_function uses eval and is forbidden by the report CSP.
                            # Observe the wheel condition without relaxing that policy.
                            table.evaluate('''async e=>{
                                const deadline=performance.now()+1000;
                                while(e.scrollLeft===0 && performance.now()<deadline)
                                    await new Promise(resolve=>requestAnimationFrame(resolve));
                            }''')
                        metrics = page.evaluate(METRICS)
                        metrics['table_user_scrolled'] = width < 1440 and metrics['table_position'] > 0
                        codes = assess_case(profile, width, metrics)
                        if codes:
                            failures.append({'profile': profile, 'width': width, 'codes': codes})
                        if width in (390, 1440):
                            for section in ('top', 'charts', 'footer'):
                                if section == 'top':
                                    page.evaluate('window.scrollTo(0,0)')
                                else:
                                    page.locator('.charts' if section == 'charts' else 'footer').scroll_into_view_if_needed()
                                page.screenshot(path=captures / f'{profile}-{width}-{section}.png')
                        if width == 390:
                            for name in ('VIEW.json', 'SHA256SUMS.txt'):
                                page.locator(f'a[href="{name}"]').click()
                                expected_url = base + profile + '/' + name
                                if (page.url != expected_url or page.locator('body').inner_text().strip()
                                        != payloads['/' + profile + '/' + name].decode().strip()):
                                    raise ValueError('LOCAL_LINK_CONTENT')
                                navigations.append({'profile': profile, 'target': name})
                                page.go_back(wait_until='load')
                        cases.append({'profile': profile, 'width': width, 'metrics': metrics, 'failures': codes})
                    finally:
                        context.close()
        finally:
            browser.close()
    if blocked:
        failures.append({'codes': ['UNEXPECTED_BROWSER_REQUEST'], 'count': len(blocked)})
    return {'cases': cases, 'failures': failures, 'browser_version': version, 'playwright_version': library_version,
            'actual_local_link_navigations': navigations, 'blocked_request_count': len(blocked),
            'browser_location': 'EXPLICIT_EXISTING_HOST_PREREQUISITE_NOT_RESTORED_APP',
            'CSS_or_DOM_modified': False}
