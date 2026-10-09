"""Architecture scaffolding, ownership and evaluation contracts; no TA/SG algorithms."""
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from types import MappingProxyType
import platform
import sys

from openpilot.tools.cyber_autotune import candidate_role_contracts as c
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

ROOT = Path(__file__).resolve().parents[3]
BASELINE = '6c60eb8ba3382c1600d056e7b213c73517ce0e87'
HISTORY = MappingProxyType({'CURRENT': 'BASELINE_EXACT', 'V1': 'TRADEOFF_ONLY', 'V2': 'REJECTED'})
HISTORICAL_ROLES = ('MIXED_HISTORICAL', 'MIXED_HISTORICAL')
OWNERS = (('tracking_error_history', 'TA'), ('feedback_integrator', 'TA'), ('causal_feedforward_history', 'TA'),
          ('last_command', 'SG'), ('reversal_state', 'SG'), ('intervention_state', 'SG'),
          ('physical_delay', 'PLANT'), ('driver_pressed_and_active_source', 'EXPERIMENT'))
EVENTS = ('EXPERIMENT_START', 'INACTIVE', 'STEERING_PRESSED', 'RELEASE', 'REENGAGEMENT', 'CONFIG_CHANGE', 'SCENARIO_BOUNDARY')
# Controller layers reset explicitly. Continuous plant dynamics/queue survive interventions.
# Config changes start a new experiment, never mutate the running plant.
RESETS = tuple((owner, event, 'RETAIN_PHYSICAL_STATE_AND_QUEUE' if owner == 'PLANT' and
                event in ('INACTIVE', 'STEERING_PRESSED', 'RELEASE', 'REENGAGEMENT') else 'FRESH_INSTANCE_NO_RETAINED_STATE')
               for owner in ('TA', 'SG', 'PLANT') for event in EVENTS)
BLOCKERS = ('CALIBRATION_UNCERTAINTY_PENDING', 'INDEPENDENT_CALIBRATION_VALIDATION_PENDING',
            'PIXEL_GEOMETRY_REGISTRATION_PENDING', 'METRIC_CALIBRATION_UNAVAILABLE', 'INDEPENDENT_REFERENCE_UNAVAILABLE')
DETECTABILITY = ('NO_OUTPUT_DIFFERENCE', 'REQUESTED_OUTPUT_DIFFERENCE_PRESENT', 'APPLIED_OUTPUT_DIFFERENCE_PRESENT',
                 'CURVATURE_EFFECT_PRESENT', 'HEADING_EFFECT_PRESENT', 'POSE_EFFECT_PRESENT',
                 'TEMPORALLY_CANCELED', 'OUTPUT_LIMITED', 'DISTANCE_NOT_REACHED')


def hash_object(value):
  return digest(canonical(value))


def validate_ownership(rows):
  if type(rows) is not tuple or rows != OWNERS:
    raise ValueError('EXACT_SINGLE_STATE_OWNER_REQUIRED')


def validate_resets(rows):
  if type(rows) is not tuple or rows != RESETS:
    raise ValueError('EXACT_EXPLICIT_RESET_OWNERSHIP_REQUIRED')


@dataclass(frozen=True)
class CandidateIdentity:
  role: str
  family: str
  source_sha256: str
  config_sha256: str
  state_schema_sha256: str
  reset_policy_sha256: str
  input_contract_sha256: str
  output_contract_sha256: str
  experiment_policy_sha256: str
  native_software_sha256: str
  car_params_profile_sha256: str
  plant_sha256: str
  environment_sha256: str
  timebase_sha256: str

  def __post_init__(self):
    if self.role not in ('TA', 'SG') or self.family != 'ARCHITECTURE_PROBE_ONLY':
      raise ValueError('UNIMPLEMENTED_ROLE_FAMILY_REQUIRED')
    for field in fields(self):
      if field.name.endswith('_sha256'):
        c.sha(getattr(self, field.name))


def identity(role, config):
  """Identity of scaffolding/probe policy only, never an executable candidate."""
  if role not in ('TA', 'SG') or type(config) is not dict:
    raise ValueError('ROLE_CONFIG_REQUIRED')
  files = ('candidate_architecture.py', 'candidate_role_contracts.py', 'candidate_architecture_policy.py',
           'candidate_architecture_probe.py', 'candidate_architecture_evidence.py')
  source = hash_object({name: digest((Path(__file__).parent / name).read_bytes()) for name in files})
  # Bind actual frozen environment/profile/plant identities from prior public policy, without rerunning it.
  from openpilot.tools.cyber_autotune.controller_plant_publication import load
  prior = load()['policy']
  from openpilot.tools.cyber_autotune.controller_plant_evidence import old_index
  context = old_index()['cases'][0]['identities'][0]['components']
  return CandidateIdentity(role, 'ARCHITECTURE_PROBE_ONLY', source, hash_object(config),
                           hash_object([r for r in OWNERS if r[1] == role]), hash_object(RESETS),
                           hash_object(schema(c.TrajectoryInput) if role == 'TA' else
                                       {'command': schema(c.GovernorCommand), 'intervention': schema(c.InterventionInput)}),
                           hash_object(schema(c.TrajectoryAuthorityOutput if role == 'TA' else c.FinalOfflineTorqueCommand)),
                           hash_object(experiment_policy()), context['software_sha256'], context['car_params_sha256'],
                           hash_object(prior['plant']), hash_object(probe_environment()), hash_object({'dt_s': .01, 'owner': 'EXPERIMENT'}))


def schema(cls):
  return {f.name: str(f.type) for f in fields(cls)}


class TrajectoryAuthorityCore:
  __slots__ = ()

  def update(self, inputs):
    if type(inputs) is not c.TrajectoryInput:
      raise ValueError('TRAJECTORY_INPUT_REQUIRED')
    raise ValueError('TRAJECTORY_IMPLEMENTATION_NOT_AUTHORIZED')


@dataclass(frozen=True)
class SmoothnessGovernor:
  enabled: bool = False

  def __post_init__(self):
    if self.enabled is not False:
      raise ValueError('SMOOTHNESS_IMPLEMENTATION_NOT_AUTHORIZED')

  def update(self, command, intervention):
    if type(command) is not c.GovernorCommand or type(intervention) is not c.InterventionInput:
      raise ValueError('COMMAND_AND_INTERVENTION_ONLY')
    # Disabled passthrough is an isolation control, not an inactive-safe vehicle controller.
    return c.FinalOfflineTorqueCommand(command.normalized_torque, command.normalized_torque, command.normalized_torque,
                                       (), 'DISABLED_EXACT_PASSTHROUGH', command.core_source_sha256,
                                       command.core_config_sha256, hash_object(asdict(identity('SG', governor_config()))))


def compose():
  raise ValueError('COMPOSITION_NOT_AUTHORIZED')


def authorize_execution(role):
  if role != 'ARCHITECTURE_PROBE':
    raise ValueError('IMPLEMENTATION_AND_SEARCH_NOT_AUTHORIZED')


def matrix():
  return {'schema': 'CANDIDATE_EXPERIMENT_MATRIX_V1', 'current_alias': True,
          'arms': ['UPSTREAM_BASELINE', 'CYBER_CURRENT_ALIAS', 'CYBER_CANDIDATE'],
          'experiments': {'EXPERIMENT_TA': 'TRAJECTORY_ONLY_PENDING', 'EXPERIMENT_SG': 'SMOOTHNESS_ONLY_PENDING',
                          'EXPERIMENT_COMPOSED': 'NOT_AUTHORIZED'},
          'roles': {'ARCHITECTURE_PROBE': True, 'DEVELOPMENT_SCREEN': False, 'FROZEN_EVALUATION': False, 'STRESS_DIAGNOSTIC': False},
          'historical_70_cases_search_allowed': False, 'composition_execution_allowed': False,
          'objective_combination': 'NO_COMPENSATION_ACROSS_HARD_FAILURES', 'weighted_score_allowed': False,
          'primary_context_m': [5, 10, 15, 20, 25, 30], 'secondary': 'LONGER_HORIZON_DESCRIPTIVE_CONTEXT',
          'secondary_meter_classification_allowed': False, 'threshold_status': 'THRESHOLD_UNJUSTIFIED'}


def validate_matrix(row):
  if type(row) is not dict or hash_object(row) != hash_object(matrix()):
    raise ValueError('EXACT_FROZEN_EXPERIMENT_MATRIX_REQUIRED')


def search_policy(role):
  if role not in ('TA', 'SG'):
    raise ValueError('ROLE_REQUIRED')
  return {'schema': 'TRAJECTORY_SEARCH_POLICY_V1' if role == 'TA' else 'SMOOTHNESS_SEARCH_POLICY_V1',
          'status': 'NOT_FROZEN', 'execution_allowed': False,
          **dict.fromkeys(('family', 'parameter_names', 'units', 'ranges', 'discretization', 'development_scenarios',
                           'frozen_evaluation_scenarios', 'hard_constraints', 'tie_breaking', 'max_candidate_count'), None),
          'state_reset': RESETS}


def readiness():
  return {'schema': 'CANDIDATE_ARCHITECTURE_READINESS_V1',
          'states': ['CANDIDATE_ARCHITECTURE_DEFINED', 'TRAJECTORY_CONTRACT_DEFINED', 'SMOOTHNESS_CONTRACT_DEFINED',
                     'COMPOSED_CONTRACT_DEFINED', 'CONTRACTS_FROZEN', 'EXPERIMENT_MATRIX_FROZEN',
                     'TRAJECTORY_IMPLEMENTATION_PENDING', 'SMOOTHNESS_IMPLEMENTATION_PENDING',
                     'COMPOSITION_NOT_AUTHORIZED', 'SEARCH_NOT_AUTHORIZED', 'IMPLEMENTATION_NOT_YET_AUTHORIZED'],
          'historical_verdicts': dict(HISTORY), 'historical_roles': HISTORICAL_ROLES,
          'v2_historical_violations': 37, 'architecture_baseline_sha': BASELINE,
          'supporting_status': 'CURRENT_CANDIDATE_FAMILY_ARCHITECTURE_REVIEW_REQUIRED',
          'architecture_track': {'TA_IMPLEMENTATION': ['TRAJECTORY_CONTRACT_DEFINED', 'NEW_EXPLICIT_IMPLEMENTATION_AUTHORIZATION'],
                                 'SG_IMPLEMENTATION': ['SMOOTHNESS_CONTRACT_DEFINED', 'NEW_EXPLICIT_IMPLEMENTATION_AUTHORIZATION'],
                                 'COMPOSITION': ['TA_STANDALONE_STRUCTURAL_PASS', 'SG_STANDALONE_STRUCTURAL_PASS',
                                                 'BOTH_EXACT_REPEATABILITY', 'DISTINCT_IDENTITIES',
                                                 'NO_DUPLICATE_DELAY', 'NO_SHARED_MUTABLE_STATE',
                                                 'NO_ROLE_VIOLATION', 'NEW_EXPLICIT_COMPOSITION_AUTHORIZATION']},
          'reference_track': list(BLOCKERS), 'reference_track_modified': False,
          'search_execution_allowed': False, 'composed_implementation_authorized': False,
          'production_authority': False, 'vehicle_activation_allowed': False, 'qualification_allowed': False,
          'sealed_reference_allowed': False, 'sealed_reference': 'NOT_GENERATED',
          'vehicle_status': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED']}


def validate_input_sequence(rows):
  """Single causal timeline; feedback must already be supplied as explicit current measurement."""
  if type(rows) is not tuple or not rows or any(type(row) is not c.TrajectoryInput for row in rows):
    raise ValueError('EXACT_CAUSAL_INPUT_SEQUENCE_REQUIRED')
  for before, after in zip(rows, rows[1:], strict=False):
    # Integer sample indices avoid cumulative binary timestamp drift.
    if round(after.time_s / after.dt_s) != round(before.time_s / before.dt_s) + 1:
      raise ValueError('CONTIGUOUS_FORWARD_TIME_REQUIRED')
    if abs(after.time_s - before.time_s - before.dt_s) > 1e-12:
      raise ValueError('EXACT_100HZ_SEQUENCE_REQUIRED')


def governor_config():
  return {'enabled': False, 'status': 'ALGORITHM_PENDING'}


def probe_environment():
  return {'python': sys.version.split()[0], 'implementation': platform.python_implementation(),
          'machine': platform.machine(), 'scope': 'CURRENT_PURE_PYTHON_FIXTURE_EXECUTION'}


def experiment_policy():
  from openpilot.tools.cyber_autotune import candidate_architecture_policy as policy
  from openpilot.tools.cyber_autotune import candidate_architecture_probe as probe
  return {'matrix': matrix(), 'trajectory_metrics': policy.metrics('TA'), 'smoothness_metrics': policy.metrics('SG'),
          'search_schemas': [search_policy('TA'), search_policy('SG')], 'families': policy.families(),
          'probe_fixture_policy': probe.fixture_policy()}
