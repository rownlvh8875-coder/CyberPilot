"""Source-audited registration infrastructure; hardware phase remains unobserved.

Native means the OS04C10 VisionIPC/static-K image (1344x760), not the raw
2688x1520 sensor array. Conditional arithmetic is never an observed transform.
No image/log I/O, detector inference, physical calibration or reference admission.
"""
import html
import json
import numpy as np
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune.private_camera_metadata import Bits
from openpilot.tools.cyber_autotune.lane_tail_report import unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

AUDIT_FILE = c.ROOT / 'docs/cyberpilot/changes/qcamera-source-pipeline-audit-v1.json'
AUDIT_SHA = '45b6fc38277e790f721976cc29257256e0a058f34fc4e98967fec1a25f2a3311'
RULES = ('CENTER_ALIGNED', 'ZERO_ORIGIN', 'CORNER_ALIGNED')
CHECKS = ('sensor', 'recording_source', 'effective_crop', 'resize_phase', 'orientation',
          'detector_restoration', 'annotation_mapping', 'distortion_ordering',
          'intrinsics_applicability', 'empirical_residual')
FLAGS = {'qualification_allowed': False, 'reference_promotable': False,
         'sealed_reference_allowed': False, 'vehicle_activation_allowed': False}


def audit():
  x = json.loads(AUDIT_FILE.read_bytes())
  unseal(x)
  if x['receipt_sha256'] != AUDIT_SHA:
    raise ValueError('SOURCE_AUDIT_IDENTITY_CHANGED')
  for path, sha in x['current_source_files'].items():
    if digest((c.ROOT / path).read_bytes()) != sha:
      raise ValueError('CAMERA_PIPELINE_SOURCE_DRIFT')
  for group in ('detector_restoration_files', 'annotation_mapping_files'):
    for path, sha in x[group].items():
      if digest((c.ROOT / path).read_bytes()) != sha:
        raise ValueError('FROZEN_COORDINATE_SOURCE_DRIFT')
  return x


def dimensions(wh):
  if type(wh) is not list or len(wh) != 2 or any(type(v) is not int or not 2 <= v <= 16384 for v in wh):
    raise ValueError('BOUNDED_INTEGER_IMAGE_DIMENSIONS_REQUIRED')


def affine(native_wh, source_wh, crop, rule):
  """Explicit hypothetical sampling convention, never guessed for actual VIDC."""
  dimensions(native_wh)
  dimensions(source_wh)
  if type(crop) is not list or len(crop) != 4:
    raise ValueError('CROP_RECTANGLE_REQUIRED')
  for value in crop:
    c.number(value)
  left, top, width, height = crop
  if min(left, top) < 0 or min(width, height) <= 1 or left + width > native_wh[0] or top + height > native_wh[1]:
    raise ValueError('CROP_OUTSIDE_NATIVE_IMAGE')
  if rule not in RULES:
    raise ValueError('EXPLICIT_RESIZE_CONVENTION_REQUIRED')
  sx, sy = width/source_wh[0], height/source_wh[1]
  ox, oy = left, top
  if rule == 'CENTER_ALIGNED':
    ox += .5*sx - .5
    oy += .5*sy - .5
  elif rule == 'CORNER_ALIGNED':
    sx, sy = (width-1)/(source_wh[0]-1), (height-1)/(source_wh[1]-1)
  return {'native_wh': native_wh, 'source_wh': source_wh, 'crop_rectangle': crop, 'resize_rule': rule,
          'scale_x': sx, 'scale_y': sy, 'offset_x_px': ox, 'offset_y_px': oy,
          'source_units': 'ORIGINAL_QCAMERA_PIXEL_CENTER_INDEX',
          'target_units': 'VISIONIPC_INTRINSICS_PIXEL_CENTER_INDEX'}


def check_affine(a):
  if type(a) is not dict or a != affine(a['native_wh'], a['source_wh'], a['crop_rectangle'], a['resize_rule']):
    raise ValueError('AFFINE_COEFFICIENT_IDENTITY_MISMATCH')


def points(values):
  out = np.asarray(values, dtype=float)
  if out.ndim != 2 or out.shape[1] != 2 or not len(out) or not np.isfinite(out).all():
    raise ValueError('FINITE_N_BY_TWO_POINTS_REQUIRED')
  return out


def forward(values, a):
  check_affine(a)
  return points(values)*[a['scale_x'], a['scale_y']] + [a['offset_x_px'], a['offset_y_px']]


def inverse(values, a):
  check_affine(a)
  return (points(values)-[a['offset_x_px'], a['offset_y_px']])/[a['scale_x'], a['scale_y']]


def intrinsics(matrix, a):
  check_affine(a)
  k = np.asarray(matrix, dtype=float)
  if k.shape != (3, 3) or not np.isfinite(k).all() or k[0, 0] <= 0 or k[1, 1] <= 0 or not np.array_equal(k[2], [0, 0, 1]):
    raise ValueError('PINHOLE_STATIC_MATRIX_REQUIRED')
  transform = np.array([[a['scale_x'], 0, a['offset_x_px']], [0, a['scale_y'], a['offset_y_px']], [0, 0, 1.]])
  return c.seal({'schema': 'SOURCE_DERIVED_QCAMERA_INTRINSICS_CONDITIONAL_V1',
                 'matrix': (np.linalg.inv(transform)@k).tolist(),
                 'native_matrix_sha256': digest(canonical(matrix)), 'affine_sha256': digest(canonical(a)),
                 'provenance': 'STATIC_INTRINSICS_PRIOR_PLUS_CONDITIONAL_IMAGE_TRANSFORM',
                 'independently_calibrated': False, **FLAGS})


def source_registration():
  x = audit()
  return c.seal({
    'schema': 'PIXEL_GEOMETRY_REGISTRATION_V1', 'status': 'PIXEL_GEOMETRY_REGISTRATION_PARTIAL',
    'software_contract_status': 'PIXEL_GEOMETRY_REGISTRATION_DEFINED_STRUCTURAL_ONLY',
    'scope': 'SOURCE_AUDIT_PARTIAL', 'source_camera_role': 'NARROW_ROAD',
    'sensor': 'os04c10', 'sensor_status': 'LOG_OBSERVED_SOURCE_PROBE_MATCH_NOT_PHYSICAL_INSPECTION',
    'recording_commit': x['recording_commit'], 'source_audit_sha256': AUDIT_SHA,
    'recorded_source_files': x['recorded_source_files'], 'current_source_files': x['current_source_files'],
    'source_wh': [526, 330], 'native_wh': [1344, 760], 'raw_sensor_wh': [2688, 1520],
    'coordinate_convention': 'TOP_LEFT_PIXEL_CENTER_INDEX_0_X_COLUMN_RIGHT_Y_ROW_DOWN',
    'orientation': 'NO_APPLICATION_ROTATION_OR_MIRROR_QCAMERA_V4L_DEFAULTS_NOT_INDEPENDENTLY_OBSERVED',
    'crop_rectangle': None, 'resize_rule': None, 'affine': None,
    'application_input_rectangle': [0, 0, 1344, 760],
    'application_qcamera_crop': x['application_qcamera_crop'],
    'effective_crop_status': 'HARDWARE_EFFECTIVE_CROP_PENDING',
    'conditional_rules': list(RULES), 'conditional_rules_exhaustive': False,
    'distortion_status': 'DISTORTION_UNVERIFIED',
    'empirical_status': 'EMPIRICAL_MAPPING_VALIDATION_UNAVAILABLE',
    'residual_bound_native_px': None,
    'checks': {key: {'status': 'PENDING', 'evidence_sha256': AUDIT_SHA} for key in CHECKS},
    'detector_restoration_sha256': digest(canonical(x['detector_restoration_files'])),
    'annotation_mapping_sha256': digest(canonical(x['annotation_mapping_files'])),
    'pipeline_sha256': digest(canonical(x['recorded_source_files'])),
    'source_metadata_sha256': x['development_metadata']['metadata_audit_sha256'],
    'physical_calibration': 'CALIBRATION_MEASUREMENT_PENDING', **FLAGS,
  })


def validate_registration(r, *, numeric=False):
  unseal(r)
  expected = source_registration()
  c.exact(r, expected.keys())
  for key in ('source_audit_sha256', 'recording_commit', 'recorded_source_files', 'current_source_files',
              'source_camera_role', 'source_wh', 'native_wh', 'raw_sensor_wh', 'sensor', 'pipeline_sha256',
              'annotation_mapping_sha256', 'detector_restoration_sha256', 'source_metadata_sha256'):
    if r[key] != expected[key]:
      raise ValueError('REGISTRATION_SOURCE_SENSOR_OR_DIMENSIONS_MISMATCH')
  if any(r[key] is not False for key in FLAGS):
    raise ValueError('NONQUALIFYING_REGISTRATION_FIREWALL')
  if r['status'] == 'PIXEL_GEOMETRY_REGISTRATION_PARTIAL':
    if r != expected or numeric:
      raise ValueError('EXACT_HARDWARE_PIXEL_REGISTRATION_PENDING')
    return r
  if r['status'] != 'PIXEL_GEOMETRY_REGISTRATION_VALIDATED':
    raise ValueError('VALIDATED_REGISTRATION_REQUIRED')
  # Actual VIDC firmware phase/crop is unresolved in the pinned audit. No API
  # accepting self-declared PASS flags may manufacture missing runtime evidence.
  if r['scope'] != 'TEST_ONLY':
    raise ValueError('ACTUAL_VIDC_PHASE_PROOF_NOT_ADMITTED_BY_THIS_AUDIT')
  if r['distortion_status'] != 'PRESERVED_TEST_ONLY':
    raise ValueError('DISTORTION_STAGE_ORDER_UNVERIFIED')
  c.exact(r['checks'], CHECKS)
  for check in r['checks'].values():
    c.exact(check, ('status', 'evidence_sha256'))
    if check['status'] != 'PASS_TEST_ONLY':
      raise ValueError('REGISTRATION_CHECK_PENDING')
    c.sha(check['evidence_sha256'])
  c.number(r['residual_bound_native_px'], positive=True)
  a = affine(r['native_wh'], r['source_wh'], r['crop_rectangle'], r['resize_rule'])
  if r['affine'] != a:
    raise ValueError('REGISTRATION_AFFINE_MISMATCH')
  return r


def projection_mapping(r, calibration):
  validate_registration(r)
  core = c.validate_admitted(calibration)
  if core['intrinsics']['resolution_wh'] != r['native_wh'] or core['measurement']['camera']['sensor'] != r['sensor']:
    raise ValueError('CALIBRATION_SENSOR_OR_IMAGE_MISMATCH')
  if r['status'] == 'PIXEL_GEOMETRY_REGISTRATION_PARTIAL':
    return {'schema': 'PIXEL_CAMERA_REGISTRATION_PENDING_V1', 'registration': r}
  validate_registration(r, numeric=True)
  if core['admission_scope'] != r['scope']:
    raise ValueError('TEST_REGISTRATION_CANNOT_BIND_PHYSICAL_CALIBRATION')
  a = r['affine']
  return {'schema': 'REGISTERED_PIXEL_CAMERA_MAPPING_V1', 'source_wh': r['source_wh'], 'target_wh': r['native_wh'],
          **{key: a[key] for key in ('scale_x', 'scale_y', 'offset_x_px', 'offset_y_px')},
          'verified_same_camera': True, 'verified_crop_resize': True,
          'evidence_sha256': r['receipt_sha256'], 'mapping_residual_bound_px': r['residual_bound_native_px'],
          'registration': r}


def native_derivative(values, r):
  validate_registration(r, numeric=True)
  return c.seal({'schema': 'NATIVE_PIXEL_COORDINATE_DERIVATIVE', 'scope': r['scope'],
                 'registration_sha256': r['receipt_sha256'], 'original_points_sha256': digest(canonical(values)),
                 'points': forward(values, r['affine']).tolist(), 'original_modified': False, **FLAGS})


def detector_contract():
  return {'canonical_wh': [1640, 590], 'crop_xyxy': [0, 270, 1640, 590], 'model_wh': [800, 320],
          'input_resize': 'OPENCV_INTER_LINEAR_PIXEL_CENTER_SAMPLING',
          'normalization': 'MODEL_PREPROCESSOR_ZERO_MEAN_STD255_BGR_NO_TEST_FLIP_NO_PADDING',
          'restoration': 'NORMALIZED_SPLINE_X_TIMES_SOURCE_WIDTH_Y_ROWS_DIV_SOURCE_HEIGHT',
          'resampling_inverse_proven': False,
          'limitation': 'NORMALIZED_LANE_REPRESENTATION_NOT_AN_EXACT_INVERSE_OF_IMAGE_RESAMPLING'}


def detector_restore(normalized_xy):
  return points(normalized_xy)*[526, 330]


def detector_normalize(source_xy):
  return points(source_xy)/[526, 330]


def canvas_to_original(client_xy, rect_xywh, backing_wh, zoom, pan_xy):
  c.number(zoom, positive=True)
  if len(rect_xywh) != 4 or len(backing_wh) != 2 or len(pan_xy) != 2 or len(client_xy) != 2:
    raise ValueError('CANVAS_COORDINATE_DIMENSIONS')
  for v in [*rect_xywh, *backing_wh, *pan_xy, *client_xy]:
    c.number(v)
  if min(rect_xywh[2:]) <= 0 or min(backing_wh) <= 0:
    raise ValueError('POSITIVE_CANVAS_RECTANGLE')
  return ((np.array(client_xy)-rect_xywh[:2])*np.array(backing_wh)/rect_xywh[2:]-pan_xy)/zoom


def sps_layout(payload):
  """SPS display crop removes codec padding; it does not reveal optical crop."""
  b = Bits(payload.replace(b'\x00\x00\x03', b'\x00\x00'))
  profile = b.read(8)
  b.read(16)
  b.ue()
  chroma, separate = 1, 0
  if profile in (100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135):
    chroma = b.ue()
    if chroma > 3:
      raise ValueError('UNSUPPORTED_CHROMA')
    if chroma == 3:
      separate = b.read(1)
    b.ue()
    b.ue()
    b.read(1)
    if b.read(1):
      for index in range(8 if chroma != 3 else 12):
        if b.read(1):
          last = next_scale = 8
          for _ in range(16 if index < 6 else 64):
            if next_scale:
              next_scale = (last+b.se()+256) % 256
            last = next_scale or last
  b.ue()
  poc = b.ue()
  if poc == 0:
    b.ue()
  elif poc == 1:
    b.read(1)
    b.se()
    b.se()
    count = b.ue()
    if count > 256:
      raise ValueError('SPS_POC_BOUND')
    for _ in range(count):
      b.se()
  elif poc != 2:
    raise ValueError('UNSUPPORTED_SPS_POC')
  b.ue()
  b.read(1)
  coded_w, h_units = 16*(b.ue()+1), b.ue()+1
  progressive = b.read(1)
  if not progressive:
    b.read(1)
  coded_h = 16*(2-progressive)*h_units
  b.read(1)
  crop = [b.ue() for _ in range(4)] if b.read(1) else [0, 0, 0, 0]
  array = 0 if separate else chroma
  ux = 2 if array in (1, 2) else 1
  uy = (2 if array == 1 else 1)*(2-progressive)
  crop = [crop[0]*ux, crop[1]*ux, crop[2]*uy, crop[3]*uy]
  visible = [coded_w-crop[0]-crop[1], coded_h-crop[2]-crop[3]]
  dimensions(visible)
  return {'coded_wh': [coded_w, coded_h], 'visible_wh': visible, 'display_crop_lrtb_px': crop,
          'chroma_format_idc': chroma, 'progressive': bool(progressive), 'proves_native_crop': False}


def visualizer(r):
  validate_registration(r)
  k = [[1141.5, 0., 672.], [0., 1141.5, 380.], [0., 0., 1.]]
  variants = {rule: {'affine': affine(r['native_wh'], r['source_wh'], [0,0,1344,760], rule)}
              for rule in RULES}
  for v in variants.values():
    v['kq'] = intrinsics(k, v['affine'])['matrix']
    v['grid'] = forward([[0,0],[262.5,164.5],[525,329]], v['affine']).tolist()
  data = canonical(variants).decode().replace('<', '\\u003c')
  return """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Qcamera coordinate registration</title><style>body{font:16px sans-serif;background:#111c28;color:#e7f4ff;margin:22px}
svg{max-width:100%;background:#1c2a38}pre{white-space:pre-wrap}label{display:block;margin:12px}</style>
<h1>SOFTWARE COORDINATE REGISTRATION</h1><h2>NOT PHYSICAL CALIBRATION</h2>
<p>HARDWARE RESIZE PHASE PENDING · DISTORTION_UNVERIFIED · NO METER QUALIFICATION</p>
<p>Native static-K / VisionIPC:1344×760. Raw sensor array:2688×1520. qcamera:526×330.</p>
<p>Rectangles below show the application input and a conditional full-frame resize hypothesis.
Effective hardware crop and phase remain unverified. These alternatives are not exhaustive bounds.</p>
<label>Conditional convention <select id="rule">""" + ''.join('<option>'+html.escape(x)+'</option>' for x in RULES) + """</select></label>
<svg id="diagram" viewBox="-25 -25 1400 820"><rect width="1344" height="760" fill="none" stroke="#6ad"/>
<path d="M672 0V760M0 380H1344" stroke="#789"/><circle cx="672" cy="380" r="8" fill="#fc5"/>
<g id="samples" fill="#f8a"/></svg>
<p>Yellow: source static principal point. Pink: conditional mapped known qcamera points (not private lane points).</p>
<svg id="qimage" viewBox="-10 -10 550 355"><rect width="526" height="330" fill="none" stroke="#6ad"/>
<circle id="qprincipal" r="4" fill="#fc5"/></svg>
<p>qcamera rectangle and conditional principal point. No verified K_q is generated.</p>
<pre id="result"></pre><script>
const variants="""+data+""";function draw(){const v=variants[document.querySelector('#rule').value];
document.querySelector('#samples').innerHTML=v.grid.map(p=>'<circle cx="'+p[0]+'" cy="'+p[1]+'" r="7"/>').join('');
document.querySelector('#qprincipal').setAttribute('cx',v.kq[0][2]);
document.querySelector('#qprincipal').setAttribute('cy',v.kq[1][2]);
document.querySelector('#result').textContent=JSON.stringify({conditional_only:true,...v},null,2);}
document.querySelector('#rule').onchange=draw;draw();</script>"""
