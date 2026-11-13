"""Bound one-shot verification commands and their inherited process group."""

import os
import signal
import subprocess


def run_command(argv, cwd, env, log_path, timeout=180):
  with log_path.open('w') as stream:
    process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    try:
      code = process.wait(timeout=timeout)
    except BaseException:
      try:
        os.killpg(process.pid, signal.SIGTERM)
      except ProcessLookupError:
        pass
      try:
        process.wait(timeout=2)
      except subprocess.TimeoutExpired:
        pass
      finally:
        try:
          os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
          pass
        process.wait(timeout=3)
      raise
    else:
      # Commands are one-shot: a successful parent must not leave a background
      # monitor behind either. Normal native_check already reaps its child.
      try:
        os.killpg(process.pid, signal.SIGKILL)
      except ProcessLookupError:
        pass
      return code
