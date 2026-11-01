"""One qualified synthetic backend/context per isolated fresh worker process."""

import importlib
import importlib.util
import platform
import sys
import sysconfig
import tempfile
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .worker import FORBIDDEN, PUBLIC_WHEEL_SHA, _receipt, sha, verify_experiment, verify_inputs, verify_installed


@dataclass
class QualifiedSession:
    adapter: Any
    receipt: dict = field(default_factory=dict)


@contextmanager
def qualified_adapter(wheel: Path, schema: Path, package_wheel: Path):
    verify_experiment(False, True, package_wheel)
    verify_inputs(wheel, schema)
    if not sys.flags.isolated or not sys.flags.dont_write_bytecode:
        raise ValueError('ISOLATED_NO_BYTECODE_REQUIRED')
    if (platform.python_implementation(), platform.python_version(), sys.platform, platform.machine()) != (
            'CPython', '3.12.13', 'linux', 'x86_64'):
        raise ValueError('UNSUPPORTED_RUNTIME')
    if 'capnp' in sys.modules or sys.prefix == sys.base_prefix:
        raise ValueError('FRESH_NATIVE_VENV_REQUIRED')
    if 'cyberlateral_dev' in sys.modules:
        raise ValueError('FRESH_PUBLIC_PACKAGE_ENV_REQUIRED')
    site = Path(sysconfig.get_paths()['purelib'])
    installed = verify_installed(wheel, site)
    public_installed = verify_installed(package_wheel, site)
    for name, code in [('capnp', 'UNEXPECTED_NATIVE_IMPORT_ORIGIN'), ('cyberlateral_dev', 'UNEXPECTED_PUBLIC_IMPORT_ORIGIN')]:
        spec = importlib.util.find_spec(name)
        if spec is None or spec.origin != str(site / name / '__init__.py'):
            raise ValueError(code)
    capnp: Any = importlib.import_module('capnp')
    capnp.remove_import_hook()
    with zipfile.ZipFile(wheel) as archive:
        include = archive.read('capnp/c++.capnp')
    if b'import ' in include or schema.read_bytes().count(b'import ') != 1:
        raise ValueError('UNEXPECTED_SCHEMA_IMPORT_CLOSURE')
    previous_prefix = sys.pycache_prefix
    with tempfile.TemporaryDirectory(prefix='r28-qualified-context-') as scratch:
        root = Path(scratch)
        (root / 'include').mkdir()
        (root / 'include/c++.capnp').write_bytes(include)
        (root / 'car.capnp').write_bytes(schema.read_bytes())
        (root / 'cold').mkdir()
        sys.pycache_prefix = str(root / 'cold')
        session = None
        try:
            from integration_tools.native_adapter import _SyntheticAdapter
            car = capnp.load(str(root / 'car.capnp'), imports=[str(root)])
            session = QualifiedSession(_SyntheticAdapter(car))
            yield session
        finally:
            if session is not None:
                session.adapter.close()
            sys.pycache_prefix = previous_prefix
    if any(name.split('.')[0] in FORBIDDEN for name in sys.modules):
        raise ValueError('FORBIDDEN_MODULES_LOADED')
    if session is not None:
        session.receipt.update(_receipt(installed, sha(include), capnp))
        session.receipt.update(public_wheel_sha256=PUBLIC_WHEEL_SHA, public_installed_files=public_installed)
