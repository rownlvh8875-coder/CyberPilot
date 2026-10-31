"""Explicit isolated synthetic native experiment. Importing this file is inert."""

import argparse
import base64
import csv
import hashlib
import importlib
import importlib.util
import io
import json
import platform
import sys
import sysconfig
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_SHA = '098a19d69e8d233ac653503b53761a94824f31812757a11a7ded1589fe1e0788'
WHEEL_SHA = '48938e0436ab1be615fc0a41434119a2065490a6212b9a5e56949e89b0588b76'
FORBIDDEN = {'openpilot', 'opendbc', 'cereal', 'numpy', 'synthetic_rate_constraint_feasibility_v1'}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def number(value: float) -> dict:
    if type(value) is not float:
        raise ValueError('OBSERVATION_FLOAT_TYPE')
    return {'type': type(value).__module__ + '.' + type(value).__name__, 'hex': value.hex()}


def verify_inputs(wheel: Path, schema: Path) -> dict:
    if schema.is_symlink() or sha(schema.read_bytes()) != SCHEMA_SHA:
        raise ValueError('SCHEMA_IDENTITY')
    if wheel.is_symlink() or sha(wheel.read_bytes()) != WHEEL_SHA:
        raise ValueError('WHEEL_IDENTITY')
    return {'schema_sha256': SCHEMA_SHA, 'wheel_sha256': WHEEL_SHA}


def verify_installed(wheel: Path, site: Path) -> dict:
    """Byte-for-byte comparison with the already pinned wheel, before import."""
    hashes = {}
    with zipfile.ZipFile(wheel) as archive:
        for entry in archive.infolist():
            name = entry.filename
            relative = PurePosixPath(name)
            if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name or name in hashes:
                raise ValueError('UNSAFE_WHEEL')
            if entry.is_dir():
                continue
            path = site / name
            if (not path.is_file() or path.is_symlink() or site.resolve() not in path.resolve().parents
                    or any(parent.is_symlink() for parent in path.parents if parent != site)):
                raise ValueError('INSTALLED_IDENTITY:' + name)
            if not name.endswith('.dist-info/RECORD') and path.read_bytes() != archive.read(entry):
                raise ValueError('INSTALLED_IDENTITY:' + name)
            hashes[name] = sha(path.read_bytes())
    for record in [name for name in hashes if name.endswith('.dist-info/RECORD')]:
        hashes.update(_verify_record(site, record, set(hashes)))
    # -B stops writes, NOT reads. Reject caches and extra importable package
    # files rather than attributing executed bytecode to a verified source path.
    for name in hashes:
        path = site / name
        if name.endswith('.py'):
            cache = path.parent / '__pycache__'
            if (cache.is_symlink() or any(cache.glob(path.stem + '.*.pyc'))
                    or path.with_suffix('.pyc').exists() or path.with_suffix('.pyc').is_symlink()):
                raise ValueError('INSTALLED_UNEXPECTED_BYTECODE:' + name)
    roots = {PurePosixPath(name).parts[0] for name in hashes if '/' in name and not name.startswith('../')}
    for name in roots:
        directory = site / name
        if not directory.is_dir():
            continue
        for path in directory.rglob('*'):
            relative = path.relative_to(site).as_posix()
            if path.is_symlink() or (path.is_file() and relative not in hashes):
                raise ValueError('INSTALLED_UNEXPECTED_FILE:' + relative)
    return hashes


def _verify_record(site: Path, record: str, payload_names: set[str]) -> dict:
    permitted_extra = {str(PurePosixPath(record).parent / name) for name in ['INSTALLER', 'REQUESTED', 'direct_url.json']}
    if record == 'pycapnp-2.1.0.dist-info/RECORD' and site.parts[-3:] == ('lib', 'python3.12', 'site-packages'):
        # Exact wheel-declared entrypoint wrapper, installer-generated and NOT run.
        permitted_extra.add('../../../bin/capnpc-cython')
    seen = set()
    extras = {}
    for row in csv.reader(io.StringIO((site / record).read_text())):
        if len(row) != 3:
            raise ValueError('INSTALLED_RECORD_ROW')
        name, digest, size = row
        if name in seen or name not in payload_names | permitted_extra:
            raise ValueError('INSTALLED_RECORD_PATH')
        seen.add(name)
        if name == record:
            if digest or size:
                raise ValueError('INSTALLED_RECORD_SELF')
            continue
        path = site / name
        if not path.is_file() or path.is_symlink():
            raise ValueError('INSTALLED_RECORD_FILE')
        raw = path.read_bytes()
        expected = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b'=').decode()
        if digest != 'sha256=' + expected or size != str(len(raw)):
            raise ValueError('INSTALLED_RECORD_HASH')
        if name in permitted_extra:
            extras[name] = sha(raw)
    if not payload_names <= seen:
        raise ValueError('INSTALLED_RECORD_COVERAGE')
    return extras


def _type(value) -> str:
    return type(value).__module__ + '.' + type(value).__name__


def _fields(module) -> list:
    return [{'name': f.name, 'ordinal': f.ordinal.explicit, 'type': f.slot.type.which()}
            for f in module.schema.node.struct.fields if f.which() == 'slot']


def _floats(car) -> list:
    fixtures = [
        ('point_three', 0.3), ('negative_zero', -0.0), ('positive_one', 1.0), ('negative_one', -1.0),
        ('smallest_subnormal', float.fromhex('0x1p-149')), ('smallest_normal', float.fromhex('0x1p-126')),
        ('nan', float('nan')), ('positive_infinity', float('inf')), ('negative_infinity', -float('inf')), ('overflow', 1e39),
    ]
    rows = []
    for name, value in fixtures:
        row = {'id': name, 'assigned': number(value)}
        message = car.CarControl.new_message()
        try:
            message.actuators.torque = value
            row['builder'] = number(message.actuators.torque)
            raw = message.to_bytes()
            row['wire_sha256'] = sha(raw)
            with car.CarControl.from_bytes(raw) as reader:
                row['reader'] = number(reader.actuators.torque)
        except Exception as error:
            row['exception'] = _type(error)
        rows.append(row)
    return rows


def _defaults(car) -> dict:
    rows = {}
    for explicit in [False, True]:
        message = car.CarControl.new_message()
        message.init('actuators')
        written = ['actuators(pointer)']
        if explicit:
            message.actuators.torque = 0.0
            message.latActive = False
            written += ['actuators.torque', 'latActive']
        raw = message.to_bytes()
        with car.CarControl.from_bytes(raw) as reader:
            values = {'torque': number(reader.actuators.torque), 'latActive': reader.latActive,
                      'wire_sha256': sha(raw), 'written_fields': written}
            for field in ['latActive', 'actuators']:
                try:
                    values['has_' + field] = reader._has(field)
                except Exception as error:
                    values['has_' + field] = {'exception': _type(error)}
        rows['explicit' if explicit else 'omitted'] = values
    rows['presence_authority'] = 'CONTROLLED_CONSTRUCTION_LEDGER_REQUIRED'
    return rows


def _messages(car) -> dict:
    cc, cs = car.CarControl.new_message(), car.CarState.new_message()
    cc.actuators.torque, cc.latActive = 0.25, True
    cs.steeringTorque, cs.steeringAngleDeg = 1.5, -7.25
    raw_cc, raw_cs = cc.to_bytes(), cs.to_bytes()
    with car.CarControl.from_bytes(raw_cc) as a, car.CarState.from_bytes(raw_cs) as b:
        rows = {'cc_builder_type': _type(cc), 'cs_builder_type': _type(cs),
                'cc_reader_type': _type(a), 'cs_reader_type': _type(b),
                'cc_schema_id': cc.schema.node.id, 'cs_schema_id': cs.schema.node.id,
                'cc_reader_schema_id': a.schema.node.id, 'cs_reader_schema_id': b.schema.node.id,
                'cc_fields': _fields(car.CarControl), 'cs_fields': _fields(car.CarState),
                'actuator_fields': _fields(car.CarControl.Actuators),
                'torque': number(a.actuators.torque), 'active': a.latActive,
                'driver': number(b.steeringTorque), 'angle': number(b.steeringAngleDeg)}
        try:
            _ = a.r19UnknownField
        except Exception as error:
            rows['invalid_field_exception'] = _type(error)
    return rows


def _receipt(installed: dict, include_sha: str, capnp) -> dict:
    modules = {}
    for name, module in sorted(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if filename and Path(filename).is_file():
            modules[name] = {'path': str(Path(filename).resolve()), 'sha256': sha(Path(filename).read_bytes())}
    mapped = {}
    for line in Path('/proc/self/maps').read_text().splitlines():
        columns = line.split(maxsplit=5)
        if len(columns) == 6 and columns[5].startswith('/'):
            path = Path(columns[5])
            mapped[str(path)] = sha(path.read_bytes())
    return {'python_version': platform.python_version(), 'python_binary_sha256': sha(Path(sys.executable).read_bytes()),
            'platform': platform.platform(), 'prefix': sys.prefix, 'capnp_version': capnp.__version__,
            'installed_wheel_files': installed, 'include_sha256': include_sha,
            'imported_files': modules, 'mapped_files': mapped,
            'scope': 'OBSERVED_PROCESS_FILES_NOT_AUTHENTICATED_OS_IMAGE_OR_PORTABLE_ABI'}


def observe(wheel: Path, schema: Path, *, owned_boundary: bool = False) -> dict:
    if type(owned_boundary) is not bool:
        raise ValueError('EXPLICIT_BOOLEAN_MODE')
    identity = verify_inputs(wheel, schema)
    if not sys.flags.isolated or not sys.flags.dont_write_bytecode:
        raise ValueError('ISOLATED_NO_BYTECODE_REQUIRED')
    if (platform.python_implementation(), platform.python_version(), sys.platform, platform.machine()) != (
            'CPython', '3.12.13', 'linux', 'x86_64'):
        raise ValueError('UNSUPPORTED_RUNTIME')
    if 'capnp' in sys.modules or sys.prefix == sys.base_prefix:
        raise ValueError('FRESH_NATIVE_VENV_REQUIRED')
    site = Path(sysconfig.get_paths()['purelib'])
    installed = verify_installed(wheel, site)
    spec = importlib.util.find_spec('capnp')
    if spec is None or spec.origin != str(site / 'capnp/__init__.py'):
        raise ValueError('UNEXPECTED_NATIVE_IMPORT_ORIGIN')
    capnp: Any = importlib.import_module('capnp')
    capnp.remove_import_hook()
    with zipfile.ZipFile(wheel) as archive:
        include = archive.read('capnp/c++.capnp')
    # Explicit import closure: one exact car schema and one wheel-owned annotation.
    if b'import ' in include or schema.read_bytes().count(b'import ') != 1:
        raise ValueError('UNEXPECTED_SCHEMA_IMPORT_CLOSURE')
    with tempfile.TemporaryDirectory(prefix='r19-owned-schema-') as scratch:
        root = Path(scratch)
        (root / 'include').mkdir()
        (root / 'include/c++.capnp').write_bytes(include)
        (root / 'car.capnp').write_bytes(schema.read_bytes())
        car = capnp.load(str(root / 'car.capnp'), imports=[str(root)])
        observations = {
            'schema_version': 1, 'scope': 'CONTROLLED_SYNTHETIC_NATIVE_OBSERVATIONS_ONLY', 'identity': identity,
            'construction_api': 'CarControl/CarState.new_message(); from_bytes(owned_bytes) context manager',
            'types': _messages(car), 'defaults': _defaults(car), 'float32': _floats(car),
            'independent_ieee_reference': {'point_three_binary32_hex': '0x1.3333340000000p-2',
                                           'logical_word_not_wire_extraction': '3e99999a'},
            'lifetime': {'reader_use': 'WITHIN_OWNED_BYTES_CONTEXT_ONLY', 'after_context_access': 'NOT_PROBED_UNSAFE',
                         'general_lifetime_guarantee': 'NOT_QUALIFIED'},
            'qualification': {'Q01': 'ARTIFACT_AND_PROCESS_RECEIPT_OBSERVED_NOT_OS_ATTESTATION',
                              'Q02': 'SCHEMA_TYPES_AND_OWNED_READ_OBSERVED_GENERAL_LIFETIME_NOT_QUALIFIED',
                              'Q03': 'DEFAULT_AMBIGUITY_OBSERVED_LEDGER_REQUIRED', 'Q04': 'SYNTHETIC_FLOAT32_OBSERVED',
                              'Q05': 'NOT_QUALIFIED', 'Q06': 'NOT_IMPLEMENTED_READER_BLOCKED'},
            'native_reader_activation': 'NOT_ALLOWED',
        }
        if owned_boundary:
            # -B alone still reads old caches. Fresh private prefix prevents
            # repository-source caches from substituting for this closed demo.
            previous_prefix = sys.pycache_prefix
            with tempfile.TemporaryDirectory(prefix='r20-cold-import-') as cold:
                sys.pycache_prefix = cold
                sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
                try:
                    from native_qualification.owned_demo import demonstrate
                    observations = demonstrate(car)
                    observations['identity'] = identity
                finally:
                    sys.pycache_prefix = previous_prefix
    forbidden = sorted(n for n in sys.modules if n.split('.')[0] in FORBIDDEN)
    if forbidden:
        raise ValueError('FORBIDDEN_MODULES_LOADED')
    observations['forbidden_modules_loaded'] = forbidden
    return {'observations': observations, 'receipt': _receipt(installed, sha(include), capnp)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--schema', type=Path, required=True)
    parser.add_argument('--owned-boundary', action='store_true')
    args = parser.parse_args()
    sys.stdout.buffer.write(canonical(observe(args.wheel.absolute(), args.schema.absolute(), owned_boundary=args.owned_boundary)))


if __name__ == '__main__':
    main()
