"""Seal public V4 fitting rules; never discover/open private storage."""

import json
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_fitting_policy as f

BASELINE = 'e722342fdd30fcaff80c6d9f94dd7d3465c8a447'
PREFIX = 'empirical-hurdle-stage1-v4-'
ROOT = Path(__file__).resolve().parents[2]
PINS = {'empirical-hurdle-stage1-v4-representation-decision': ('7f63e587e160318312a6d758c5002ea005182334971c3d299282db6a3b8bdaf5',
                                                        '5c1a64fb49aa0c5eda0ee21f1cd9173653647353b82915fb85fcb001ea3cc74b'),
 'empirical-hurdle-stage1-v4-representation-design-contract': ('e720a21539da698eb34bb1b69b71f1e6088aaae678eea2c3432dae57a433796e',
                                                               '01b695d8941298066b61acc341a07f2cbedcd8f1df408754d476744fc3e2a1b8'),
 'empirical-hurdle-stage1-v4-current-feature-contract': ('a7550eef12d82d15515b2d1fcbf2d6e3c7288d754f321426f23782339397991c',
                                                         '5c7ea2975f7ee2881b028c445a5aa6076669ecf87c1989e91a5d582921850ce0'),
 'empirical-hurdle-stage1-v4-training-feasibility': ('f761d41fc5f002fb5f73c8f503921dea6fcd86da54adf1d9dbdbaab8e0327738',
                                                     '13724bf5d68b6d25481b30baeaa8bb41f06f0192e71d076dbcb1c3da86100868'),
 'empirical-hurdle-stage1-v4-parameter-complexity': ('91e8790e2f36d55b32612d23344819ba2c7003766a5a70f8a43ce2d9335373cb',
                                                     'b444353b1a50dd31ee51ca44148994fccc128a0c90970329d505d8f24d863091'),
 'empirical-hurdle-stage1-v4-artifact-lifecycle-review': ('48c098cd667297382deaa11c7a29685d8b843bbe5a1233b8758ff24ce7f76c11',
                                                          '01477fcc8177ec4e69a82b25ba9ee1eac4bfd4e8bd7712e14ba1a4873797ddea'),
 'empirical-hurdle-stage1-v4-future-fitting-requirements-v2': ('0b9f31143b3b5e63924e7e982344ba9d62ce9c34f02f10c492a31c4b0ea942f9',
                                                               '93a5da880cab202bc369f74d6730729f953e4e05eeab68d98560e6391a229be2'),
 'empirical-hurdle-stage1-v4-representation-validation': ('76113e967e152b819de655033db628cacff564fceab70f69b66dbad6944b5ac3',
                                                          '5cef4f2754d0dce517f4a0d89aca17e4a33d6408e8131dd5b2370b67a0635c80'),
 'empirical-hurdle-stage1-v4-causal-state-contract': ('bdcd62d3e2736a96e4118d1da070b5f0c77aa2a23d57a776888594a6a4db686c',
                                                      'd3df9b9c32043aa01df9f95c6adb126ceab76439bc72aac79c4c06fe86096e39'),
 'empirical-hurdle-stage1-v4-rollout-state-contract': ('efd06a9d9109ce326e96ecc29af480007f85cbbccf398f1c0750164ba266bada',
                                                       '1b503078ac9e5adda34f54650099309c7db718c5181ccdca5dc462d11899542f'),
 'empirical-hurdle-fit-cv-results-v1': ('72e0179a96a8885e7ffab57bf1c579ef75536769bc1a03990a007b3b4e2ac272',
                                        '8d7c45a7a97f73918f927b19b0004c309078239b8b8523e1beac08fa6c53f5c4'),
 'empirical-hurdle-fit-cv-authorization-v1': ('54b879120e55c805df5f4094bf04637553bf6faafcfecef69f052d160a29ccb2',
                                              'd93d6bb418a958b998c0308e4ce71a605a4069286029b5539d80b38001a34c6b'),
 'empirical-hurdle-fit-cv-repeatability-v1': ('f734bd6fb3a956e62c883eb24b22d0df0a4626a6ae17a733ca43592f27c00e08',
                                              '60c262b004f253f6de203404520f9edc8ab3d78c0dba51948dd62759003f35dc'),
 'empirical-hurdle-route-cv-contract-v1': ('a40183e88f0ae7b830d353cdce3a692f56111d31a5c27cd1394d205d77e5e6f8',
                                           '9e6bddd4f4d0e3dbe1cd02d7cfe2313a17da5459215f4fa397d42b098b406a4a'),
 'empirical-hurdle-acceptance-gate-v1': ('606d5d3f46677d0107298f8b94e0a6d5a73da62f01db0164c4812a9fa2cccee1',
                                         '1a5198475b7a3843381762078475915a389b2898e950effc171a3df58219ca60'),
 'empirical-hurdle-selection-rule-v1': ('aeb3e51e85039660be702517dfd79e4c932eb72bde0b1a9d9bdc4bbaad36586c',
                                        '9622e7134b56f0c48153cba1a23dd690bdc6d578a433c6f77b34e3f7a3cf70f0'),
 'empirical-hurdle-stage1-v3-external-storage-amendment': ('d59da0af6279c33109513848f9c910a484b352a4a530d47da60af32a17d1239d',
                                                           '5b109186575c4b50b7095a4e99d6028fd8a8f21e4e944fb6ca5ec59d6a4a26e5'),
 'empirical-hurdle-stage1-v3-storage-migration-verification': ('a1b25dd9913c0906a8239af85f09d7db42eb3559b6ed15f408ba14555f5173e4',
                                                               'f147cb4121a5e34f57d663c8fa631ab26805d30c9157515802f7a0cf7529adc9')}
SOURCE_PINS = {'openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_math.py': 'b410b2f0138848faf4e976094a1bd4f3cc3ac44418b54a24310717c6261e0e73',
 'openpilot/tools/cyber_autotune/empirical_s2_ri_fit_cv_math.py': 'a1c1203c8222df067064ff1891aafa82cdafd997338c7ca7687a321c66777f29',
 'openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_gates.py': '7529884d62ee5773bc163a301a9d96c641ff2a2e2e911d3e3e4f0a5c1a6828c2',
 'openpilot/tools/cyber_autotune/empirical_hurdle_v4_state_contract.py': '3a21944b47ee82f4401b6742742924b7458741f17959e3ed2c2d41df67f68793',
 'openpilot/tools/cyber_autotune/empirical_hurdle_v3_io.py': '1fb772477eed0be39653d92247edf31cdfab109069afb6b56fbadbb65cd06b3d'}
FROZEN = 'HURDLE_STAGE1_CONTEXT_CONDITIONAL_LOGISTIC_V4_FITTING_POLICY_FROZEN'
REFERENCE_FILES = (
  'openpilot/tools/cyber_autotune/empirical_hurdle_v4_fitting_policy.py',
  'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_fitting_policy.py',
  'tools/cyberpilot/build_hurdle_v4_fitting_policy.py',
  'docs/cyberpilot/changes/empirical-hurdle-stage1-v4-fitting-policy-freeze.md',
)
VALIDATION_EVIDENCE = {'combined': {'command_argv': ['python',
                               '-B',
                               '-m',
                               'pytest',
                               '-q',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_additional_root_policy.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_causal_analysis.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_causal_dataset.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_causal_policy.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_causal_publication.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_causal_recovery.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_causal_support_guard_v1.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_cross_root_inventory.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_cross_root_publication.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_dataset_v2_inventory.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_dataset_v2_policy.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_dataset_v2_publication.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_export_metadata.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_final_readiness_v2.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_grid_analysis.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_grid_emission.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_grid_publication.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_attribution.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_compressed_storage.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_decision_policy_v2.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_design.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_fit_cv_execution.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_fit_cv_math.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_fitting_policy.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v2_attribution.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v2_execution.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v2_execution_policy.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v2_threshold.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v3.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v3_actual_evidence.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v3_authorization.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v3_execution.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v3_executor_publication.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v3_external_storage.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v3_store.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v3_temporal.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v3_threshold.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_fitting_policy.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_policy_review.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_representation_review.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_review.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_two_context.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_identifiability_contract.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_identifiability_execution.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_identifiability_schema.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_identifiability_v1.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_metadata_copy_variants.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_plant_inventory.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_plant_model.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_plant_policy.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_plant_publication.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_plant_run.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_plant_signals.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_prior_use.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_qlog_reconciliation.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_route_eligibility.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_s2_ri_admission.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_s2_ri_attribution_v2.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_s2_ri_attribution_v2_layout.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_s2_ri_contract.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_s2_ri_execution.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_s2_ri_failure_attribution.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_s2_ri_fit_cv_execution.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_s2_ri_fit_cv_gates.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_s2_ri_fit_cv_math.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_s2_ri_fit_cv_publication.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_s2_ri_fit_cv_rollout.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_s2_ri_fit_cv_store.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_s2_ri_fitting_policy.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_s2_ri_fitting_publication.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_s2_ri_math.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_s2_ri_publication.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_s2_ri_reconstruction.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_salvage_policy.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_salvage_pools.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_salvage_publication.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_salvage_receipts.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_salvage_sources.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_signal_crosscheck.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_signal_policy.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_signal_publication.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_signal_reader.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_signal_run.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_simulator_prior_use.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_source_dependencies.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_source_execution.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_source_fingerprint.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_source_metadata.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_source_policy.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_source_publication.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_stage_a_attribution.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_stage_a_publication.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_stage_a_regime.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_v2_evidence.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_v2_execution.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_v2_generation.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_v2_policy.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_v2_publication.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_v2_signals.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_v3.py',
                               'openpilot/tools/cyber_autotune/tests/test_empirical_v3_publication.py'],
              'command_expansion': 'SHELL_GLOB_test_empirical_STAR_py',
              'exit_code': 0,
              'log_sha256': '901ee03972f6e2ca0868b451e9b8106769658cfa3cc3bf0715469614d15dacd6',
              'passed': 2083},
 'compileall': {'command_argv': ['python', '-B', '-m', 'compileall', '-q', 'tools/cyberpilot', 'openpilot/tools/cyber_autotune'],
                'exit_code': 0,
                'log_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
                'passed': None},
 'diff-check': {'command_argv': ['git', 'diff', '--cached', '--check'],
                'exit_code': 0,
                'log_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
                'passed': None},
 'environment': {'command_argv': ['python', '-B', '-'],
                 'exit_code': 0,
                 'log_sha256': 'c34324245ec415d0958cd81534819f9c5c31d57c898ac0977383f252198b3ed6',
                 'passed': None,
                 'stdin_script_lines': ['import platform, numpy as np, os',
                                        'from openpilot.tools.cyber_autotune import empirical_plant_policy as p',
                                        "assert platform.python_version() == '3.12.13'",
                                        "assert np.__version__ == '2.5.3'",
                                        "assert os.environ['OPENBLAS_NUM_THREADS'] == '1'",
                                        "assert os.environ['OMP_NUM_THREADS'] == '1'",
                                        "expected = '704bde2afe24c22d171cc7d2508517db81b7db455743b2cb0e5de9dda88da7a2'",
                                        "assert p.sha(p.canonical(np.show_config(mode='dicts'))) == expected"]},
 'focused': {'command_argv': ['python', '-B', '-m', 'pytest', '-q', 'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_fitting_policy.py'],
             'exit_code': 0,
             'log_sha256': '5be3c91d51044ffd888b83d0655e96b864f829b53fdb6911f642488a13c28631',
             'passed': 51},
 'full': {'command_argv': ['python', '-B', 'tools/test_runner.py', 'openpilot/tools/cyber_autotune/tests', 'openpilot/selfdrive/controls/tests', '-j4'],
          'exit_code': 0,
          'log_sha256': 'f46da13381fea6bc2d9b578a50ceab456c4a3ba8be8355dabdcc57e055fb7d03',
          'passed': 4942},
 'independent_reviews': {'causal_authority_reproducibility': 'APPROVED',
                         'numerical_statistical': 'APPROVED',
                         'reviewed_numerical_and_test_source_hashes': {'openpilot/tools/cyber_autotune/empirical_hurdle_v4_fitting_policy.py':
        '529c6c14832a18bc18eb51409e1637ca2c003892d62aa883f900c238d59be76f',
                                                                       'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_fitting_policy.py':
        'fd3a4d59cc127e49aa8aa5d63ec0b90d871b084d7d715c89dd24e20c32b34fe5'},
                         'scope': 'POLICY_NUMERICS_AUTHORITY_BODY; OBSERVED_BROADER_CHECKS_RECORDED_SEPARATELY'},
 'json': {'command_argv': ['python', '-B', '-'],
          'exit_code': 0,
          'log_sha256': 'f3b094193c08f722d2e74d149cb1a7ef238556c3daf0a1312e7f48ddf07590fa',
          'passed': 718,
          'stdin_script_lines': ['import json',
                                 'from pathlib import Path',
                                 "files = list(Path('docs/cyberpilot/policies').glob('*.json'))",
                                 "files += list(Path('docs/cyberpilot/changes').glob('*.json'))",
                                 'for path in files: json.loads(path.read_bytes())',
                                 "print('JSON', len(files), 'PASS')"]},
 'lateral': {'command_argv': ['python',
                              '-B',
                              '-m',
                              'unittest',
                              '-q',
                              'openpilot.selfdrive.test.process_replay.test_cyber_lateral_card_replay',
                              'openpilot.selfdrive.test.process_replay.test_cyber_lateral_native_experiment'],
             'exit_code': 0,
             'log_sha256': '14d0d8bfab949eded61d86c5cd53df93ba18a93da46bdf7a821f68b281017f81',
             'passed': 16},
 'prior': {'command_argv': ['python',
                            '-B',
                            '-m',
                            'pytest',
                            '-q',
                            'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v3.py',
                            'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v3_actual_evidence.py',
                            'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v3_authorization.py',
                            'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v3_execution.py',
                            'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v3_executor_publication.py',
                            'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v3_external_storage.py',
                            'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v3_store.py',
                            'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v3_temporal.py',
                            'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v3_threshold.py',
                            'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_review.py',
                            'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_two_context.py',
                            'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_policy_review.py',
                            'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_representation_review.py'],
           'exit_code': 0,
           'log_sha256': '530f849179c9b0d86727b1d1f73a8455e62aa7995fe6f8a0ab97588359a42661',
           'passed': 264},
 'publication': {'command_argv': ['python', '-B', 'tools/cyberpilot/check_publication.py', '--base', 'origin/main', '--json'],
                 'exit_code': 0,
                 'log_sha256': '37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570',
                 'passed': None},
 'ruff': {'command_argv': ['ruff',
                           'check',
                           'tools/cyberpilot',
                           'openpilot/tools/cyber_autotune',
                           'openpilot/selfdrive/controls/lib/cyber_lateral',
                           'openpilot/selfdrive/controls/lib/cyber_long',
                           'openpilot/selfdrive/controls/tests/test_cyber_lateral.py',
                           'openpilot/selfdrive/controls/tests/test_cyber_lateral_command_domain.py',
                           'openpilot/selfdrive/controls/tests/test_cyber_lateral_integration.py',
                           'openpilot/selfdrive/controls/tests/test_cyber_lateral_jerk_observer.py',
                           'openpilot/selfdrive/controls/tests/test_cyber_lateral_metrics.py',
                           'openpilot/selfdrive/controls/tests/test_cyber_lateral_model_coordinates.py',
                           'openpilot/selfdrive/controls/tests/test_cyber_lateral_optimizer.py',
                           'openpilot/selfdrive/controls/tests/test_cyber_lateral_params.py',
                           'openpilot/selfdrive/controls/tests/test_cyber_lateral_path_observer.py',
                           'openpilot/selfdrive/controls/tests/test_cyber_lateral_path_tracking.py',
                           'openpilot/selfdrive/controls/tests/test_cyber_long.py',
                           'openpilot/selfdrive/controls/tests/test_cyber_long_boundary.py',
                           'openpilot/selfdrive/controls/tests/test_cyber_long_feedback.py',
                           'openpilot/selfdrive/controls/tests/test_cyber_long_integration.py',
                           'openpilot/selfdrive/controls/tests/test_cyber_long_params.py',
                           'openpilot/selfdrive/test/process_replay/cyber_lateral_card.py',
                           'openpilot/selfdrive/test/process_replay/cyber_lateral_native_experiment.py',
                           'openpilot/selfdrive/test/process_replay/cyber_lateral_replay.py',
                           'openpilot/selfdrive/test/process_replay/test_cyber_lateral_card_replay.py',
                           'openpilot/selfdrive/test/process_replay/test_cyber_lateral_native_experiment.py'],
          'exit_code': 0,
          'log_sha256': '82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18',
          'passed': None},
 'scons': {'command_argv': ['scons', '-u', '-j2'],
           'exit_code': 0,
           'log_sha256': '870f4ab033b2c85dbd11bd689b1dedd563221b66b4fdd762fa7cd9a0cf82f056',
           'passed': None},
 'source_stability': {'after_sha256': '0444439021b5ba2a382dd91cad45ebccd68d8d5e8f0c3f2ea43d9555c77cce1a',
                      'before_sha256': '0444439021b5ba2a382dd91cad45ebccd68d8d5e8f0c3f2ea43d9555c77cce1a',
                      'equal': True,
                      'exit_code': 0}}


def locked_inputs():
  rows = {}
  try:
    for name, (file_sha, receipt_sha) in PINS.items():
      raw = (p.PUBLIC / (name + '.json')).read_bytes()
      f.need(p.sha(raw) == file_sha)
      row = p.verify(json.loads(raw))
      f.need(row['receipt_sha256'] == receipt_sha)
      rows[name] = row
    for path, sha in SOURCE_PINS.items():
      f.need(p.sha((ROOT / path).read_bytes()) == sha)
  except (ValueError, OSError, KeyError, TypeError) as error:
    raise ValueError('V4_FITTING_POLICY_INPUT_CONFLICT') from error
  return rows


def job_bindings(source):
  expected = [(c, fold) for c in f.old.CANDIDATES for fold in ('FOLD_A', 'FOLD_B')]
  f.need([(j['candidate_id'], j['fold']) for j in source['jobs']] == expected)
  out = []
  for j in source['jobs']:
    _, length = f.old.parameters(j['candidate_id'])
    nominal = 2 * length + 3
    f.need(j['stage1']['nominal_columns'] == j['stage1']['effective_columns'] == nominal)
    f.need(j['stage1']['constant_columns'] == 0)
    f.need(j['stage1']['train_anchor_sha256'] == j['train_anchor_sha256'])
    f.need(j['stage2']['count'] == j['train_move_count'])
    fields = ('model_receipt_sha256', 'coefficient_sha256', 'normalizer_receipt_sha256', 'train_anchor_sha256',
              'count', 'nominal_columns', 'effective_columns', 'rank', 'constant_columns')
    out.append({**{key: j[key] for key in ('candidate_id', 'fold', 'receipt_sha256', 'train_route', 'development_route',
      'train_count', 'train_move_count', 'train_static_count', 'train_anchor_sha256')},
      'stages': {stage: {key: j[stage][key] for key in fields} for stage in ('stage1', 'stage2')},
      'one_step_anchor': {key: j['one_step'][key] for key in ('count', 'anchor_sha256')},
      'rollout_anchors': {str(h): {key: j['rollout'][str(h)]['overall'][key] for key in ('count', 'anchor_sha256')}
                          for h in f.old.HORIZONS},
      'population_receipts': j['population_receipts'], 'v1_threshold_receipt_sha256': j['threshold']['receipt_sha256']})
  return out


def selection_order_proof():
  candidates = f.old.CANDIDATES
  def key(candidate, multiplier):
    d, length = f.old.parameters(candidate)
    return multiplier * (2 * length + 3), length, d, candidate
  for a in candidates:
    for b in candidates:
      f.need((key(a, 2) < key(b, 2)) == (key(a, 3) < key(b, 3)))
      f.need((key(a, 2) == key(b, 2)) == (key(a, 3) == key(b, 3)))
  return {'pairs_verified': len(candidates) ** 2, 'historical_proxy': '2P', 'actual_v4_nominal': '3P',
          'actual_v4_generic_identifiable_upper_including_stage2': '3P-1',
          'proof': 'BOTH_STRICTLY_INCREASING_IN_L_AND_INDEPENDENT_OF_d; SAME_PRECEDING_METRICS_AND_L_d_ID_KEYS',
          'scope': 'EXACT_FROZEN_16_STRUCTURES_ONLY', 'selector_code_changed': False,
          'historical_proxy_is_not_reported_as_actual_v4_count': True}


def build():
  inputs = locked_inputs()
  def get(name):
    return inputs[PREFIX + name]
  architecture = get('representation-design-contract')
  f.need(architecture['status'] == 'HURDLE_STAGE1_V4_REPRESENTATION_DESIGN_FROZEN')
  f.need(get('representation-decision')['selected_option'] == 'C')
  source = inputs['empirical-hurdle-fit-cv-results-v1']
  f.need(source['private_manifest_sha256'] == 'c4de3955c12cd0d9721d4c7c1519da53b4d80f80be0c05e142047853a7b217a6')
  jobs = job_bindings(source)
  auth = inputs['empirical-hurdle-fit-cv-authorization-v1']
  gate = inputs['empirical-hurdle-acceptance-gate-v1']
  selector = inputs['empirical-hurdle-selection-rule-v1']
  f.need(len(gate['clauses']) == 32 and selector['reductions']['TOTAL_NOMINAL_PARAMETER_COUNT'] == '2*(2*L+3)_THRESHOLD_SEPARATE')
  common = {
    'schema': 'HURDLE_STAGE1_CONTEXT_CONDITIONAL_LOGISTIC_V4_FITTING_POLICY_V1',
    'baseline': BASELINE, 'family': architecture['family'], 'scope': 'PUBLIC_POLICY_AND_SYNTHETIC_REFERENCE_ONLY',
    'architecture': 'FROZEN', 'fitting_policy': 'FROZEN', 'actual_execution_authorized': False,
    'private_executor_implemented': False, 'actual_model': 'NOT_FIT', 'actual_coefficients': 'NOT_GENERATED',
    'operation_counter_scope': 'ACTUAL_EMPIRICAL_OPERATIONS_ONLY; AUTHORIZED_SYNTHETIC_TEST_OPERATIONS_SEPARATE',
    'private_numeric_array_opens': 0, 'model_fit_calls': 0, 'normalizer_fit_calls': 0, 'threshold_search_calls': 0,
    'raw_log_openings': 0, 'qlog_openings': 0, 'holdout_openings': 0, 'source_writes': 0,
    'v4': dict.fromkeys(('fitting', 'cv', 'development', 'rollout', 'selection', 'performance'), 'NOT_RUN'),
    'holdout': 'CLOSED', 'opening_count': 0, 'holdout_discovery': 0, 'pooled_refit': 'NOT_AUTHORIZED', 'vehicle_authority': 'NONE',
    'historical_states_preserved': architecture['historical_states_preserved'],
    'prior_review_states_preserved': architecture['prior_review_states_preserved'],
    'preserved_authority_states': architecture['preserved_authority_states'],
    'hugging_face': {'status': 'HUGGING_FACE_NOT_REQUIRED_FOR_MODEL_SIZE', 'setup': 'NOT_RUN', 'login': 'NOT_RUN',
                    'repo': 'NOT_CREATED', 'upload': 0, 'download': 0},
  }
  out = {}
  def add(name, body):
    out[PREFIX + name + '.json'] = p.seal({**common, 'component': name, **body})
  add('fitting-policy-inputs', {
    'input_lock': {name + '.json': {'file_sha256': pair[0], 'receipt_sha256': pair[1]} for name, pair in PINS.items()},
    'source_lock': SOURCE_PINS, 'reference_source_hashes': {name: p.sha((ROOT / name).read_bytes()) for name in REFERENCE_FILES},
    'input_reconciliation': 'PASS',
    'architecture_receipt_sha256': architecture['receipt_sha256'], 'public_v1_jobs': jobs,
    'job_binding_sha256': p.sha(p.canonical(jobs)), 'private_payload_verification_now': 'NOT_RUN',
    'successful_v1_manifest_sha256': source['private_manifest_sha256'],
    'historical_v1_authorization_sha256': auth['authorization_sha256'],
    'historical_v1_repeatability': inputs['empirical-hurdle-fit-cv-repeatability-v1']['repeatability'],
    'historical_metadata_is_not_new_execution_authorization': True})
  add('normalization-policy', {
    'status': 'V4_SHARED_V1_STAGE1_NORMALIZER_REUSE_FROZEN',
    'policy': 'REUSE_BYTE_IDENTICAL_V1_STAGE1_TRAIN_NORMALIZER_SAME_CANDIDATE_FOLD_BOTH_HEADS',
    'context_normalizer': 'CONTEXT_LOCAL_NORMALIZER_REFIT_NOT_AUTHORIZED', 'mean_std_fit': False,
    'normalizer_identity': 'PUBLIC_RECEIPT_PLUS_FUTURE_PRIVATE_MANIFEST_ARRAY_CONTENT_VERIFICATION',
    'source_public_full_nominal_effective_jobs': 32, 'source_public_no_constant_columns_jobs': 32,
    'future_content_guard': 'MATCH_PINNED_RECEIPT_ARRAY_SHAS_AND_EFFECTIVE_arange_P; ALL_CONSTANT_FLAGS_FALSE; RETAINED_NONINTERCEPT_STD_POSITIVE',
    'source_transform': 'empirical_s2_ri_fit_cv_math.transform',
    'real_affine_coefficient_map': 'beta_j=w_j*std_j; beta_0=w_0+SUM_j>0(w_j*mean_j)',
    'static_delta_absorption': 'beta0_static=beta0+beta_delta*((0-mean_delta)/std_delta); DROP_DELTA',
    'function_class_proof': 'INVERTIBLE_AFFINE_MAP_ON_ALL_NONINTERCEPT_COLUMNS_IN_PINNED32_SOURCE_JOBS; STATIC_STRUCTURAL_COLUMN_ABSORBED',
    'generic_legacy_constant_example': 'ONLY_RETAINED_CLASS_OR_TRAIN_SUPPORT_EQUIVALENCE; NOT_UNRESTRICTED_OFF_SUPPORT_RAW_CLASS',
    'floating_evaluation_byte_equivalence_claim': False, 'new_normalization_parameters': 0,
    'failure': 'V4_NORMALIZER_IDENTITY_CONFLICT'})
  add('identifiable-basis-policy', {
    'status': 'V4_STATIC_STRUCTURAL_DELTA_GAUGE_FROZEN', 'P': '2L+3', 'raw_z_column': 'P-3=2L',
    'context_definition': 'RAW_PRIOR_SOURCE_GRID_DELTA_NE_ZERO_BEFORE_NORMALIZATION',
    'static': 'V1_EFFECTIVE_RAW_COLUMN_INDICES_EXCLUDING_P-3', 'move': 'ALL_V1_EFFECTIVE_RAW_COLUMN_INDICES',
    'order': 'ORIGINAL_ASCENDING_FEATURE_INDEX; INTERCEPT_0_RETAINED',
    'additional_context_constant_or_dependent_columns': 'NO_AUTO_DROP; FAIL_CLOSED',
    'actual_pinned_source_masks': {str(length): {'static': [j for j in range(2 * length + 3) if j != 2 * length],
                                                'move': list(range(2 * length + 3))} for length in (1, 5, 15, 45)},
    'raw_nominal_reconstruction': 'REMOVED_NORMALIZED_DELTA_COEFFICIENT_ZERO_WITH_INTERCEPT_ABSORPTION',
    'no_later_arbitrary_gauge_choice': True})
  add('support-rank-policy', {
    'support_per_head': {'positive_minimum': f.SUPPORT, 'negative_minimum': f.SUPPORT, 'rows': 'STRICTLY_GREATER_THAN_EFFECTIVE_COLUMNS'},
    'support_basis': 'HISTORICAL_SUPPORT_FLOOR_REUSED_NOT_NEW_HYPERPARAMETER_NOT_STATISTICAL_SUFFICIENCY',
    'numerical_rank': {'singular': 'FLOAT64_SVD_DESCENDING', 'tolerance': 'sigma_max*max(n_rows,n_cols)*finfo(float64).eps',
      'comparison': 'sigma>tol', 'required': 'rank==n_cols', 'environment': 'PINNED_NUMPY_BLAS'},
    'exact_rank': 'ALSO_REQUIRE_NONZERO_p_BY_p_ROW_MINOR_VERIFIED_OVER_EXACT_BINARY64_RATIONAL_ENTRIES',
    'witness_row_selection': 'CERTIFICATION_ONLY_ALL_ORIGINAL_ROWS_REMAIN_IN_FIT',
    'why_exact_rank_added': 'NUMERICAL_RANK_IS_NOT_A_MATHEMATICAL_EXACT_RANK_PROOF; NO_NEW_TOLERANCE_OR_PARAMETER',
    'failure': 'V4_STAGE1_HEAD_RANK_FAILURE', 'forbidden': ['PSEUDOINVERSE', 'RIDGE', 'EXTRA_COLUMN_DROP', 'OLD_MODEL_FALLBACK']})
  add('separation-policy', {
    'policy': 'UNREGULARIZED_FINITE_MLE_ONLY', 'signed_design': 'A=diag(2*y-1)*X_EFFECTIVE',
    'separation': 'EXISTS_b: A*b>=0_ALL_ROWS_AND_A*b>0_SOME_ROW',
    'bounded_lp': 'MAX_1^T*A*b_SUBJECT_A*b>=0_AND_norm1(b)<=1',
    'present_certificate': 'EXACT_FEASIBLE_b_WITH_POSITIVE_OBJECTIVE; POSITIVE_OBJECTIVE_SUFFICES_NO_OPTIMUM_NEEDED',
    'absent_certificate': 'EXACT_RATIONAL_lambda_i>=1_ALL_ROWS_AND_A^T*lambda=0',
    'dual_proof': 'q=lambda-1>=0; mu=0; |A^T*(q+1)|<=mu; PRIMAL_b=0_AND_DUAL_ZERO_CERTIFY_OPTIMUM_0',
    'number_semantics': 'EACH_FINITE_BINARY64_X_ENTRY_AS_EXACT_INTEGER_RATIO; RATIONAL_WITNESSES; NO_DECIMAL_ROUNDING_NO_EPSILON',
    'binding': 'EXACT_EFFECTIVE_MATRIX_CONTENT_DTYPE_SHAPE_ROW_ORDER_LABELS_BASIS_AND_SOURCE_IDENTITIES',
    'certificate_residual': 'EXACT_ZERO_REQUIRED; SMALL_NONZERO_NOT_ACCEPTED',
    'complete_or_quasi': 'BOTH_FAIL; ZERO_MARGIN_WITNESS_ALONE_NOT_A_QUASI_CLASSIFICATION_PROOF',
    'generator': 'LARGE_DATA_CERTIFICATE_GENERATOR_NOT_IMPLEMENTED_REQUIRED_BEFORE_EXECUTOR_READINESS',
    'current_reference': 'SYNTHETIC_EXACT_PROOF_VERIFIER_WITH_SUPPLIED_WITNESSES_NO_LP_SOLVER',
    'dependency_added': False,
    'unknown': 'SEPARATION_CERTIFICATE_INCONCLUSIVE_FAIL_CLOSED',
    'heuristics_forbidden': ['COEFFICIENT_CAP', 'SMALL_GRADIENT', 'ITERATION_COUNT', 'HESSIAN_CONDITION', 'LOOKS_CONVERGED']})
  add('optimizer-policy', {
    'status': 'V4_INDEPENDENT_HEAD_UNREGULARIZED_NEWTON_POLICY_FROZEN',
    'source': 'empirical_hurdle_fit_cv_math.newton', 'loss': 'UNWEIGHTED_UNREGULARIZED_LOCAL_HEAD_MEAN_LOG_LOSS',
    'equation': 'mean(logaddexp(0,X*beta)-y*(X*beta))', 'initialization': 'ZERO_FLOAT64',
    'gradient': 'X.T@(p-y)/n_head', 'hessian': 'X.T@((p*(1-p))[:,None]*X)/n_head',
    'linear_solver': 'numpy.linalg.solve', 'direction': 'solve(H,g)', 'update': 'beta-alpha*direction',
    'max_accepted_updates': f.MAX_UPDATES, 'maxabs_local_mean_gradient_tolerance': f.GRADIENT_TOLERANCE,
    'comparison': '<=', 'armijo_c': f.ARMIJO_C, 'alpha': '0.5**j', 'trial_exponents': list(f.TRIAL_EXPONENTS),
    'armijo': 'trial_loss<=current_loss-c*alpha*dot(g,direction)',
    'stop_order': 'TEST_GRADIENT_FIRST; IF_NOT_CONVERGED_AND_UPDATES>=100_FAIL; THEN_SOLVE_AND_TRIALS',
    'global_weighted_head_gradient': 'FORBIDDEN', 'separation_certificate': 'REQUIRED_BEFORE_NEWTON',
    'exact_mle_parameter_error_certificate': False,
    'no_convergence_guarantee_within_budget': True,
    'failures': ['NONFINITE', 'SINGULAR_HESSIAN', 'NONPOSITIVE_SLOPE', 'NO_ARMIJO_TRIAL', 'MOVE_GATE_NONCONVERGENCE']})
  add('regularization-policy', {
    'regularization': 'NONE', 'lambda': 'NOT_APPLICABLE', 'class_weighting': 'NONE',
    'oversampling': False, 'resampling': False, 'synthetic_positive_generation_for_empirical_fit': False,
    'coefficient_clipping': False, 'pseudocount': False,
    'justification': 'V1_UNREGULARIZED_CONTINUITY_NO_NEW_TUNABLE_LAMBDA; EXISTENCE_RANK_SEPARATION_CERTIFIED_SEPARATELY',
    'forbidden_fallback': ['L1', 'L2', 'ELASTIC_NET', 'FIRTH', 'RIDGE', 'V1_MODEL'],
    'balanced_accuracy_applies_to': 'THRESHOLD_SELECTION_ONLY_NOT_LOSS'})
  add('head-fitting-policy', {
    'policy': 'FIT_STATIC_AND_MOVE_HEADS_INDEPENDENTLY', 'execution_order': ['STATIC', 'MOVE'],
    'rows': 'ORIGINAL_TRAIN_ORDER_FILTERED_BY_RAW_z', 'head_local_normalizer_fit': False,
    'preconditions_each_head': ['SOURCE_MODEL_NORMALIZER_ANCHOR_IDENTITIES', 'SUPPORT', 'NUMERICAL_AND_EXACT_RANK', 'EXACT_NO_SEPARATION'],
    'likelihood_equivalence': 'SUM_NLL_SEPARATES; GLOBAL_ARGMIN_PRODUCT_OF_HEAD_ARGMINS_IF_EXIST_UNCOUPLED; LOCAL_MEAN_POSITIVE_WEIGHTS_SAME_MINIMIZERS',
    'unique_finite_real_mle': 'FINITE_INPUTS_EXACT_FULL_COLUMN_RANK_AND_EXACT_NO_COMPLETE_QUASI_SEPARATION',
    'optimizer_byte_equivalence_to_joint_block': False,
    'non_equivalence_reasons': ['LOCAL_MEAN_GRADIENT_SCALE', 'REDUCTION_ORDER', 'ARMIJO_PATH', 'REPARAMETERIZATION'],
    'combined_probability': 'ONE_ORIGINAL_ROW_ORDER_VECTOR; z=0_STATIC_HEAD_ELSE_z=1_MOVE_HEAD',
    'stage2': 'REUSE_BYTE_IDENTICAL_V1_STAGE2_COEFFICIENTS_AND_MOVE_ONLY_TRAIN_NORMALIZER_SAME_CANDIDATE_FOLD',
    'stage2_train_anchor': 'PIN_TRUE_MOVE_SUBSET_SEPARATELY_FROM_STAGE1_PARENT_TRAIN',
    'causal_contract_receipts': {name: get(name)['receipt_sha256'] for name in ('causal-state-contract', 'rollout-state-contract')},
    'causal_rules': {key: architecture[key] for key in ('one_step_z', 'rollout_initial_z', 'rollout_recursive_z',
      'initial_history_array_indices', 'predecessor_admission', 'boundaries', 'gate_is_not_state', 'future_truth_use')}})
  add('threshold-policy', {
    'status': 'V4_COMBINED_SCORE_GLOBAL_TRAIN_BA_THRESHOLD_FROZEN',
    'source': 'empirical_hurdle_fit_cv_math.threshold', 'population': 'COMBINED_ORIGINAL_ORDER_TRAIN_ONLY',
    'cutoff_count': 1, 'candidate_set': 'SORTED_UNIQUE_UNION_{0.0,1.0}_ALL_FINITE_COMBINED_TRAIN_PROBABILITIES',
    'decision': 'MOVE_IFF_p>threshold; EQUALITY_STATIC', 'epsilon': 0, 'rounded_probabilities': False,
    'objective': 'MAX_PYTHON_INT_BA_NUM=TP*N_negative+TN*N_positive',
    'tie_order': ['MAX_BA_NUM', 'MAX_TN', 'MAX_THRESHOLD'], 'sort': 'STABLE_NUMPY_ARGSORT_PLUS_EXACT_EQUAL_SCORE_GROUPS',
    'justification': 'PREDECLARED_V1_CLASSIFICATION_POLICY_NO_NEW_TARGET_OR_STAGE2_TASK_COUPLING_ISOLATES_REPRESENTATION_CHANGE',
    'old_family_closure': 'OLD_FIXED_SCORE_ONLY_NOT_NEW_REPRESENTATION_SINGLE_THRESHOLD',
    'not_promised': 'NO_GLOBAL_TRANSFER_INVARIANCE_NO_ALL_STATIC_COLLAPSE_PREVENTION_OR_REAL_GAIN_GUARANTEE',
    'endpoint_limit': 'NO_ALL_MOVE_CANDIDATE_WHEN_ANY_p=0; NO_NEGATIVE_OR_NEXTAFTER_CUTOFF_ADDED',
    'stage2_during_threshold_fit': 'NOT_USED', 'development_during_threshold_fit': 'FORBIDDEN',
    'fallback': 'NONE; NO_0_5_V2_V3_PER_HEAD_F1_RECALL_TARGET_OR_OTHER_THRESHOLD'})
  add('failure-policy', {
    'job_failure': 'V4_STAGE1_FIT_FAILED_CLOSED',
    'causes': ['V4_NORMALIZER_IDENTITY_CONFLICT', 'V4_STAGE1_HEAD_SUPPORT_FAILURE', 'V4_STAGE1_HEAD_RANK_FAILURE',
      'SEPARATION_PRESENT', 'SEPARATION_CERTIFICATE_INCONCLUSIVE', 'MOVE_GATE_NONCONVERGENCE', 'MOVE_GATE_NUMERICAL_FAILURE',
      'MOVE_GATE_LINE_SEARCH_FAILURE', 'V4_STAGE1_NUMERICAL_FAILURE'],
    'job_accounting': 'ALL_16_CANDIDATES_X_2_FOLDS_RECORD_COMPLETE_OR_FAILED; NEVER_SILENTLY_DROP',
    'candidate_admissible': 'BOTH_FOLDS_FULL_GATE_AND_ALL_FITTING_REQUIREMENTS',
    'partial_head_reuse_or_promotion': False, 'one_head_or_global_head_fallback': False,
    'regularization_or_threshold_fallback': False,
    'final_gate': {'receipt_sha256': gate['receipt_sha256'], 'clauses': gate['clauses'], 'both_folds_required': True,
      'metric_projection_rollout_semantics': 'UNCHANGED_V1', 'epsilon': 0},
    'selection': {'receipt_sha256': selector['receipt_sha256'], 'source': 'empirical_hurdle_fit_cv_gates.select/selection_key',
      'ascending_keys': selector['ascending_keys'], 'no_near_winner': True, 'complexity_binding': selection_order_proof()}})
  env = {'python': '3.12.13', 'numpy': '2.5.3', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
         'blas_build_identity_sha256': auth['blas_build_identity_sha256'], 'dtype': 'float64', 'order': 'C', 'rng': 'NONE'}
  add('artifact-identity-policy', {
    'environment': env, 'private_build_metadata_publication': 'FORBIDDEN',
    'head_payload_fields': ['CANDIDATE_FOLD_CONTEXT', 'ARCHITECTURE_POLICY_RECEIPTS', 'SOURCE_TRAIN_MANIFEST_ANCHORS_ROW_ORDER',
      'V1_NORMALIZER_RECEIPT_AND_CONTENT_HASHES', 'EXACT_BASIS_RAW_AND_TRANSFORMED_INDICES_FEATURE_NAMES',
      'SUPPORT_NUMERIC_SINGULAR_VALUES_EXACT_RANK_MINOR', 'EXACT_SEPARATION_CERTIFICATE_RECEIPT_AND_WITNESSES',
      'FLOAT64_COEFFICIENTS_AND_ARRAY_SHA', 'CONVERGENCE_RECEIPT', 'COEFFICIENT_IDENTITY'],
    'coefficient_publication': 'FORBIDDEN', 'normalizer_value_publication': 'FORBIDDEN',
    'public': 'COUNTS_STATUSES_HASHES_CONVERGENCE_AGGREGATES_RECEIPTS_ONLY',
    'two_runs': 'INDEPENDENT_E_OUTPUT_ROOTS_NO_RUN1_COEFFICIENT_THRESHOLD_PREDICTION_CACHE_REUSE',
    'byte_exact': ['SOURCE_ANCHORS_MODELS_NORMALIZER_REFERENCES', 'BASIS_MASKS_RANK_AND_SEPARATION_CERTIFICATES',
      'COEFFICIENTS_CONVERGENCE', 'COMBINED_PROBABILITIES_THRESHOLD', 'FUTURE_DEV_ROLLOUT_GATES_METRICS',
      'FINAL_GATE_SELECTION_AGGREGATES', 'LOGICAL_MANIFESTS_AND_PAYLOAD_HASHES'],
    'repeatability_failure': 'V4_EXACT_REPEATABILITY_FAILURE',
    'certificate_generator_identity': 'DETERMINISTIC_GENERATOR_FULL_SOURCE_ENVIRONMENT_ALGORITHM_AND_VERSION_MUST_BE_FROZEN_BEFORE_EXECUTION',
    'rational_serialization': 'REDUCED_SIGNED_NUMERATOR_POSITIVE_DENOMINATOR_DECIMAL_STRINGS_CANONICAL_SORTED_JSON',
    'nonunique_certificate_choice': 'GENERATOR_MUST_BE_DETERMINISTIC; PROOF_BYTES_ROW_ORDER_AND_GENERATOR_IDENTITY_IN_TWO_RUN_COMPARISON',
    'compression': 'C_ORDER_NPY_GZIP_LEVEL1_MTIME0_FILENAME_EMPTY; PIN_ZLIB_ENVIRONMENT_BEFORE_EXECUTION',
    'resume': 'VERIFY_ONLY_SAVED_HASHED_FINAL_ARTIFACTS_NO_SOURCE_NUMERIC_LOAD_OR_RECOMPUTE',
    'resume_traps': ['SOURCE_MODEL_LOADER', 'HEAD_FITTER', 'NORMALIZER_FITTER', 'PREDICTOR', 'THRESHOLD_SELECTOR',
      'DEVELOPMENT', 'ROLLOUT', 'SCORER', 'CANDIDATE_SELECTOR'],
    'storage': 'E_EXTERNAL_SSD_ONLY_EXPLICIT_VERIFIED_ROOTS_NO_C_D_NO_BROAD_SCAN',
    'storage_pattern_receipt': inputs['empirical-hurdle-stage1-v3-external-storage-amendment']['receipt_sha256'],
    'historical_storage_receipt_is_v4_execution_authority': False,
    'future_authorization': 'SEPARATE_TRUSTED_HEAD_SOURCE_MODEL_ENVIRONMENT_E_VOLUME_CAPACITY_RECEIPT_REQUIRED',
    'actual_model_artifact_generated': False})
  policy_components = list(out)
  add('fitting-policy-decision', {
    'status': FROZEN, 'architecture_receipt_sha256': architecture['receipt_sha256'],
    'component_receipts': {name: out[name]['receipt_sha256'] for name in policy_components},
    'reason': 'HISTORICAL_NORMALIZER_SOLVER_THRESHOLD_CONTINUITY_WITH_STRUCTURAL_GAUGE_AND_EXACT_FINITE_MLE_PRECONDITIONS',
    'no_new_tunable_hyperparameters': True, 'science_optimality_or_performance_claim': False,
    'normalization': 'FROZEN', 'basis': 'FROZEN', 'support_rank': 'FROZEN', 'separation': 'FROZEN',
    'regularization': 'FROZEN_NONE', 'optimizer': 'FROZEN', 'threshold': 'FROZEN_GLOBAL_V1_BA',
    'stage2': 'UNCHANGED_BYTE_REUSE', 'actual_execution_ready': False})
  add('fitting-policy-readiness', {
    'status': FROZEN, 'policy_decision_receipt_sha256': out[PREFIX + 'fitting-policy-decision.json']['receipt_sha256'],
    'policy_ready': True, 'actual_private_executor_ready': False,
    'blockers_before_private_executor_readiness': ['LARGE_SCALE_EXACT_CERTIFICATE_GENERATOR_AND_VERIFIER_IMPLEMENTATION',
      'PRIVATE_AUTHORIZED_INPUT_MODEL_ANCHOR_IDENTITY_PREFLIGHT', 'E_VOLUME_CAPACITY_STORAGE_IMPLEMENTATION',
      'ACTUAL_EXECUTOR_SYNTHETIC_REVIEW_REPEATABILITY_TRAPPED_RESUME'],
    'next_increment': 'SEPARATE_V4_EXECUTOR_IMPLEMENTATION_REVIEW_NOT_ACTUAL_FIT',
    'auto_advance': False})
  add('fitting-policy-validation', {
    'status': 'HURDLE_STAGE1_V4_FITTING_POLICY_REVIEW_COMPLETE',
    'checks': {'new_focused': {'passed': 51}, 'prior_v3_v4_focused': {'passed': 264},
      'combined_empirical': {'passed': 2083}, 'full_autotune_controls': {'passed': 4942}, 'lateral_replay': {'passed': 16},
      'json': {'passed': 718}, 'ruff': 'PASS', 'compileall': 'PASS', 'publication_privacy_authority': 'PASS',
      'git_diff_check': 'PASS', 'scons': 'PASS', 'numerical_statistical_review': 'APPROVED', 'causal_authority_review': 'APPROVED'},
    'synthetic_operations': {'head_fitting': 'EXECUTED_SYNTHETIC_ONLY', 'threshold_sweeps': 'EXECUTED_SYNTHETIC_ONLY',
      'exact_certificate_verification': 'PASS_SUPPLIED_SYNTHETIC_WITNESSES', 'actual_large_certificate_generation': 'NOT_IMPLEMENTED'},
    'synthetic_two_runs': 'BYTE_EXACT_RESULT_IDENTITY_PASS_NOT_ACTUAL_MODEL_REPEATABILITY',
    'observed_validation_evidence': VALIDATION_EVIDENCE,
    'environment': env, 'legacy_d_fixture_isolation': 'PRIVATE_TMPFS_MOUNT_NAMESPACE_NO_GLOBAL_STORAGE_GUARD_CHANGE'})
  return out


def main():
  for name, row in build().items():
    p.persist(p.PUBLIC / name, row)
  print('SEALED_14_FITTING_POLICY_ARTIFACTS_NO_PRIVATE_ACCESS')


if __name__ == '__main__':
  main()
