"""Real IPC -> separate unchanged web CLI -> HTTP/Chromium, synthetic only."""

import argparse
import hashlib
import http.client
import importlib
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from openpilot.system.cyberpilot_web.server import init_token  # noqa: E402
from tools.cyberpilot_web_native.fixtures import SyntheticPublisher  # noqa: E402
from tools.cyberpilot_web_native.isolation import TOPICS, namespace, validate_namespace  # noqa: E402
from tools.cyberpilot_web_native.prepare import check_gitlinks, check_output_path, source_hashes  # noqa: E402


def validate_build(prepared):
  receipt = json.loads((prepared / 'BUILD_RECEIPT.json').read_text())
  profile = check_gitlinks(ROOT)
  for name, expected in profile.items():
    entry = receipt['dependencies'][name]
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=prepared / name, text=True).strip()
    if actual != expected['commit'] or entry['commit'] != actual or source_hashes(prepared / name) != entry['tracked_source_sha256']:
      raise ValueError('native_dependency_drift')
  if hashlib.sha256((prepared / 'msgq/msgq/ipc_pyx.so').read_bytes()).hexdigest() != receipt['binary_sha256']:
    raise ValueError('native_binary_drift')
  return receipt


def exercise_case(browser, output, width, height, prepared):
  checks = []
  with namespace() as run, tempfile.TemporaryDirectory(prefix='cyberpilot-native-private-') as directory:
    private = Path(directory)
    token_path = private / 'token'
    token = init_token(token_path)
    validate_namespace(run)
    ipc = importlib.import_module('msgq.ipc_pyx')
    opendbc = importlib.import_module('opendbc')
    assert ipc.__file__ is not None and opendbc.__file__ is not None
    assert Path(ipc.__file__).resolve() == (prepared / 'msgq/msgq/ipc_pyx.so').resolve()
    assert Path(opendbc.__file__).resolve() == (prepared / 'opendbc/opendbc/__init__.py').resolve()
    publisher = SyntheticPublisher(run)
    settings = {'car_valid': True, 'pause_car': False}
    lock = threading.Lock()
    stop = threading.Event()
    errors = []

    def publish():
      try:
        while not stop.is_set():
          with lock:
            state = settings.copy()
          for topic in TOPICS:
            if topic == 'carState' and state['pause_car']:
              continue
            publisher.publish(topic, valid=state['car_valid'] if topic == 'carState' else True)
          stop.wait(0.1)
      except Exception as error:
        errors.append(type(error).__name__)

    process = subprocess.Popen([sys.executable, '-B', '-m', 'openpilot.system.cyberpilot_web', 'serve',
                                '--source', 'openpilot', '--port', '0', '--token-file', str(token_path)],
                               cwd=ROOT, env=os.environ.copy(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    worker = threading.Thread(target=publish, daemon=True)
    context = None
    try:
      lines = queue.Queue()
      stream = process.stdout
      assert stream is not None
      threading.Thread(target=lambda: lines.put(stream.readline()), daemon=True).start()
      line = lines.get(timeout=12)
      assert 'source=openpilot' in line, 'web process did not start'
      port = int(line.split('127.0.0.1:')[1].split('/')[0])
      worker.start()
      from playwright.sync_api import expect
      context = browser.new_context(viewport={'width': width, 'height': height}, device_scale_factor=1)
      page = context.new_page()
      page_errors = []
      page.on('pageerror', lambda error: page_errors.append(str(error)))
      page.goto(f'http://127.0.0.1:{port}/')
      page.locator('#token').fill(token)
      page.locator('#login button').click()
      expect(page.locator('#active')).to_have_text('활성', timeout=12000)
      expect(page.locator('#can')).to_have_text('연결됨')
      expect(page.locator('#temperature')).to_have_text('42.5 °C')
      assert '합성 native' in page.locator('#alert').inner_text()
      assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
      page.screenshot(path=str(output / f'native-synthetic-{width}.png'), full_page=True)
      checks.append('native-ipc-separate-cli-auth-ui')
      connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
      connection.request('GET', '/api/status', headers={'Authorization': 'Bearer ' + token})
      response = connection.getresponse()
      data = json.loads(response.read())
      connection.close()
      assert response.status == 200 and data['collector_error'] is None
      assert data['topics']['managerState']['data']['processes'][0]['name'] == 'synthetic-worker'
      assert data['topics']['carState']['source_time_ns'].isdecimal()
      checks.append('actual-native-http-fields-and-timestamp')
      with lock:
        settings['car_valid'] = False
      expect(page.locator('#car-status')).to_contain_text('유효하지 않은 메시지', timeout=7000)
      assert page.locator('#can').inner_text() == '—'
      assert page.locator('#active').inner_text() == '활성'
      checks.append('native-invalid-frame-hides-values')
      with lock:
        settings['car_valid'] = True
      expect(page.locator('#can')).to_have_text('연결됨', timeout=7000)
      with lock:
        settings['pause_car'] = True
      expect(page.locator('#car-status')).to_contain_text('오래된 메시지', timeout=9000)
      assert page.locator('#can').inner_text() == '—'
      assert page.locator('#active').inner_text() == '활성'
      assert page.locator('#temperature').inner_text() == '42.5 °C'
      page.screenshot(path=str(output / f'native-topic-outage-{width}.png'), full_page=True)
      checks.append('native-topic-stop-independent-freshness')
      with lock:
        settings['pause_car'] = False
      expect(page.locator('#can')).to_have_text('연결됨', timeout=7000)
      checks.append('native-topic-recovery')
      stop.set()
      worker.join(timeout=3)
      expect(page.locator('#selfdrive-status')).to_contain_text('오래된 메시지', timeout=9000)
      assert page.locator('#active').inner_text() == '—'
      assert page.locator('#connection').inner_text() == '서버 연결됨'
      page.screenshot(path=str(output / f'native-source-stopped-{width}.png'), full_page=True)
      checks.append('source-outage-distinct-from-web-connection')
      assert not page_errors and not errors, (page_errors, errors)
      return checks
    finally:
      if context:
        context.close()
      stop.set()
      if worker.ident is not None:
        worker.join(timeout=3)
      if worker.is_alive():
        raise RuntimeError('publisher_did_not_stop')
      process.terminate()
      try:
        stdout, stderr = process.communicate(timeout=8)
      except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate(timeout=3)
      publisher.close()
      assert token not in stdout + stderr


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--prepared', type=Path, required=True)
  parser.add_argument('--output', type=Path, required=True)
  args = parser.parse_args()
  check_output_path(ROOT, args.output).mkdir()
  receipt = validate_build(args.prepared)
  from playwright.sync_api import sync_playwright
  results = []
  with sync_playwright() as playwright:
    executable = os.getenv('CYBERPILOT_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome')
    browser = playwright.chromium.launch(executable_path=executable, args=['--no-sandbox'])
    version = browser.version
    try:
      for width, height in ((1440, 1250), (390, 844)):
        results.append({'viewport': [width, height], 'checks': exercise_case(browser, args.output, width, height, args.prepared)})
    finally:
      browser.close()
  result = {'status': 'PASS', 'scope': 'SYNTHETIC_HOST_NATIVE_TELEMETRY_NOT_DEVICE', 'cases': results,
            'browser_version': version, 'binary_sha256': receipt['binary_sha256'], 'vehicle_input_count': 0,
            'controller_execution': 0, 'f61_execution': 0, 'actual_rate_calculation': 0, 'native_status_publishing': 'NONZERO_SYNTHETIC_ONLY'}
  (args.output / 'NATIVE_WEB_RESULTS.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
  print('Host-native telemetry web PASS: 2 browser cases, 12 checks, 6 captures; synthetic only.')


if __name__ == '__main__':
  main()
