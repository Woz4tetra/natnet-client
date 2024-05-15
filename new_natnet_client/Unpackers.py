import new_natnet_client.NatNetTypes as NatNetTypes
from typing import Callable, Iterable, Tuple, Dict
from collections import deque
from struct import unpack
from itertools import batched

class DataUnpackerV3_0:
  rigid_body_lenght: int = 38
  marker_lenght: int = 26
  frame_suffix_lenght: int = 42
  @classmethod
  def unpack_data_size(cls, data: bytes) -> Tuple[int, int]:
    return 0, 0

  @classmethod
  def unpack_frame_prefix_data(cls, data: bytes) -> Tuple[NatNetTypes.Frame_prefix, int]:
    offset = 0
    prefix = NatNetTypes.Frame_prefix(int.from_bytes(data[offset : (offset:=offset+4)], byteorder='little', signed=True))
    return prefix, offset

  @classmethod
  def unpack_marker_set_data(cls, data: bytes) -> Tuple[NatNetTypes.Marker_set_data, int]:
    offset = 0
    num_marker_sets = int.from_bytes(data[offset : (offset:=offset+4)], byteorder='little', signed=True)
    _, tmp_offset = cls.unpack_data_size(data)
    offset += tmp_offset
    markers: Iterable[NatNetTypes.Marker_data] = deque()
    position_unpacker: Callable[[Iterable[int]], NatNetTypes.Position] = lambda position_data: NatNetTypes.Position.unpack(bytes(position_data))
    for _ in range(num_marker_sets):
      name, _, _ = data[offset:].partition(b'\0')
      offset += len(name) + 1
      name = str(name, encoding="utf-8")
      num_markers = int.from_bytes(data[offset : (offset:=offset+4)], byteorder='little', signed=True)
      positions = tuple(map(
        position_unpacker,
        batched(data[offset : (offset:=offset+(12*num_markers))], 12)
      ))
      markers.append(NatNetTypes.Marker_data(name, num_markers, positions))
    marker_sets = tuple(markers)
    return NatNetTypes.Marker_set_data(num_marker_sets, marker_sets), offset

  @classmethod
  def unpack_legacy_other_markers(cls, data: bytes) -> Tuple[NatNetTypes.Legacy_marker_set_data,int]:
    offset = 0
    num_markers = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    _, tmp_offset = cls.unpack_data_size(data)
    offset += tmp_offset
    positions = deque(map(
      lambda position_data: NatNetTypes.Position.unpack(bytes(position_data)),
      batched(data[offset:(offset:=offset+(12*num_markers))], 12)
    ))
    positions = tuple(positions)
    return NatNetTypes.Legacy_marker_set_data(num_markers, positions), offset

  @classmethod
  def unpack_rigid_body(cls, data: bytes) -> NatNetTypes.Rigid_body:
    offset = 0
    identifier = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    pos = NatNetTypes.Position.unpack(data[offset:(offset:=offset+12)])
    rot = NatNetTypes.Quaternion.unpack(data[offset:(offset:=offset+16)])
    err = unpack('<f', data[offset:(offset:=offset+4)])[0]
    param: int = unpack( 'h', data[offset:(offset:=offset+2)])[0]
    tracking = bool(param & 0x01)
    return NatNetTypes.Rigid_body(identifier, pos, rot, err, tracking)

  @classmethod
  def unpack_rigid_body_data(cls, data: bytes) -> Tuple[NatNetTypes.Rigid_body_data, int]:
    offset = 0
    num_rigid_bodies = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    _, tmp_offset = cls.unpack_data_size(data)
    offset += tmp_offset
    rigid_bodies = tuple(map(
        lambda rigid_body_data: cls.unpack_rigid_body(bytes(rigid_body_data)),
        batched(data[offset:(offset:=offset+(cls.rigid_body_lenght*num_rigid_bodies))], cls.rigid_body_lenght) 
    ))
    return NatNetTypes.Rigid_body_data(num_rigid_bodies, rigid_bodies), offset
  
  @classmethod
  def unpack_skeleton(cls, data: bytes) -> Tuple[NatNetTypes.Skeleton, int]:
    offset = 0
    identifier = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    num_rigid_bodies = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    rigid_bodies = tuple(map(
        lambda rigid_body_data: cls.unpack_rigid_body(bytes(rigid_body_data)),
        batched(data[offset:(offset:=offset+(cls.rigid_body_lenght*num_rigid_bodies))], cls.rigid_body_lenght) 
    ))
    return NatNetTypes.Skeleton(identifier, num_rigid_bodies, rigid_bodies), offset

  @classmethod
  def unpack_skeleton_data(cls, data: bytes) -> Tuple[NatNetTypes.Skeleton_data, int]:
    offset = 0
    num_skeletons = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    _, tmp_offset = cls.unpack_data_size(data)
    offset += tmp_offset
    skeletons: Iterable[NatNetTypes.Skeleton] = deque()
    for _ in range(num_skeletons):
      skeleton, tmp_offset = cls.unpack_skeleton(data[offset:])
      offset += tmp_offset
      skeletons.append(skeleton)
    skeletons = tuple(skeletons)
    return NatNetTypes.Skeleton_data(num_skeletons, skeletons), offset

  @classmethod
  def unpack_asset_rigid_body(cls, data: bytes) -> NatNetTypes.Asset_RB:
    raise NotImplementedError("Subclasses must implement the unpack method")

  @classmethod
  def unpack_asset_marker(cls, data: bytes) -> NatNetTypes.Asset_marker:
    raise NotImplementedError("Subclasses must implement the unpack method")

  @classmethod
  def unpack_asset(cls, data: bytes) -> Tuple[NatNetTypes.Asset, int]:
    raise NotImplementedError("Subclasses must implement the unpack method")

  @classmethod
  def unpack_asset_data(cls, data: bytes) -> Tuple[NatNetTypes.Asset_data, int]:
    raise NotImplementedError("Subclasses must implement the unpack method")

  @classmethod
  def decode_marker_id(cls, identifier: int) -> Tuple[int, int]:
    return (
      identifier >> 16,
      identifier & 0x0000ffff
    )

  @classmethod
  def unpack_labeled_marker(cls, data: bytes) -> NatNetTypes.Labeled_marker:
    offset = 0
    identifier = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    pos = NatNetTypes.Position.unpack(data[offset:(offset:=offset+12)])
    size = unpack('<f', data[offset:(offset:=offset+4)])[0]
    param = unpack( 'h', data[offset:(offset:=offset+2)])[0]
    residual = unpack('<f', data[offset:(offset:=offset+4)])[0] * 1000.0
    return NatNetTypes.Labeled_marker(identifier, pos, size, param, residual)

  @classmethod
  def unpack_labeled_marker_data(cls, data: bytes) -> Tuple[NatNetTypes.Labeled_marker_data, int]:
    offset = 0
    num_markers = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    _, tmp_offset = cls.unpack_data_size(data)
    offset += tmp_offset
    markers = tuple(map(
      lambda marker_data: cls.unpack_labeled_marker(bytes(marker_data)),
      batched(data[offset:(offset:=offset+(cls.marker_lenght*num_markers))],cls.marker_lenght)
    ))
    return NatNetTypes.Labeled_marker_data(num_markers, markers), offset

  @classmethod
  def unpack_channels(cls, data: bytes, num_channels: int) -> Tuple[Tuple[NatNetTypes.Channel, ...], int]:
    offset = 0
    channels: Iterable[NatNetTypes.Channel] = deque()
    frame_unpacker: Callable[[Iterable[int]], float] = lambda frame_data: unpack('<f', bytes(frame_data))[0]
    for _ in range(num_channels):
      num_frames = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
      frames = tuple(map(
        frame_unpacker,
        batched(data[offset:(offset:=offset+(4*num_frames))],4)
      ))
      channels.append(NatNetTypes.Channel(num_frames, frames))
    return tuple(channels), offset

  @classmethod
  def unpack_force_plate_data(cls, data: bytes) -> Tuple[NatNetTypes.Force_plate_data, int]:
    offset = 0
    num_force_plates = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    _, tmp_offset = cls.unpack_data_size(data)
    offset += tmp_offset
    force_plates: Iterable[NatNetTypes.Force_plate] = deque()
    for _ in range(num_force_plates):
      identifier = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
      num_channels = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
      channels, tmp_offset = cls.unpack_channels(data[offset:], num_channels)
      offset += tmp_offset
      force_plates.append(NatNetTypes.Force_plate(identifier, num_channels, channels))
    force_plates = tuple(force_plates)
    return NatNetTypes.Force_plate_data(num_force_plates, force_plates), offset

  @classmethod
  def unpack_device_data(cls, data: bytes) -> Tuple[NatNetTypes.Device_data, int]:
    offset = 0
    num_devices = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    _, tmp_offset = cls.unpack_data_size(data)
    offset += tmp_offset
    devices: Iterable[NatNetTypes.Device] = deque()
    for _ in range(num_devices):
      identifier = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
      num_channels = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
      channels, tmp_offset = cls.unpack_channels(data[offset:], num_channels)
      offset += tmp_offset
      devices.append(NatNetTypes.Device(identifier, num_channels, channels))
    devices = tuple(devices)
    return NatNetTypes.Device_data(num_devices, devices), offset

  @classmethod
  def unpack_frame_suffix_data(cls, data: bytes) -> NatNetTypes.Frame_suffix:
    offset = 0
    time_code = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    time_code_sub = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    timestamp = unpack('<d', data[offset:(offset:=offset+8)])[0]
    camera_mid_exposure = int.from_bytes(data[offset:(offset:=offset+8)], byteorder='little', signed=True)
    stamp_data = int.from_bytes(data[offset:(offset:=offset+8)], byteorder='little', signed=True)
    stamp_transmit = int.from_bytes(data[offset:(offset:=offset+8)], byteorder='little', signed=True)
    param = unpack( 'h', data[offset:(offset:=offset+2)])[0]
    recording = bool(param & 0x01)
    tracked_models_changed = bool(param & 0x02)
    return NatNetTypes.Frame_suffix(time_code, time_code_sub, timestamp, camera_mid_exposure, stamp_data, stamp_transmit, recording, tracked_models_changed)

  @classmethod
  def unpack_mocap_data(cls, data: bytes) -> NatNetTypes.MoCap:
    offset = 0
    tmp_offset = 0

    prefix_data, tmp_offset = cls.unpack_frame_prefix_data(data[offset:])
    offset += tmp_offset

    marker_set_data, tmp_offset = cls.unpack_marker_set_data(data[offset:])
    offset += tmp_offset

    legacy_marker_set_data, tmp_offset = cls.unpack_legacy_other_markers(data[offset:])
    offset += tmp_offset

    rigid_body_data, tmp_offset = cls.unpack_rigid_body_data(data[offset:])
    offset += tmp_offset

    skeleton_data, tmp_offset = cls.unpack_skeleton_data(data[offset:])
    offset += tmp_offset

    labeled_marker_data, tmp_offset = cls.unpack_labeled_marker_data(data[offset:])
    offset += tmp_offset

    force_plate_data, tmp_offset = cls.unpack_force_plate_data(data[offset:])
    offset += tmp_offset

    device_data, tmp_offset = cls.unpack_device_data(data[offset:])
    offset += tmp_offset

    suffix_data = cls.unpack_frame_suffix_data(data[offset:])

    return NatNetTypes.MoCap(prefix_data, marker_set_data, legacy_marker_set_data, rigid_body_data, skeleton_data, labeled_marker_data, force_plate_data, device_data, suffix_data)

  @classmethod
  def unpack_marker_set_description(cls, data: bytes) -> Tuple[Dict[str, NatNetTypes.Marker_set_description], int]:
    offset = 0
    name, _, _ = data[offset:].partition(b'\0')
    offset += len(name) + 1
    name = str(name, encoding="utf-8")
    num_markers = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    markers_names: Iterable[str] = deque()
    for _ in range(num_markers):
      marker_name, _, _ = data[offset:].partition(b'\0')
      offset += len(name) + 1
      markers_names.append(str(marker_name, encoding="utf-8"))
    markers_names = tuple(markers_names)
    return {name : NatNetTypes.Marker_set_description(name, num_markers, markers_names)}, offset

  @classmethod
  def unpack_rigid_body_description(cls, data: bytes) -> Tuple[Dict[int, NatNetTypes.Rigid_body_description], int]:
    offset = 0
    name, _, _ = data[offset:].partition(b'\0')
    offset += len(name) + 1
    name = str(name, encoding="utf-8")
    identifier = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    parent_id = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    pos = NatNetTypes.Position.unpack(data[offset:(offset:=offset+12)])
    num_markers = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    offset_pos = offset
    offset_id = offset_pos + (12*num_markers)
    offset_name = offset_id + (4*num_markers)
    marker_name = ""
    markers: Iterable[NatNetTypes.RB_marker] = deque()
    for _ in range(num_markers):
      marker_pos = NatNetTypes.Position.unpack(data[offset_pos:(offset_pos:=offset_pos+12)])
      marker_id = int.from_bytes(data[offset_id:(offset_id:=offset_id+4)], byteorder='little', signed=True)
      markers.append(NatNetTypes.RB_marker(marker_name, marker_id, marker_pos))
    markers = tuple(markers)
    return {identifier : NatNetTypes.Rigid_body_description(name, identifier, parent_id, pos, num_markers, markers)}, offset_name

  @classmethod
  def unpack_skeleton_description(cls, data: bytes) -> Tuple[Dict[int, NatNetTypes.Skeleton_description], int]:
    offset = 0
    name, _, _ = data[offset:].partition(b'\0')
    offset += len(name) + 1
    name = str(name, encoding="utf-8")
    identifier = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    num_rigid_bodies = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    rigid_bodies: Iterable[NatNetTypes.Rigid_body_description] = deque()
    for _ in range(num_rigid_bodies):
      d, offset_tmp = cls.unpack_rigid_body_description(data[offset:])
      rigid_body = list(d.values())[0]
      rigid_bodies.append(rigid_body)
      offset += offset_tmp
    rigid_bodies = tuple(rigid_bodies)
    return {identifier : NatNetTypes.Skeleton_description(name, identifier, num_rigid_bodies, rigid_bodies)}, offset

  @classmethod
  def unpack_force_plate_description(cls, data: bytes) -> Tuple[Dict[str, NatNetTypes.Force_plate_description], int]:
    offset = 0
    identifier = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)

    serial_number, _, _ = data[offset:].partition(b'\0')
    offset += len(serial_number) + 1
    serial_number = str(serial_number, encoding='utf-8')

    f_width: float = unpack('<f', data[offset:(offset:=offset+4)])[0]
    f_length: float = unpack('<f', data[offset:(offset:=offset+4)])[0]
    dimensions = (f_width, f_length)

    origin = NatNetTypes.Position.unpack(data[offset:(offset:=offset+12)])

    # Not tested
    calibration_matrix = tuple(unpack('<f', data[offset:(offset:=offset+4)])[0] for _ in range(12*12))
    corners = tuple(unpack('<f', data[offset:(offset:=offset+4)])[0] for _ in range(4*3))

    plate_type = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    channel_data_type = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    num_channels = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    
    channels: Iterable[str] = deque()
    for _ in range(num_channels):
      channel_name, _, _ = data[offset:].partition(b'\0')
      offset += len(channel_name) + 1
      channels.append(str(channel_name, encoding='utf-8'))
    channels = tuple(channels)
    return {serial_number : NatNetTypes.Force_plate_description(identifier, serial_number, dimensions, origin, calibration_matrix, corners, plate_type, channel_data_type, num_channels, channels)}, offset

  @classmethod
  def unpack_device_description(cls, data: bytes) -> Tuple[Dict[str, NatNetTypes.Device_description], int]:
    offset = 0
    
    identifier = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    
    name, _, _ = data[offset:].partition(b'\0')
    offset += len(name) + 1
    name = str(name, encoding='utf-8')
    
    serial_number, _, _ = data[offset:].partition(b'\0')
    offset += len(serial_number) + 1
    serial_number = str(serial_number, encoding='utf-8')

    device_type = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    channel_data_type = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    num_channels = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    channels: Iterable[str] = deque()
    for _ in range(num_channels):
      channel_name,_,_ = data[offset:].partition(b'\0')
      offset += len(channel_name) + 1
      channels.append(str(channel_name, encoding='utf-8'))
    channels = tuple(channels)
    return {serial_number : NatNetTypes.Device_description(identifier, name, serial_number, device_type, channel_data_type, num_channels, channels)}, offset

  @classmethod
  def unpack_camera_description(cls, data: bytes) -> Tuple[Dict[str, NatNetTypes.Camera_description], int]:
    offset = 0
    name, _, _ = data[offset:].partition(b'\0')
    offset += len(name) + 1
    name = str(name, encoding="utf-8")
    pos = NatNetTypes.Position.unpack(data[offset:(offset:=offset+12)])
    orientation = NatNetTypes.Quaternion.unpack(data[offset:(offset:=offset+16)])
    return {name : NatNetTypes.Camera_description(name, pos, orientation)}, offset

  @classmethod
  def unpack_marker_description(cls, data: bytes) -> Tuple[Dict[int, NatNetTypes.Marker_description], int]:
    offset = 0
    name, _, _ = data[offset:].partition(b'\0')
    offset += len(name) + 1
    name = str(name, encoding="utf-8")
    identifier = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    pos = NatNetTypes.Position.unpack(data[offset:(offset:=offset+12)])
    size = unpack('<f', data[offset:(offset:=offset+4)])[0]
    param = unpack( 'h', data[offset:(offset:=offset+2)])[0]
    return {identifier : NatNetTypes.Marker_description(name, identifier, pos, size, param)}, offset

  @classmethod
  def unpack_asset_description(cls, data: bytes) -> Tuple[Dict[int, NatNetTypes.Asset_description], int]:
    offset = 0
    name, _, _ = data[offset:].partition(b'\0')
    offset += len(name) + 1
    name = str(name, encoding="utf-8")
    asset_type = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    identifier = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    num_rigid_bodies = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    rigid_bodies: Iterable[NatNetTypes.Rigid_body_description] = deque()
    for _ in range(num_rigid_bodies):
      d, offset_tmp = cls.unpack_rigid_body_description(data[offset:])
      rigid_body = list(d.values())[0]
      rigid_bodies.append(rigid_body)
      offset += offset_tmp
    rigid_bodies = tuple(rigid_bodies)
    num_markers = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    markers: Iterable[NatNetTypes.Marker_description] = deque()
    for _ in range(num_markers):
      d,offset_tmp = cls.unpack_marker_description(data[offset:])
      marker = list(d.values())[0]
      markers.append(marker)
      offset += offset_tmp
    markers = tuple(markers)
    return {identifier : NatNetTypes.Asset_description(name, asset_type, identifier, num_rigid_bodies, rigid_bodies, num_markers, markers)}, offset

class DataUnpackerV4_1(DataUnpackerV3_0):
  asset_rigid_body_lenght: int = 38
  asset_marker_lenght: int = 26
  frame_suffix_lenght: int = 50

  @classmethod
  def unpack_data_size(cls, data: bytes) -> Tuple[int, int]:
    offset = 0
    size_in_bytes = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    return size_in_bytes, offset

  @classmethod
  def unpack_asset_rigid_body(cls, data: bytes) -> NatNetTypes.Asset_RB:
    offset = 0
    identifier = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    pos = NatNetTypes.Position.unpack(data[offset:(offset:=offset+12)])
    rot = NatNetTypes.Quaternion.unpack(data[offset:(offset:=offset+16)])
    err = unpack('<f', data[offset:(offset:=offset+4)])[0]
    param = unpack( 'h', data[offset:(offset:=offset+2)])[0]
    return NatNetTypes.Asset_RB(identifier, pos, rot, err, param)

  @classmethod
  def unpack_asset_marker(cls, data: bytes) -> NatNetTypes.Asset_marker:
    offset = 0
    identifier = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    pos = NatNetTypes.Position.unpack(data[offset:(offset:=offset+12)])
    size = unpack('<f', data[offset:(offset:=offset+4)])[0]
    param = unpack( 'h', data[offset:(offset:=offset+2)])[0]
    residual = unpack('<f', data[offset:(offset:=offset+4)])[0]
    return NatNetTypes.Asset_marker(identifier, pos, size, param, residual)

  @classmethod
  def unpack_asset(cls, data: bytes) -> Tuple[NatNetTypes.Asset, int]:
    offset = 0
    identifier = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    num_rigid_bodies = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    rigid_bodies = tuple(map(
      lambda rigid_body_data: cls.unpack_asset_rigid_body(bytes(rigid_body_data)),
      batched(data[offset:(offset:=offset+(cls.asset_rigid_body_lenght*num_rigid_bodies))], cls.asset_rigid_body_lenght)
    ))
    num_markers = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    markers = tuple(map(
      lambda marker_data: cls.unpack_asset_marker(bytes(marker_data)),
      batched(data[offset:(offset:=offset+(cls.asset_marker_lenght*num_markers))], cls.asset_marker_lenght)
    ))
    return NatNetTypes.Asset(identifier, num_rigid_bodies, rigid_bodies, num_markers, markers), offset

  @classmethod
  def unpack_asset_data(cls, data: bytes) -> Tuple[NatNetTypes.Asset_data, int]:
    offset = 0
    num_assets = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    _, tmp_offset = cls.unpack_data_size(data)
    offset += tmp_offset
    assets: Iterable[NatNetTypes.Asset] = deque()
    for _ in range(num_assets):
      asset, tmp_offset = cls.unpack_asset(data[offset:])
      offset += tmp_offset
      assets.append(asset)
    assets = tuple(assets)
    return NatNetTypes.Asset_data(num_assets, assets), offset

  @classmethod
  def unpack_frame_suffix_data(cls, data: bytes) -> NatNetTypes.Frame_suffix:
    offset = 0
    time_code = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    time_code_sub = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    timestamp = unpack('<d', data[offset:(offset:=offset+8)])[0]
    camera_mid_exposure = int.from_bytes(data[offset:(offset:=offset+8)], byteorder='little', signed=True)
    stamp_data = int.from_bytes(data[offset:(offset:=offset+8)], byteorder='little', signed=True)
    stamp_transmit = int.from_bytes(data[offset:(offset:=offset+8)], byteorder='little', signed=True)
    precision_timestamp_sec = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    precision_timestamp_frac_sec = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    param = unpack( 'h', data[offset:(offset:=offset+2)])[0]
    recording = bool(param & 0x01)
    tracked_models_changed = bool(param & 0x02)
    return NatNetTypes.Frame_suffix(time_code, time_code_sub, timestamp, camera_mid_exposure, stamp_data, stamp_transmit, recording, tracked_models_changed, precision_timestamp_sec, precision_timestamp_frac_sec)

  @classmethod
  def unpack_mocap_data(cls, data: bytes) -> NatNetTypes.MoCap:
    offset = 0
    tmp_offset = 0

    prefix_data, tmp_offset = cls.unpack_frame_prefix_data(data[offset:])
    offset += tmp_offset

    marker_set_data, tmp_offset = cls.unpack_marker_set_data(data[offset:])
    offset += tmp_offset

    legacy_marker_set_data, tmp_offset = cls.unpack_legacy_other_markers(data[offset:])
    offset += tmp_offset

    rigid_body_data, tmp_offset = cls.unpack_rigid_body_data(data[offset:])
    offset += tmp_offset

    skeleton_data, tmp_offset = cls.unpack_skeleton_data(data[offset:])
    offset += tmp_offset

    asset_data, tmp_offset = cls.unpack_asset_data(data[offset:])
    offset += tmp_offset

    labeled_marker_data, tmp_offset = cls.unpack_labeled_marker_data(data[offset:])
    offset += tmp_offset

    force_plate_data, tmp_offset = cls.unpack_force_plate_data(data[offset:])
    offset += tmp_offset

    device_data, tmp_offset = cls.unpack_device_data(data[offset:])
    offset += tmp_offset

    suffix_data = cls.unpack_frame_suffix_data(data[offset:])

    return NatNetTypes.MoCap(prefix_data, marker_set_data, legacy_marker_set_data, rigid_body_data, skeleton_data, labeled_marker_data, force_plate_data, device_data, suffix_data, asset_data)

  @classmethod
  def unpack_rigid_body_description(cls, data: bytes) -> Tuple[Dict[int, NatNetTypes.Rigid_body_description], int]:
    d, offset = super().unpack_rigid_body_description(data)
    rb_desc = tuple(d.values())[0]
    for marker in rb_desc.markers:
      name, _, _ = data[offset:].partition(b'\0')
      offset += len(name) + 1
      marker.name = str(name, encoding="utf-8")
    return d, offset