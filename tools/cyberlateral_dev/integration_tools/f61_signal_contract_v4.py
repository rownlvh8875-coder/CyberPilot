"""Frozen data only; no F61 implementation or shared runtime validator."""

CONTRACT_ID = 'F70UGHR_REQUEST_TO_REQUEST_EXACT_SUBSET_V4'
COMMITS = ('6ca11a4aea8223ebfebb1140bd8094ef1b3c5b90', '1dac44b22426711bdec4aa6ed79f0c8d55be1241')
F61_SHA = 'f343b0edd5578348c570692f05d655dee8e2b1555492a1d99b218d3f81fab035'
STAGE = 'REQUESTED_NORMALIZED'
TIME_SOURCE = 'CAR_CONTROLS_UPDATE_NOW_NANOS_ARGUMENT'
DOMAINS = ('LIVE_MONOTONIC_NS', 'REPLAY_RECORDED_CAN_NS')
FIXTURE = 'PUBLIC_SYNTHETIC_SOURCE_FIXTURE'
CONTROLLER_PATH = 'opendbc_repo/opendbc/car/hyundai/carcontroller.py'
CONTROLLER_SYMBOL = 'CarController.update::CC.actuators.torque'
TOP_KEYS = (
    'schema_version',
    'contract_id',
    'mode',
    'source_identity',
    'current_production_value',
    'previous_production_state',
    'current_sample_time_ns',
    'previous_sample_time_ns',
    'static_context_reference',
    'reset_between_samples',
)
SNAPSHOT_KEYS = (
    'value',
    'dtype',
    'unit',
    'stage_id',
    'source_commit',
    'control_mode',
    'clock_domain',
    'epoch_id',
    'sequence',
    'active',
    'override',
    'time_source',
    'provenance',
)
SOURCE_KEYS = ('production_repository', 'production_commit', 'controller_path', 'controller_symbol', 'f61_source_sha256')
CONTEXT_KEYS = ('kind', 'fixture_id', 'vehicle_context', 'actual_vehicle_gate')
PROJECTION_KIND = 'PARTIAL_ADAPTER_SIGNAL_PROJECTION_NOT_CONSTRUCTOR_ARGS'
