"""Complete decoded synthetic worker doubles; declarations, not native custody."""


def complete_claims(data, mode):
    from integration_tools import fault_reference, fixed_model_reference, sequence_reference

    references = {'R22': fixed_model_reference.REFERENCE_SHA256, 'R23': sequence_reference.REFERENCE_SHA256,
                  'R24': fault_reference.REFERENCE_SHA256}
    scopes = {'R22': 'FIVE_FIXED_SYNTHETIC_SINGLE_STEPS_NOT_ACTUAL_OR_CHAIN',
              'R23': 'FOUR_FIXED_SYNTHETIC_NATIVE_MODEL_STEPS_NOT_ACTUAL_HISTORY',
              'R24': 'NINETY_NINE_FIXED_SYNTHETIC_FAULT_RESET_STEPS_NOT_ACTUAL_HISTORY'}
    data.update(schema_version=1, scope=scopes[mode], package_version='0.3.0', model_reference_sha256=references[mode],
                actual_call_custody='NOT_QUALIFIED', forbidden_modules_loaded=[],
                identity={'schema_sha256': '098a19d69e8d233ac653503b53761a94824f31812757a11a7ded1589fe1e0788',
                          'wheel_sha256': '48938e0436ab1be615fc0a41434119a2065490a6212b9a5e56949e89b0588b76'})
    if mode == 'R22':
        data['oracle_algorithm'] = 'INDEPENDENT_INTEGER_SIGNIFICAND_EXPONENT_NOT_STRUCT_ROUNDTRIP'
        data['input_structure_only_not_F61'] = True
    else:
        data['time_semantics'] = 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME'
    for row in data['cases']:
        row.update(oracle_parity=True, cc_sha256='1' * 64, cs_sha256='2' * 64)
        if mode == 'R22':
            if row['accepted']:
                row.update(custody_claim='DECLARED_READBACK_BINDING_NOT_AUTHENTICATED_NATIVE_CUSTODY',
                           precision_claim='EXACT_SUPPLIED_FLOAT32_PROMOTED_TO_PYTHON_FLOAT')
            else:
                row['oracle_rejection_code'] = 'SEMANTIC_DOMAIN'
        else:
            index = row['index']
            row['stamp'] = {'sequence_id': 'R23_FIXED_SEQUENCE' if mode == 'R23' else 'R24_FIXED_FAULT_RESET',
                            'invocation_index': index, 'capture_id': 'entry_' + str(index)}
            row['state_binding'] = 'EXPLICIT_FIXED_INITIAL_DATA' if index == 0 else 'PREVIOUS_VERIFIED_MODEL_OUTPUT_NOT_ACTUAL_HISTORY'
    return data
