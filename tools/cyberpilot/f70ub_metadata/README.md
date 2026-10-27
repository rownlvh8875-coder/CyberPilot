# F70UB Static Source Boundary V1

This external, standard-library component validates two frozen metadata records.
It does not admit command samples, generate calculator inputs, execute a limiter,
or resolve the original F70UB context instance or r budget.

Run tests from an extracted package root:

```sh
python3 -I -B -m unittest discover -s . -p 'test_*.py' -v
python3 -I -S -B verify_bundle.py --output-dir /path/to/new/output-a
python3 -I -S -B verify_bundle.py --output-dir /path/to/new/output-b
diff -r /path/to/new/output-a /path/to/new/output-b
```

Output directories must be new. The verifier reads only its own fixed artifact
names. Use a trusted, private extraction directory; concurrent hostile filesystem
mutation and hostile interpreter/module replacement are outside this scope.

Core API: load_json(bytes), validate_contract(object), validate_record(object,
contract), canonicalize_record(object), hash_record(object). BoundaryError.code
is a fixed diagnostic. Admission means exact registered metadata identity only.
Never pass these results to an evaluator as numeric samples.

The full evidence manifest excludes itself. The ZIP SHA is detached to avoid a
self-reference; the ZIP is created once and is not included in its own archive.
Existing 202-test results are evidence from the immutable repository baseline;
they are not extra tests shipped in this standalone 45-test package.
