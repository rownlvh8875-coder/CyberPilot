"""Aggregate-only additive publication; private filesystem inventories stay local."""

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from tools.cyberpilot.check_publication import scan_bytes

FORBIDDEN_KEYS = frozenset(
  (
    'private_path',
    'timestamp',
    'timestamps',
    'logger_start_id',
    'targets',
    'predictions',
    'residuals',
    'commands',
    'steering_values',
    'raw_rows',
    'numeric_rows',
    'design_matrix',
    'local_path',
  )
)


def validate(row):
  p.verify(row)

  def visit(value):
    if isinstance(value, dict):
      if set(value) & FORBIDDEN_KEYS:
        raise ValueError('PRIVATE_PUBLICATION_FIELD')
      for item in value.values():
        visit(item)
    elif isinstance(value, list):
      for item in value:
        visit(item)

  visit(row)
  if scan_bytes('aggregate.json', p.canonical(row)):
    raise ValueError('PRIVATE_PUBLICATION_CONTENT')
  return row


def write(path, row):
  p.persist(path, validate(row))
