"""Real browser smoke: host data, mobile layout, source fixtures and disconnect."""

import argparse
import json
import os
import shutil
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from openpilot.system.cyberpilot_web.server import create_server  # noqa: E402
from openpilot.system.cyberpilot_web.telemetry import HostCollector, Store  # noqa: E402


def response_fixture(payload):
  def handler(route):
    route.fulfill(json=payload)
  return handler


def main():
  from playwright.sync_api import expect, sync_playwright
  parser = argparse.ArgumentParser()
  parser.add_argument("--output", type=Path, required=True)
  args = parser.parse_args()
  args.output.mkdir(parents=True, exist_ok=True)
  token = "b" * 43  # explicit isolated test credential, never a deployed token
  store = Store("host")
  HostCollector(store).poll()
  server = create_server("127.0.0.1", 0, token, store, {"branch": "browser-test", "commit": "test-source-only"})
  thread = threading.Thread(target=server.serve_forever, daemon=True)
  thread.start()
  stopped = False
  checks = []
  browser_version = None
  try:
    with sync_playwright() as playwright:
      executable = os.getenv("CYBERPILOT_CHROMIUM") or shutil.which("chromium") or shutil.which("google-chrome")
      browser = playwright.chromium.launch(executable_path=executable, args=["--no-sandbox"])
      browser_version = browser.version
      for width, height in ((1440, 1250), (390, 844)):
        HostCollector(store).poll()
        context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error, errors=errors: errors.append(str(error)))
        page.goto(f"http://127.0.0.1:{server.server_port}/")
        page.locator("#token").fill(token)
        page.locator("#login button").click()
        expect(page.locator("#connection")).to_have_text("서버 연결됨")
        assert page.locator("#can").inner_text() == "—"
        assert "개발 호스트" in page.locator("#source").inner_text()
        assert "실제 관측값" in page.locator("#host-source").inner_text()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        box = page.locator("#logout").bounding_box()
        assert box is not None and box["height"] >= 44
        page.screenshot(path=str(args.output / f"host-{width}.png"), full_page=True)
        checks.append(f"host-login-layout-{width}")
        fixture = store.snapshot()
        fixture["source"] = "openpilot"
        fixture["identity"] = {"branch": "synthetic-browser-fixture", "commit": "not-device-evidence"}
        fixture["topics"]["selfdriveState"] = {"status": "live", "age_s": 0, "source_time_ns": "1", "data": {"active": True, "alert_text_1": "<script>unsafe</script>", "alert_text_2": "합성 표시 검증"}}
        fixture["topics"]["carState"] = {"status": "stale", "age_s": 6, "source_time_ns": "1", "data": None}
        page.route("**/api/status", response_fixture(fixture))
        expect(page.locator("#active")).to_have_text("활성")
        assert page.locator("#can").inner_text() == "—"
        assert "오래된 메시지" in page.locator("#car-status").inner_text()
        assert "<script>unsafe</script>" in page.locator("#alert").inner_text()
        assert page.locator("#alert script").count() == 0
        page.screenshot(path=str(args.output / f"synthetic-{width}.png"), full_page=True)
        checks.append(f"synthetic-stale-safe-text-{width}")
        page.unroute("**/api/status")
        if width == 390:
          server.shutdown()
          server.server_close()
          thread.join(timeout=2)
          stopped = True
          expect(page.locator("#connection")).to_have_text("연결 끊김", timeout=12000)
          assert page.locator("#active").inner_text() == "—"
          assert page.locator("#memory").inner_text() == "—"
          page.screenshot(path=str(args.output / "disconnected-390.png"), full_page=True)
          checks.append("actual-server-disconnect-clears-values")
        page.locator("#logout").click()
        assert page.locator("#login").is_visible()
        assert page.evaluate("sessionStorage.getItem('cyberpilot-token')") is None
        assert not errors, errors
        context.close()
      browser.close()
    (args.output / "browser-results.json").write_text(json.dumps({"status": "PASS", "checks": checks, "vehicle_execution": 0, "browser_version": browser_version}, ensure_ascii=False, indent=2) + "\n")
    print(f"Browser PASS: {len(checks)} checks; 5 screenshots")
  finally:
    if not stopped:
      server.shutdown()
      server.server_close()
      thread.join(timeout=2)


if __name__ == "__main__":
  main()
