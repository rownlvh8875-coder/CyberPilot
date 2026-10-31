"""Preserved portable model results + explicitly constructed test receipt, no model."""

import hashlib
import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / 'fixtures/r31_report'
NAMES = ['INPUT.json', 'RESULTS.json', 'TRACE.csv', 'SUMMARY_KO.md', 'RECEIPT.json']


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def rehash(root):
    (root / 'SHA256SUMS.txt').write_bytes(''.join(hashlib.sha256((root / name).read_bytes()).hexdigest() + '  ' + name + '\n'
                                               for name in sorted(NAMES)).encode())


def write_bundle(root, profile='sign'):
    root.mkdir()
    for name in NAMES[:-1]:
        (root / name).write_bytes((FIXTURES / profile / name).read_bytes())
    source = json.loads((root / 'INPUT.json').read_bytes())
    receipt = {'schema_version': 1, 'input_raw_sha256': source['input_raw_sha256'],
               'input_path': '/declared-fixture/input.json', 'output_path': '/declared-fixture/output',
               'source_root': '/declared-fixture/component', 'model_origin': '/declared-fixture/component/src/cyberlateral_dev/__init__.py',
               'python_executable': '/declared-fixture/python', 'python_version': '3.12.13',
               'python_executable_sha256': '0' * 64, 'python_prefix': '/declared-fixture/env',
               'cache_policy': 'COLD_PRIVATE_PREFIX_IN_CLI_ONLY_NOT_IN_PROCESS_API', 'forbidden_modules_loaded': [],
               'scope': 'TEST_FIXTURE_DECLARATION_NOT_RUNTIME_ATTESTATION'}
    (root / 'RECEIPT.json').write_bytes(canonical(receipt))
    rehash(root)
    return root


def edit_json(root, name, change):
    value = json.loads((root / name).read_bytes())
    change(value)
    (root / name).write_bytes(canonical(value))
    rehash(root)
