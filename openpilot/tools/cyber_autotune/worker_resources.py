"""Linux trusted offline subprocess caps; never call from a control process."""
import os
import resource


MAX_ADDRESS_SPACE_BYTES = 2 * 1024 ** 3
MAX_CPU_SECONDS = 60


def apply_worker_limits():
  # Resource ceilings, not control tolerances; wall-time/process cleanup is owned
  # by the supervisor. Address space includes native libraries and trace buffers.
  resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
  resource.setrlimit(resource.RLIMIT_CPU, (MAX_CPU_SECONDS, MAX_CPU_SECONDS))
  resource.setrlimit(resource.RLIMIT_AS, (MAX_ADDRESS_SPACE_BYTES, MAX_ADDRESS_SPACE_BYTES))
  for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
