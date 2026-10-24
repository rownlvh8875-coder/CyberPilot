# Cyber H1 visual inspector implementation plan

> Use executing-plans natively, TDD, then independent review.

Goal: expose exactly the existing 800-row baseline H1 synthetic package in a
localhost read-only viewer, with honest nulls and explicit PRE/COMMAND/POST phases.
Spec: the user's CYBER_H1_VISUAL_INSPECTOR_V1 requirements.
Stack: Python stdlib HTTP/JSON, self-contained SVG/HTML/CSS/JavaScript.

Global constraints: no historical edits, source pins exact, external synthetic
store only, one baseline arm, no resampling/fill/derived vehicle measurements,
T1 ceiling, no write/model/search/optimizer/holdout authority.

Review focus: source/row/page drift; post-step plotted at completion; null as null;
Host/Origin/traversal/mutation rejection; exact immutable resume and no symlinks.

## 1. Pure adapter and immutable catalog
Files: cyber_h1_visual_adapter.py, cyber_h1_visual_catalog.py, test_cyber_h1_visual_adapter.py.
Interfaces: load_source(store), convert(package), persist(output, frameset),
load(output), catalog(frameset). Page size 100, exactly eight pages and 800 frames.
- [x] RED source drift, phase map, nulls, single arm, page integrity and store tests.
- [x] Implement exact source validation, pure mapping, atomic no-overwrite pages.
- [x] GREEN and two complete conversions with identical receipts/input bytes.

## 2. Read-only server and self-contained viewer
Files: cyber_h1_visual_server.py, static/cyber_h1_visual.{html,js,css},
test_cyber_h1_visual_server.py.
Interfaces: create_server(store, host, port), GET/HEAD catalog/run/pages/frame/health.
- [x] RED loopback/Host/Origin/GET-only/bounds/traversal/security header tests.
- [x] Implement explicit manual server; no filesystem endpoint or subprocess.
- [x] Implement synchronized SVG charts, phase cursor, pose, null/evidence panels.
- [x] GREEN API tests and actual browser first/middle/final/play/step/event checks.

## 3. Evidence and delivery
Files: cyber_h1_visual_publication.py, six aggregate JSON outputs, feature doc.
- [x] Pin historical and new source/aggregate receipts; browser telemetry evidence.
- [x] Independent review and regression fixes; all required validation suites.
- [x] Prepare reviewed commit/push. Post-push exact-HEAD CI SUCCESS and clean/equal fetch remain delivery gates reported in the handoff.
