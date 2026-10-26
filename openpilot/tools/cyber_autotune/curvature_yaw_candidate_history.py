"""Append-only consistency history; external retained tip prevents rewriting."""
import copy
from openpilot.tools.cyber_autotune.native_protocol import canonical,digest,_keys,_hex

QUALIFICATION='BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE'
FIELDS=('candidate','status','alias_of','source_sha256','config_sha256','search_policy_sha256','result_sha256',
        'scenario_set','rejection_reasons','robustness_result','qualification_status')
STATUSES=('REFERENCE','TRADEOFF_ONLY','REJECTED','SCREENING_IMPROVED','BLOCKED')


def validate_history(records):
  if type(records) is not list or len(records)>64:
    raise ValueError('INVALID_HISTORY_SIZE')
  seen={}
  parent=None
  for record in records:
    _keys(record,('entry','parent_sha256','record_sha256'))
    entry=record['entry']
    _keys(entry,FIELDS)
    if (record['parent_sha256']!=parent or record['record_sha256']!=digest(canonical({k:v for k,v in record.items() if k!='record_sha256'}))
        or type(entry['candidate']) is not str or not entry['candidate'] or entry['candidate'] in seen
        or entry['status'] not in STATUSES or entry['qualification_status']!=QUALIFICATION
        or not all(_hex(entry[k],64) for k in ('source_sha256','config_sha256','result_sha256'))
        or (entry['search_policy_sha256'] is not None and not _hex(entry['search_policy_sha256'],64))
        or type(entry['scenario_set']) is not list or not entry['scenario_set']
        or not all(type(s) is str and s for s in entry['scenario_set'])
        or len(set(entry['scenario_set']))!=len(entry['scenario_set'])
        or type(entry['rejection_reasons']) is not list or not all(type(s) is str for s in entry['rejection_reasons'])
        or (entry['robustness_result'] is not None and not _hex(entry['robustness_result'],64))):
      raise ValueError('HISTORY_BINDING_OR_AUTHORITY_DRIFT')
    if entry['candidate']=='CURRENT' and entry['alias_of']!='BASELINE':
      raise ValueError('CURRENT_ALIAS_REQUIRED')
    if entry['alias_of'] is not None:
      if entry['alias_of'] not in seen or any(entry[k]!=seen[entry['alias_of']][k] for k in
          ('source_sha256','config_sha256','result_sha256','scenario_set','status','qualification_status')):
        raise ValueError('DECLARED_ALIAS_NOT_EQUIVALENT')
    seen[entry['candidate']]=entry
    parent=record['record_sha256']


def append_history(records,entry,*,expected_parent_sha256):
  validate_history(records)
  if expected_parent_sha256!=(records[-1]['record_sha256'] if records else None):
    raise ValueError('STALE_HISTORY_PARENT')
  record={'entry':copy.deepcopy(entry),'parent_sha256':expected_parent_sha256}
  record['record_sha256']=digest(canonical(record))
  result=copy.deepcopy(records)+[record]
  validate_history(result)
  return result
