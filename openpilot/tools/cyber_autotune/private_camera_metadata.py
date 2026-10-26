"""Encoded MPEG-TS/H264 metadata only: never invokes a codec or image decoder.

Restricted qcamera format: 188-byte TS, one video PES PID, SPS/AUD present,
presentation timestamps and stable dimensions. Unsupported input is rejected.
Access-unit count is metadata, not an inspected image/content selection signal.
"""
import re
from statistics import median


class Bits:
  def __init__(self, data):
    self.bits = ''.join(f'{v:08b}' for v in data)
    self.pos = 0

  def read(self, count):
    if self.pos + count > len(self.bits):
      raise ValueError('TRUNCATED_SPS')
    value = int(self.bits[self.pos:self.pos + count], 2)
    self.pos += count
    return value

  def ue(self):
    zero = 0
    while self.read(1) == 0:
      zero += 1
      if zero > 31:
        raise ValueError('SPS_EXP_GOLOMB_BOUND')
    return (1 << zero) - 1 + (self.read(zero) if zero else 0)

  def se(self):
    value = self.ue()
    return (value + 1) // 2 if value % 2 else -value // 2


def sps_geometry(data):
  bits = Bits(data.replace(b'\x00\x00\x03', b'\x00\x00'))
  profile = bits.read(8)
  bits.read(16)
  bits.ue()
  chroma = 1
  separate = 0
  if profile in (100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135):
    chroma = bits.ue()
    if chroma > 3:
      raise ValueError('UNSUPPORTED_SPS_CHROMA')
    if chroma == 3:
      separate = bits.read(1)
    bits.ue()
    bits.ue()
    bits.read(1)
    if bits.read(1):
      for index in range(8 if chroma != 3 else 12):
        if bits.read(1):
          last = next_scale = 8
          for _ in range(16 if index < 6 else 64):
            if next_scale:
              next_scale = (last + bits.se() + 256) % 256
            last = next_scale or last
  bits.ue()
  poc = bits.ue()
  if poc == 0:
    bits.ue()
  elif poc == 1:
    bits.read(1)
    bits.se()
    bits.se()
    count = bits.ue()
    if count > 256:
      raise ValueError('SPS_POC_BOUND')
    for _ in range(count):
      bits.se()
  elif poc != 2:
    raise ValueError('UNSUPPORTED_SPS_POC')
  bits.ue()
  bits.read(1)
  width = 16 * (bits.ue() + 1)
  height_units = bits.ue() + 1
  frame_only = bits.read(1)
  if not frame_only:
    bits.read(1)
  height = 16 * (2 - frame_only) * height_units
  bits.read(1)
  if bits.read(1):
    left, right, top, bottom = [bits.ue() for _ in range(4)]
    chroma_array = 0 if separate else chroma
    sub_width = 2 if chroma_array in (1, 2) else 1
    sub_height = 2 if chroma_array == 1 else 1
    crop_x = sub_width if chroma_array else 1
    crop_y = sub_height * (2 - frame_only)
    width -= crop_x * (left + right)
    height -= crop_y * (top + bottom)
  if width <= 0 or height <= 0 or width * height > 6_000_000:
    raise ValueError('UNSUPPORTED_SPS_IMAGE_DOMAIN')
  return width, height


def h264_metadata(elementary, timestamps):
  starts = list(re.finditer(b'\x00\x00(?:\x00)?\x01', elementary))
  geometries, frames = set(), 0
  for i, match in enumerate(starts):
    end = starts[i + 1].start() if i + 1 < len(starts) else len(elementary)
    nal = elementary[match.end():end]
    if not nal:
      raise ValueError('EMPTY_H264_NAL')
    kind = nal[0] & 31
    if kind == 7:
      geometries.add(sps_geometry(nal[1:]))
    elif kind == 9:
      frames += 1
  if len(geometries) != 1 or frames < 10 or len(timestamps) != frames:
    raise ValueError('STABLE_SPS_AUD_AND_ONE_PTS_PER_FRAME_REQUIRED')
  sorted_pts = sorted(timestamps)
  differences = [b - a for a, b in zip(sorted_pts, sorted_pts[1:], strict=False)]
  if not differences or min(differences) <= 0:
    raise ValueError('UNIQUE_PRESENTATION_TIMESTAMPS_REQUIRED')
  fps = 90000.0 / median(differences)
  if not 1 <= fps <= 120 or max(differences) > 2 * median(differences):
    raise ValueError('UNSUPPORTED_CAMERA_TIMEBASE')
  width, height = next(iter(geometries))
  return {'width': width, 'height': height, 'frame_count': frames, 'fps': fps, 'codec': 'h264'}


def ts_metadata(data):
  if not data or len(data) % 188:
    raise ValueError('188_BYTE_TS_REQUIRED')
  pid_video, elementary, timestamps = None, bytearray(), []
  previous = {}
  for offset in range(0, len(data), 188):
    packet = data[offset:offset + 188]
    if packet[0] != 0x47 or packet[1] & 0x80 or packet[3] & 0xc0:
      raise ValueError('INVALID_OR_ENCRYPTED_TS')
    pid = ((packet[1] & 31) << 8) | packet[2]
    control = (packet[3] >> 4) & 3
    if control not in (1, 3):
      continue
    start = 4 + (packet[4] + 1 if control == 3 else 0)
    payload = packet[start:]
    new = bool(packet[1] & 0x40)
    if new and payload[:3] == b'\0\0\1' and len(payload) >= 14 and 0xe0 <= payload[3] <= 0xef:
      if pid_video is not None and pid_video != pid:
        raise ValueError('MULTIPLE_VIDEO_PIDS_UNSUPPORTED')
      pid_video = pid
    if pid != pid_video:
      continue
    counter = packet[3] & 15
    if pid in previous and counter != (previous[pid] + 1) % 16:
      raise ValueError('VIDEO_TRANSPORT_CONTINUITY_FAILURE')
    previous[pid] = counter
    if new:
      if payload[:3] != b'\0\0\1' or not payload[7] & 0x80:
        raise ValueError('VIDEO_PES_WITH_PTS_REQUIRED')
      pts = payload[9:14]
      if any(not pts[k] & 1 for k in (0, 2, 4)):
        raise ValueError('INVALID_PTS_MARKERS')
      timestamp = ((pts[0] & 14) << 29) | (pts[1] << 22) | ((pts[2] & 254) << 14) | (pts[3] << 7) | (pts[4] >> 1)
      timestamps.append(timestamp)
      payload = payload[9 + payload[8]:]
    elementary.extend(payload)
  return h264_metadata(bytes(elementary), timestamps)
