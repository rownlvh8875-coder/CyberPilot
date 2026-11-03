"""Best-effort diagnostics only after an offline tool has determined its result."""

import sys
import warnings


def _warn_after_result(message: str) -> None:
    """Best-effort diagnostic only; never replace a determined result."""
    try:
        warnings.warn(message, RuntimeWarning, stacklevel=2)
    except Exception:
        # Caller warning filters/hooks may raise. Keep their policy unchanged.
        try:
            print(f'WARNING: {message}', file=sys.stderr)
        except Exception:
            # A closed/broken diagnostic sink cannot undo publication either.
            pass
