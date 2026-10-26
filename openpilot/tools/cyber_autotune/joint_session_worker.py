"""Fixed joint entry; execute the existing worker bootstrap from source, not pyc."""
from pathlib import Path
import runpy


if __name__ == '__main__':
  worker = Path(__file__).resolve().with_name('lateral_session_worker.py')
  # No caller-selected path/module. Parent supervises startup; the common worker
  # arms its inherited absolute deadline before importing repository code.
  namespace = runpy.run_path(str(worker), run_name='cyber_joint_worker')
  raise SystemExit(namespace['main'](_joint=True))
