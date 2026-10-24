"""Certified synthetic rectangle search; exact-on-completion, Cartesian worst case.

Only declaratively defined integer counts can prune. Float/percentile comparisons
are evaluated canonically at leaves; an uncertain float bound never prunes.
"""

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_two_context_math as m
from openpilot.tools.cyber_autotune.empirical_hurdle_v4_two_context_oracle import Policy
from openpilot.tools.cyber_autotune import empirical_plant_policy as p

COMPLETE = 'SYNTHETIC_EXACT_OPTIMUM_CERTIFIED'
EMPTY = 'SYNTHETIC_NO_FEASIBLE_PAIR'
EXHAUSTED = 'V4_TWO_CONTEXT_FITTING_INCONCLUSIVE_RESOURCE_BOUND'


def area(rect):
  a, b, c, d = rect
  return (int(b) - int(a) + 1) * (int(d) - int(c) + 1)


def split(rect):
  a, b, c, d = rect
  if b - a >= d - c and b > a:
    mid = (a + b) // 2
    return [[a, mid, c, d], [mid + 1, b, c, d]]
  mid = (c + d) // 2
  return [[a, b, c, mid], [a, b, mid + 1, d]]


def fit(population, policy, *, enable_integer_pruning=False, max_nodes=None):
  m.require(type(policy) is Policy, 'V4_TWO_CONTEXT_POLICY_CONFLICT')
  m.require(type(enable_integer_pruning) is bool and (max_nodes is None or type(max_nodes) is int and max_nodes >= 0))
  table = m.IntegerTables(population)
  root = [0, len(table.domain[0]) - 1, 0, len(table.domain[1]) - 1]
  nodes, stack = [{'rect': root, 'kind': 'PENDING'}], [0]
  best, best_id, feasible = None, None, 0
  visits = leaves = prunes = objective_prunes = 0
  primary, floor = policy.objective.primary_count(), policy.feasibility.tp_floor()
  while stack and (max_nodes is None or visits < max_nodes):
    node_id = stack.pop()
    node, rect = nodes[node_id], nodes[node_id]['rect']
    visits += 1
    if enable_integer_pruning and floor is not None:
      upper = table.upper(rect, 'TP')
      if upper < floor:
        node.update(kind='PRUNE_TP', bound=upper, floor=floor, policy_sha256=policy.identity)
        prunes += 1
        continue
    if enable_integer_pruning and primary is not None and best is not None:
      upper = table.upper(rect, *primary)
      # STRICT only: every primary tie stays searchable for the external full key.
      if upper < best[0]:
        node.update(kind='PRUNE_OBJECTIVE', bound=upper, incumbent=best_id, policy_sha256=policy.identity)
        prunes += 1
        objective_prunes += 1
        continue
    if area(rect) == 1:
      pair = table.pair((rect[0], rect[2]))
      row = m.evaluate_pair(population, pair)
      accepted = policy.feasibility.accepts(row)
      key = policy.key(pair, row) if accepted else None
      node.update(kind='LEAF', metrics=row, feasible=accepted, key=list(key) if key is not None else None)
      leaves += 1
      feasible += int(accepted)
      if key is not None and (best is None or key > best):
        best, best_id = key, node_id
      continue
    rectangles = split(rect)
    children = [len(nodes), len(nodes) + 1]
    node.update(kind='SPLIT', children=children)
    nodes.extend({'rect': child, 'kind': 'PENDING'} for child in rectangles)
    if primary is not None:
      order = sorted(children, key=lambda i: (table.upper(nodes[i]['rect'], *primary), -i))
      stack.extend(order)  # Highest bound popped first; preserve structural left/right child order.
    else:
      stack.extend(reversed(children))
  unresolved = sum(area(nodes[i]['rect']) for i in stack)
  complete = not stack
  best_node = nodes[best_id] if best_id is not None and complete else None
  result = {'status': (COMPLETE if best is not None else EMPTY) if complete else EXHAUSTED,
            'scope': 'SYNTHETIC_ONLY_NO_V4_POLICY_AUTHORITY', 'input_sha256': population.identity, 'policy_sha256': policy.identity,
            'domain_size': area(root), 'domain_shape': [len(v) for v in table.domain], 'nodes': nodes,
            'selected_pair': table.pair((best_node['rect'][0], best_node['rect'][2])) if best_node else None,
            'selected_metrics': best_node['metrics'] if best_node else None,
            'selected_key': list(best) if best_node else None, 'visited_rectangles': visits, 'leaves_evaluated': leaves,
            'rectangles_pruned': prunes, 'objective_prunes': objective_prunes, 'evaluated_feasible_pair_count': feasible,
            'feasible_pair_count': feasible if complete and objective_prunes == 0 else None,
            'unresolved_domain_size': unresolved, 'certificate_record_count': len(nodes)}
  population.verify()
  return result


def verify_certificate(population, policy, result):
  """Independent coverage-tree, canonical-leaf and bound verification; no sampled proof."""
  def need(condition):
    m.require(condition, 'V4_TWO_CONTEXT_CERTIFICATE_CONFLICT')
  try:
    population.verify()
    need(type(result) is dict and set(result) == {
      'status', 'scope', 'input_sha256', 'policy_sha256', 'domain_size', 'domain_shape', 'nodes', 'selected_pair', 'selected_metrics',
      'selected_key', 'visited_rectangles', 'leaves_evaluated', 'rectangles_pruned', 'objective_prunes', 'evaluated_feasible_pair_count',
      'feasible_pair_count', 'unresolved_domain_size', 'certificate_record_count'})
    need(result['scope'] == 'SYNTHETIC_ONLY_NO_V4_POLICY_AUTHORITY')
    need(all(type(result[k]) is int and result[k] >= 0 for k in (
      'domain_size', 'visited_rectangles', 'leaves_evaluated', 'rectangles_pruned', 'objective_prunes', 'evaluated_feasible_pair_count',
      'unresolved_domain_size', 'certificate_record_count')))
    need(result['feasible_pair_count'] is None or type(result['feasible_pair_count']) is int)
    need(type(result['domain_shape']) is list and len(result['domain_shape']) == 2 and all(type(v) is int for v in result['domain_shape']))
    need(type(policy) is Policy and result['input_sha256'] == population.identity and result['policy_sha256'] == policy.identity)
    table = m.IntegerTables(population)
    nodes = result['nodes']
    root = [0, len(table.domain[0]) - 1, 0, len(table.domain[1]) - 1]
    need(type(nodes) is list and len(nodes) > 0 and nodes[0]['rect'] == root)
    pending = [(0, root)]
    seen, leaves = set(), {}
    unresolved = prunes = objective_prunes = 0
    while pending:
      i, expected = pending.pop()
      need(type(i) is int and 0 <= i < len(nodes) and i not in seen)
      seen.add(i)
      node = nodes[i]
      need(node['rect'] == expected and all(type(x) is int for x in node['rect']))
      kind, rect = node['kind'], node['rect']
      extra = {'PENDING': set(), 'SPLIT': {'children'}, 'LEAF': {'metrics', 'feasible', 'key'},
               'PRUNE_TP': {'bound', 'floor', 'policy_sha256'}, 'PRUNE_OBJECTIVE': {'bound', 'incumbent', 'policy_sha256'}}
      need(kind in extra and set(node) == {'rect', 'kind'} | extra[kind])
      if kind == 'PENDING':
        unresolved += area(rect)
      elif kind == 'SPLIT':
        need(area(rect) > 1 and type(node['children']) is list and len(node['children']) == 2)
        pending.extend(zip(node['children'], split(rect), strict=True))
      elif kind == 'LEAF':
        need(area(rect) == 1)
        pair = table.pair((rect[0], rect[2]))
        row = m.evaluate_pair(population, pair)
        accepted = policy.feasibility.accepts(row)
        key = list(policy.key(pair, row)) if accepted else None
        need(p.canonical(node['metrics']) == p.canonical(row) and node['feasible'] is accepted and p.canonical(node['key']) == p.canonical(key))
        leaves[i] = (pair, row, tuple(key) if key is not None else None)
      elif kind == 'PRUNE_TP':
        floor = policy.feasibility.tp_floor()
        upper = table.upper(rect, 'TP')
        need(type(node['floor']) is int and type(node['bound']) is int)
        need(node['policy_sha256'] == policy.identity and floor is not None and node['floor'] == floor and node['bound'] == upper and upper < floor)
        prunes += 1
      else:
        primary = policy.objective.primary_count()
        need(node['policy_sha256'] == policy.identity and primary is not None)
        need(type(node['incumbent']) is int and 0 <= node['incumbent'] < len(nodes))
        incumbent = nodes[node['incumbent']]
        need(incumbent['kind'] == 'LEAF' and incumbent['feasible'] is True)
        upper = table.upper(rect, *primary)
        need(type(node['bound']) is int and node['bound'] == upper and upper < incumbent['key'][0])
        prunes += 1
        objective_prunes += 1
    need(len(seen) == len(nodes))  # Reject cycles, reused children and unreachable forged records.
    feasible = [(i, entry) for i, entry in leaves.items() if entry[2] is not None]
    best = max(feasible, key=lambda item: item[1][2])[1] if feasible else None
    if unresolved:
      need(result['status'] == EXHAUSTED and all(result[k] is None for k in ('selected_pair', 'selected_metrics', 'selected_key', 'feasible_pair_count')))
    else:
      need(result['status'] == (COMPLETE if best else EMPTY))
      need(p.canonical(result['selected_pair']) == p.canonical(best[0] if best else None))
      need(p.canonical(result['selected_metrics']) == p.canonical(best[1] if best else None))
      need(p.canonical(result['selected_key']) == p.canonical(list(best[2]) if best else None))
      need(result['feasible_pair_count'] == (len(feasible) if objective_prunes == 0 else None))
    need(result['domain_size'] == area(root) and result['domain_shape'] == [len(v) for v in table.domain])
    need(result['unresolved_domain_size'] == unresolved and result['leaves_evaluated'] == len(leaves))
    need(result['rectangles_pruned'] == prunes and result['objective_prunes'] == objective_prunes)
    need(result['visited_rectangles'] == sum(n['kind'] != 'PENDING' for n in nodes))
    need(result['certificate_record_count'] == len(nodes) and result['evaluated_feasible_pair_count'] == len(feasible))
    return True
  except (KeyError, TypeError, IndexError, AssertionError) as error:
    raise ValueError('V4_TWO_CONTEXT_CERTIFICATE_CONFLICT') from error
