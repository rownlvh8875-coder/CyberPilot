# R59 — R32 footer long-token wrapping

The user selected the next step stated after R58: fix the footer wrapping and
recheck the same screens. Ordinary offline implementation choices and routine
questions were previously delegated. Baseline main is
26ad702efb1e3ec6fa956202f9056bcea0655074.

## Intent and approach

R58 measured document width391 and actual horizontal pan1 at viewport390 in both
preserved sign/resumed reports. Text-range inspection located the unbreakable
SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE token in the footer. A separate DOM-only
diagnostic eliminated the overflow by allowing that footer text to wrap.

Extend the existing `code` overflow-wrap rule to `footer` in the R32 renderer.
This is the author's minimal implementation choice. Shrinking fonts would harm
readability; hiding overflow would mask content; broad body wrapping would touch
unrelated text. No wording, graph, table, public API or numerical changes.

## Proof and boundaries

Use a real Chromium regression against actual renderer output before the edit
and after it. At390, expect391/pan1 before and390/pan0 after, without tolerance.
Exercise narrower/wider selected mobile widths and desktop as additional checks.
Preserve footer text, VIEW bytes, graphs, typed table values, scoped scrolling,
local links, CSP and the14px axis/legend contract. Recheck the R58 eight-report
desktop/mobile selection with unchanged saved inputs, and inspect actual images.

Keep the existing dependency locks and883-test suite. A browser-dependent
regression is delivered as external reproducible evidence, not a source-string
unit test or a silently skipped CI dependency. The ordinary CI suite alone is
not a browser-layout verdict. Historical R58 FAIL evidence remains unchanged.

No model/native/F61/r/dt/vehicle execution by the browser or renderer. Existing
full unit/gate/CI synthetic work is NONZERO and is not misreported as0. Actual
r/T2/scale remain null, Rate Budget unresolved, Static Gate FAIL, vehicle NO_GO.
No HF writes, main merge, source snapshot edits, dependency changes, browser
policy changes, permission weakening or deletion. Feature branch/PR only.
