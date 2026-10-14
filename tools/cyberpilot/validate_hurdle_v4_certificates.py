"""Deterministic synthetic certificate stress; no source paths or empirical I/O."""

import argparse
import json
from pathlib import Path
import resource
import time
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_certificate as c


def stress():
  n, p = 200000, 93
  base = np.repeat(np.eye(p), 2, axis=0)
  x = np.ascontiguousarray(np.tile(base, (n // len(base) + 1, 1))[:n])
  balanced = np.tile(np.array([0, 1]), n // 2)
  correction = balanced.copy()
  correction[0] = 1  # Exact S!=0, one sparse active correction required.
  cases = [
    ('OVERLAP', balanced, 'NO_SEPARATION'),
    ('SPARSE_CORRECTION', correction, 'NO_SEPARATION'),
    ('QUASI', np.where(x[:, -1] != 0, 1, balanced), 'SEPARATION_PRESENT'),
  ]
  records = []
  for label, labels, expected in cases:
    start = time.monotonic()
    certificate = c.separation_generate(x, labels)
    verification = c.separation_verify(x, labels, certificate)
    assert certificate['status'] == verification['status'] == expected
    assert certificate['certificate_sha256'] == verification['certificate_sha256']
    rank = c.rank_generate(x)
    assert rank['status'] == 'RANK_CERTIFICATE_PASS' and c.rank_verify(x, rank)
    records.append(
      {
        'case': label,
        'N': n,
        'P': p,
        'status': expected,
        'rank_status': rank['status'],
        'elapsed_seconds': time.monotonic() - start,
        'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'active_max': certificate['active_max'],
        'iterations': certificate['iterations'],
        'logical_full_row_passes': certificate['logical_full_row_passes'],
        'exact_verification_rows': verification['exact_verification_rows'],
        'certificate_sha256': certificate['certificate_sha256'],
        'rank_sha256': rank['certificate_sha256'],
      }
    )
  # Medium cone case requires one independent active row per dimension.
  dim = 12
  medium = np.ascontiguousarray(np.tile(np.repeat(np.eye(dim), 3, axis=0), (100, 1)))
  labels = np.tile(np.array([0, 1, 1]), len(medium) // 3)
  start = time.monotonic()
  certificate = c.separation_generate(medium, labels)
  assert certificate['status'] == 'NO_SEPARATION' and certificate['active_max'] == dim
  records.append(
    {
      'case': 'MULTI_ACTIVE_CORRECTION',
      'N': len(medium),
      'P': dim,
      'status': certificate['status'],
      'active_max': certificate['active_max'],
      'iterations': certificate['iterations'],
      'elapsed_seconds': time.monotonic() - start,
      'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
      'certificate_sha256': certificate['certificate_sha256'],
    }
  )
  return {
    'scope': 'SYNTHETIC_ONLY',
    'rng': 'NONE',
    'cases': records,
    'limitations': ['REPEATED_DYADIC_BASIS_CONSTRUCTIONS', 'NOT_A_GENERAL_CONE_RUNTIME_GUARANTEE', 'GENERATOR_INCOMPLETE_EXACT_VERIFIER_AUTHORITATIVE'],
  }


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--output', type=Path, required=True)
  args = parser.parse_args()
  args.output.write_text(json.dumps(stress(), sort_keys=True, indent=2) + '\n')


if __name__ == '__main__':
  main()
