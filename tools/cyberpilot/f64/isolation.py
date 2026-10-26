"""Reviewed-code Controller isolation, not a hostile-code OS sandbox."""
import ast
import builtins
from collections.abc import Mapping, Sequence
import importlib.abc
import hashlib
from pathlib import Path
from types import ModuleType
import sys

FORBIDDEN = ('openpilot.selfdrive', 'selfdrive', 'opendbc', 'opendbc_repo', 'panda', 'pandacan',
             'cereal', 'msgq', 'openpilot.system', 'openpilot.tools.sim',
             'openpilot.tools.cyber_autotune.trajectory_authority_core',
             'openpilot.tools.cyber_autotune.trajectory_v0_screen',
             'openpilot.tools.cyber_autotune.smoothness_closed_loop')
_ACTIVE = []
_ORIGINAL_IMPORT = builtins.__import__


class IsolationError(RuntimeError):
  """Fixed safe codes, no user data."""


def forbidden(name):
  return any(name == prefix or name.startswith(prefix + '.') for prefix in FORBIDDEN)


def inspect_text(text):
  tree = ast.parse(text)
  dependencies, calls = [], []
  for node in ast.walk(tree):
    if isinstance(node, ast.Import):
      dependencies += [a.name for a in node.names if forbidden(a.name)]
    elif isinstance(node, ast.ImportFrom):
      base = node.module or ''
      dependencies += [name for name in [base, *(base+'.'+a.name for a in node.names)] if forbidden(name)]
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ('eval', 'exec', '__import__'):
      calls.append(node.func.id)
  return {'allowed': not dependencies and not calls, 'controller_dependencies': sorted(set(dependencies)),
          'unsafe_dynamic_calls': sorted(set(calls))}


def inspect_project(root):
  root = Path(root)
  approved = {'tools.cyberpilot.f64.'+name for name in ('source', 'metrics', 'oracle', 'isolation', 'runner', 'entry')}
  approved |= {'tools.cyberpilot.synthetic_command_rate_attribution_v1', 'tools.cyberpilot.cli_security_f51'}
  queue = sorted(n for n in approved if n.startswith('tools.cyberpilot.f64.'))
  seen, imports, dependencies, unknown, unsafe = set(), {}, [], [], []
  while queue:
    module = queue.pop()
    if module in seen:
      continue
    seen.add(module)
    path = root / (module.replace('.', '/')+'.py')
    if not path.is_file():
      unknown.append(module)
      continue
    text = path.read_text()
    tree = ast.parse(text)
    checked = inspect_text(text)
    unsafe.extend(module+':'+v for v in checked['unsafe_dynamic_calls'])
    names = []
    for node in ast.walk(tree):
      if isinstance(node, ast.Import):
        names.extend(a.name for a in node.names)
      elif isinstance(node, ast.ImportFrom):
        base = node.module or ''
        names.extend([base, *(base+'.'+a.name for a in node.names)])
      elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'import_module'):
        if (module == 'tools.cyberpilot.synthetic_command_rate_attribution_v1' and node.args and
            isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
          names.append(node.args[0].value)
        else:
          unsafe.append(module+':unresolved_dynamic_import')
    dependencies.extend(n for n in names if forbidden(n))
    imports[module] = sorted(set(names))
    for name in names:
      if name.split('.')[0] in sys.stdlib_module_names or name == '__future__':
        continue
      if name.startswith('tools.'):
        # Module path or imported symbol from an existing approved module.
        candidates = [name]
        while '.' in candidates[-1]:
          candidates.append(candidates[-1].rsplit('.', 1)[0])
        target = next((n for n in candidates if (root/(n.replace('.', '/')+'.py')).is_file()), None)
        if target is None:
          if (root/name.replace('.', '/')).is_dir():
            continue
          unknown.append(name)
        elif target not in approved:
          unknown.append(target)
        else:
          queue.append(target)
        # Initializers on the path must be reviewed too, never ignored.
        pieces = name.split('.')
        for i in range(1, len(pieces)):
          init = root / '/'.join(pieces[:i]) / '__init__.py'
          if init.is_file() and init.read_text().strip():
            unknown.append('.'.join(pieces[:i])+'.__init__')
      elif name:
        unknown.append(name)
    if module == 'tools.cyberpilot.synthetic_command_rate_attribution_v1':
      if hashlib.sha256(path.read_bytes()).hexdigest() != '9ff1a333dcc45d14577246651f88b28d5935a6dce954b308bb90b1d3f4ccf018':
        unknown.append(module+':pin')
  return {'project_modules_checked': len(seen), 'controller_dependencies': sorted(set(dependencies)),
          'project_import_graph': imports, 'transitive_local_graph': True,
          'unapproved_imports': sorted(set(unknown)), 'unsafe_dynamic_calls': sorted(set(unsafe)),
          'scope': 'REVIEWED_LOCAL_TRANSITIVE_GRAPH_AND_STDLIB_ALLOWLIST_NOT_HOSTILE_CODE_SANDBOX'}


def active():
  return bool(_ACTIVE)


def require_active():
  if not active():
    raise IsolationError('F64_ISOLATION_IMPORT')


def _blocked(code, counter):
  if _ACTIVE:
    _ACTIVE[-1].counts[counter] += 1
  raise IsolationError(code)


class _Finder(importlib.abc.MetaPathFinder):
  def find_spec(self, fullname, path=None, target=None):
    if _ACTIVE and forbidden(fullname):
      _blocked('F64_ISOLATION_IMPORT', 'forbidden_import_attempts')
    return None


def _import(name: str, globals: Mapping[str, object] | None = None, locals: Mapping[str, object] | None = None,  # noqa: A002
            fromlist: Sequence[str] | None = (), level: int = 0) -> ModuleType:
  # Preserve the exact keyword names/types of Python's builtin import API.
  if _ACTIVE and forbidden(name):
    _blocked('F64_ISOLATION_IMPORT', 'forbidden_import_attempts')
  return _ORIGINAL_IMPORT(name, globals, locals, fromlist, level)


def _audit(event, args):
  if not _ACTIVE:
    return
  if event == 'import' and args and forbidden(str(args[0])):
    _blocked('F64_ISOLATION_IMPORT', 'forbidden_import_attempts')
  if event in ('subprocess.Popen', 'os.system', 'os.fork', 'os.forkpty', 'os.posix_spawn', 'os.exec', 'os.spawn'):
    _blocked('F64_ISOLATION_PROCESS', 'process_attempts')
  if event.startswith('socket.'):
    _blocked('F64_ISOLATION_NETWORK', 'network_attempts')
  if event == 'ctypes.dlopen':
    _blocked('F64_ISOLATION_NATIVE', 'native_loader_attempts')
  if event == 'open' and args and isinstance(args[0], (str, bytes)):
    name = args[0].decode(errors='replace') if isinstance(args[0], bytes) else args[0]
    lower = name.lower().replace('\\', '/')
    if lower.endswith(('.rlog', '.qlog', '.zst', '.bz2')) or 'private_e2' in lower or '/private/e2' in lower:
      _blocked('F64_ISOLATION_PRIVATE', 'private_access_attempts')


sys.addaudithook(_audit)


class Guard:
  def __init__(self):
    self.counts = dict.fromkeys(('controller_calls', 'forbidden_import_attempts', 'process_attempts',
                                 'network_attempts', 'native_loader_attempts', 'private_access_attempts'), 0)
    self.finder = _Finder()

  def __enter__(self):
    if any(forbidden(name) for name in sys.modules):
      raise IsolationError('F64_ISOLATION_IMPORT')
    _ACTIVE.append(self)
    sys.meta_path.insert(0, self.finder)
    builtins.__dict__['__import__'] = _import  # Runtime interception of the builtin module namespace.
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    sys.meta_path.remove(self.finder)
    if not _ACTIVE or _ACTIVE[-1] is not self:
      raise IsolationError('F64_ISOLATION_IMPORT')
    _ACTIVE.pop()
    if not _ACTIVE:
      builtins.__import__ = _ORIGINAL_IMPORT
    return False
