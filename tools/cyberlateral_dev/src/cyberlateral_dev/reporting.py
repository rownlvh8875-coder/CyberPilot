"""Deterministic synthetic model results, not physical/candidate evaluation."""
import hashlib
import json
from dataclasses import asdict

from . import __version__
from .simulation import simulate
from .synthetic_catalog import fixed_catalog


def canonical_report(record: object) -> bytes:
    return (json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def catalog_report() -> dict:
    catalog = fixed_catalog()
    fixtures = [{'id': s.id, 'initial_state': asdict(s.initial_state), 'samples': [asdict(x) for x in s.samples]} for s in catalog]
    scenarios = [dict(fixture, result=asdict(simulate(scenario.samples, scenario.initial_state)))
                 for fixture, scenario in zip(fixtures, catalog, strict=True)]
    gates = {'actual_r': None, 'actual_T2': None, 'actual_vehicle_scale': None, 'R_BUDGET': 'UNRESOLVED',
             'STATIC_EVIDENCE_GATE': 'FAIL', 'SOURCE_SCHEMA_UNQUALIFIED': 6000, 'Candidate': 'NO_GO', 'Runtime': 'NO_GO',
             'actual_activation': 'NOT_ALLOWED', 'F70UH': 'NOT_ALLOWED', 'F70V': 'NOT_ALLOWED', 'F71': 'NOT_ALLOWED',
             'D2': 'PERFORMANCE_NOT_EVALUATED', 'F19': 'LEGACY_UNRESOLVED', 'NATIVE_EXACT_REPLAY': 'NOT_PROVEN'}
    return {'schema_version': 1, 'contract_id': 'F70UGZ_R6_OFFLINE_SIMULATION_V1', 'package_version': __version__,
            'scope': 'SYNTHETIC_DEVELOPMENT_ONLY', 'source_scope': 'NOT_CONTROLLER_EXECUTION',
            'fixture_authority': 'DEVELOPMENT_FIXTURE_NOT_POLICY', 'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME',
            'fixture_catalog_sha256': hashlib.sha256(canonical_report(fixtures)).hexdigest(),
            'scenario_count': len(scenarios), 'total_steps': sum(len(s.samples) for s in catalog), 'scenarios': scenarios,
            'gates': gates, 'original_helper_calls': 0, 'Controller_execution': 0, 'Runtime_execution': 0, 'CAN': 0,
            'F61_execution': 0, 'calculator_input_execution': 0, 'r_calculations': 0, 'dt_calculations': 0,
            'actual_production_inputs': 0, 'actual_serializer_execution': 0, 'candidate_performance_evaluation': 0,
            'claim': 'model output only; no independent parity, vehicle safety, physical dynamics or serializer claim'}
