"""CyberLateral development module V1; synthetic computation, not vehicle runtime."""

from ._r4.domain import Limits
from ._r4.flow_types import State as LateralState
from ._r4.quantization_types import NormalizedSample as LateralInput
from ._r4.state_model import initial_state
from .api import step
from .output_types import LateralOutput
from .simulation import SimulationResult, simulate

__version__ = "0.3.0"

__all__ = ["LateralInput", "LateralOutput", "LateralState", "Limits", "SimulationResult", "__version__", "initial_state", "simulate", "step"]
