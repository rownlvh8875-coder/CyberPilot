# R32.2 mobile chart readability

User evidence R321_LOCAL_VISUAL_CHECK_FAIL identifies unreadable SVG axis ticks
and captions at viewport390x844. ZIP SHA256
`08f2f03b20f0148936464d75d784c66e2715982a604385f809e8df5e102241e2`.
The720-unit SVG shrinks to340CSS px, also shrinking its11-unit text. Both supplied
chart captures confirm this; this is not missing Korean glyphs or changed values.

## Scope and approach

Make axis labels and the invocation-index caption ordinary14CSS-px HTML outside
the responsive SVG. A grid reserves an intrinsic label column and flexible plot;
the plot retains existing polyline/circle coordinates with a padded plot-only
viewBox. Move the legend to wrapping complete entries at14CSS px. A single resumed
index is centered, not repeated at two ends. Choose this small display-only fix
under the user's delegated implementation choices.

Alternatives: enlarging text inside the fixed viewBox remains scale-dependent and
can clip labels; a minimum-width scrolling graph keeps tiny screens readable but
unnecessarily hides part of the plot. Neither is selected.

## Invariants and non-goals

No saved input/VIEW/table numbers, series coordinates, calculations, R31 producer,
validator/public model/wheel/native code, dependencies or workflow changes.
Two charts, Korean, exact hex/integer authority, distinct requested/applied state,
single-point markers, CSP/no JS or external assets and all closed gates remain.
This does not establish vehicle timing, r/T2/scale, safety, runtime or deployment.

## Verification boundary

TDD checks real rendered HTML, label content/placement outside SVG and graph/data
preservation. Full pure tests, static tools, immutable guards and repeated/fresh
report generation must pass. These checks are not browser layout measurements.
Known cloud administrator navigation denial is not bypassed or retried. Actual
post-fix desktop/mobile appearance remains PENDING_LOCAL_RECHECK; produce a precise
authorized local-Codex check rather than asking the user to inspect manually.
