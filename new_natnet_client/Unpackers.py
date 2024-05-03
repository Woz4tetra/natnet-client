import new_natnet_client.NatNetTypes as NatNetTypes
from dataclasses import asdict
from typing import Tuple, Dict
from collections import deque
from struct import unpack

class DataUnpackerV3_0:
  @classmethod
  def unpack_data_size(cls, data:bytes) -> Tuple[int, int]:
    return 0,0

  @classmethod
  def unpack_frame_prefix_data(cls, data:bytes) -> Tuple[NatNetTypes.Frame_prefix, int]:
    offset = 0
    prefix = NatNetTypes.Frame_prefix(int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True))
    return prefix, offset

  @classmethod
  def unpack_marker_set_data(cls, data:bytes) -> Tuple[NatNetTypes.Marker_set_data, int]:
    offset = 0
    template = {}
    template['num_marker_sets'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    _, tmp_offset = cls.unpack_data_size(data)
    offset += tmp_offset
    markers = deque()
    for i in range(template['num_marker_sets']):
      template_marker = {}
      name, _, _ = data[offset:].partition(b'\0')
      offset += len(name) + 1
      template_marker['name'] = str(name, encoding="utf-8")
      template_marker['num_markers'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
      positions = deque()
      for j in range(template_marker['num_markers']):
        positions.append(NatNetTypes.Position.unpack(data[offset:(offset:=offset+12)]))
      template_marker['positions'] = tuple(positions)
      markers.append(NatNetTypes.Marker_data(**template_marker))
    template['marker_sets'] = tuple(markers)
    return NatNetTypes.Marker_set_data(**template), offset

  @classmethod
  def unpack_legacy_other_markers(cls, data:bytes) -> Tuple[NatNetTypes.Legacy_marker_set_data,int]:
    offset = 0
    template = {}
    template['num_markers'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    _, tmp_offset = cls.unpack_data_size(data)
    offset += tmp_offset
    positions = deque()
    for _ in range(template['num_markers']):
      positions.append(NatNetTypes.Position.unpack(data[offset:(offset:=offset+12)]))
    template['positions'] = tuple(positions)
    return NatNetTypes.Legacy_marker_set_data(**template), offset

  @classmethod
  def unpack_rigid_body(cls, data:bytes) -> Tuple[NatNetTypes.Rigid_body, int]:
    offset = 0
    template = {}
    template['id'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    template['pos'] = NatNetTypes.Position.unpack(data[offset:(offset:=offset+12)])
    template['rot'] = NatNetTypes.Quaternion.unpack(data[offset:(offset:=offset+16)])
    template['err'] = unpack('<f', data[offset:(offset:=offset+4)])[0]
    param:int = unpack( 'h', data[offset:(offset:=offset+2)])[0]
    template['tracking'] = bool(param & 0x01)
    return NatNetTypes.Rigid_body(**template), offset

  @classmethod
  def unpack_rigid_body_data(cls, data:bytes) -> Tuple[NatNetTypes.Rigid_body_data, int]:
    offset = 0
    template = {}
    template['num_rigid_bodies'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    _, tmp_offset = cls.unpack_data_size(data)
    offset += tmp_offset
    rigid_bodies = deque()
    for _ in range(template['num_rigid_bodies']):
      rigid_body, tmp_offset = cls.unpack_rigid_body(data[offset:])
      offset += tmp_offset
      rigid_bodies.append(rigid_body)
    template['rigid_bodies'] = tuple(rigid_bodies)
    return NatNetTypes.Rigid_body_data(**template), offset
  
  @classmethod
  def unpack_skeleton(cls, data:bytes) -> Tuple[NatNetTypes.Skeleton, int]:
    offset = 0
    template = {}
    template['id'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    template['num_rigid_bodies'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    rigid_bodies = deque()
    for _ in range(template['num_rigid_bodies']):
      rigid_body, tmp_offset = cls.unpack_rigid_body(data[offset:])
      offset += tmp_offset
      rigid_bodies.append(rigid_body)
    template['rigid_bodies'] = tuple(rigid_bodies)
    return NatNetTypes.Skeleton(**template), offset

  @classmethod
  def unpack_skeleton_data(cls, data:bytes) -> Tuple[NatNetTypes.Skeleton_data, int]:
    offset = 0
    template = {}
    template['num_skeletons'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    _, tmp_offset = cls.unpack_data_size(data)
    offset += tmp_offset
    skeletons = deque()
    for _ in range(template['num_skeletons']):
      skeleton, tmp_offset = cls.unpack_skeleton(data[offset:])
      offset += tmp_offset
      skeletons.append(skeleton)
    template['skeletons'] = tuple(skeletons)
    return NatNetTypes.Skeleton_data(**template), offset

  @classmethod
  def unpack_asset_rigid_body(cls, data:bytes) -> Tuple[NatNetTypes.Asset_RB, int]:
    raise NotImplementedError("Subclasses must implement the unpack method")

  @classmethod
  def unpack_asset_marker(cls, data:bytes) -> Tuple[NatNetTypes.Asset_marker, int]:
    raise NotImplementedError("Subclasses must implement the unpack method")

  @classmethod
  def unpack_asset(cls, data:bytes) -> Tuple[NatNetTypes.Asset, int]:
    raise NotImplementedError("Subclasses must implement the unpack method")

  @classmethod
  def unpack_asset_data(cls, data:bytes) -> Tuple[NatNetTypes.Asset_data, int]:
    raise NotImplementedError("Subclasses must implement the unpack method")

  @classmethod
  def decode_marker_id(cls, id:int) -> Tuple[int, int]:
    return (
      id >> 16,
      id & 0x0000ffff
    )

  @classmethod
  def unpack_labeled_marker_data(cls, data:bytes) -> Tuple[NatNetTypes.Labeled_marker_data, int]:
    offset = 0
    template = {}
    template['num_markers'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    _, tmp_offset = cls.unpack_data_size(data)
    offset += tmp_offset
    markers = deque()
    for _ in range(template['num_markers']):
      template_marker = {}
      template_marker['id'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
      template_marker['pos'] = NatNetTypes.Position.unpack(data[offset:(offset:=offset+12)])
      template_marker['size'] = unpack('<f', data[offset:(offset:=offset+4)])[0]
      template_marker['param'] = unpack( 'h', data[offset:(offset:=offset+2)])[0]
      template_marker['residual'] = unpack('<f', data[offset:(offset:=offset+4)])[0] * 1000.0
      markers.append(NatNetTypes.Labeled_marker(**template_marker))
    template['markers'] = tuple(markers)
    return NatNetTypes.Labeled_marker_data(**template), offset

  @classmethod
  def unpack_force_plate_data(cls, data:bytes) -> Tuple[NatNetTypes.Force_plate_data, int]:
    offset = 0
    template = {}
    template['num_force_plates'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    _, tmp_offset = cls.unpack_data_size(data)
    offset += tmp_offset
    force_plates = deque()
    for i in range(template['num_force_plates']):
      template_force_plate = {}
      template_force_plate['id'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
      template_force_plate['num_channels'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
      channels = deque()
      for j in range(template_force_plate['num_channels']):
        template_channel = {}
        template_channel['num_frames'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
        frames = deque()
        for k in range(template_channel['num_frames']):
          frames.append(unpack('<f', data[offset:(offset:=offset+4)])[0])
        template_channel['frames'] = tuple(frames)
        channels.append(NatNetTypes.Channel(**template_channel))
      template_force_plate['channels'] = tuple(channels)
      force_plates.append(NatNetTypes.Force_plate(**template_force_plate))
    template['force_plates'] = tuple(force_plates)
    return NatNetTypes.Force_plate_data(**template), offset

  @classmethod
  def unpack_device_data(cls, data:bytes) -> Tuple[NatNetTypes.Device_data, int]:
    offset = 0
    template = {}
    template['num_devices'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    _, tmp_offset = cls.unpack_data_size(data)
    offset += tmp_offset
    devices = deque()
    for i in range(template['num_devices']):
      template_device = {}
      template_device['id'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
      template_device['num_channels'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
      channels = deque()
      for j in range(template_device['num_channels']):
        template_channel = {}
        template_channel['num_frames'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
        frames = deque()
        for k in range(template_channel['num_frames']):
          frames.append(unpack('<f', data[offset:(offset:=offset+4)])[0])
        template_channel['frames'] = tuple(frames)
        channels.append(NatNetTypes.Channel(**template_channel))
      template_device['channels'] = tuple(channels)
      devices.append(NatNetTypes.Device(**template_device))
    template['devices'] = tuple(devices)
    return NatNetTypes.Device_data(**template), offset

  @classmethod
  def unpack_frame_suffix_data(cls, data:bytes) -> Tuple[NatNetTypes.Frame_suffix, int]:
    offset = 0
    template = {}
    template['time_code'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    template['time_code_sub'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    template['timestamp'] = unpack('<d', data[offset:(offset:=offset+8)])[0]
    template['camera_mid_exposure'] = int.from_bytes(data[offset:(offset:=offset+8)], byteorder='little', signed=True)
    template['stamp_data'] = int.from_bytes(data[offset:(offset:=offset+8)], byteorder='little', signed=True)
    template['stamp_transmit'] = int.from_bytes(data[offset:(offset:=offset+8)], byteorder='little', signed=True)
    param = unpack( 'h', data[offset:(offset:=offset+2)])[0]
    template['recording'] = bool(param & 0x01)
    template['tracked_models_changed'] = bool(param & 0x02)
    return NatNetTypes.Frame_suffix(**template), offset

  @classmethod
  def unpack_mocap_data(cls, data:bytes) -> Tuple[NatNetTypes.MoCap, int]:
    offset = 0
    tmp_offset = 0
    template = {}

    template['prefix_data'], tmp_offset = cls.unpack_frame_prefix_data(data[offset:])
    offset += tmp_offset

    template['marker_set_data'], tmp_offset = cls.unpack_marker_set_data(data[offset:])
    offset += tmp_offset

    template['legacy_marker_set_data'], tmp_offset = cls.unpack_legacy_other_markers(data[offset:])
    offset += tmp_offset

    template['rigid_body_data'], tmp_offset = cls.unpack_rigid_body_data(data[offset:])
    offset += tmp_offset

    template['skeleton_data'], tmp_offset = cls.unpack_skeleton_data(data[offset:])
    offset += tmp_offset

    template['labeled_marker_data'], tmp_offset = cls.unpack_labeled_marker_data(data[offset:])
    offset += tmp_offset

    template['force_plate_data'], tmp_offset = cls.unpack_force_plate_data(data[offset:])
    offset += tmp_offset

    template['device_data'], tmp_offset = cls.unpack_device_data(data[offset:])
    offset += tmp_offset

    template['suffix_data'], tmp_offset = cls.unpack_frame_suffix_data(data[offset:])
    offset += tmp_offset

    return NatNetTypes.MoCap(**template), offset

  @classmethod
  def unpack_marker_set_description(cls, data:bytes) -> Tuple[Dict[str, NatNetTypes.Marker_set_description], int]:
    offset = 0
    template = {}
    name, _, _ = data[offset:].partition(b'\0')
    offset += len(name) + 1
    template['name'] = str(name, encoding="utf-8")
    template['num_markers'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    names = deque()
    for _ in range(template['num_markers']):
      name, _, _ = data[offset:].partition(b'\0')
      offset += len(name) + 1
      names.append(str(name, encoding="utf-8"))
    template['markers_names'] = tuple(names)
    return {template['name']:NatNetTypes.Marker_set_description(**template)}, offset

  @classmethod
  def unpack_rigid_body_description(cls, data:bytes) -> Tuple[Dict[int, NatNetTypes.Rigid_body_description], int]:
    offset = 0
    template = {}
    name, _, _ = data[offset:].partition(b'\0')
    offset += len(name) + 1
    template['name'] = str(name, encoding="utf-8")
    template['id'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    template['parent_id'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    template['pos'] = NatNetTypes.Position.unpack(data[offset:(offset:=offset+12)])
    template['num_markers'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    offset_pos = offset
    offset_id = offset_pos + (12*template['num_markers'])
    offset_name = offset_id + (4*template['num_markers'])
    template["name"] = ""
    markers = deque()
    for _ in range(template['num_markers']):
      template['pos'] = data[offset_pos:(offset_pos:=offset_pos+12)]
      template['id'] = int.from_bytes(data[offset_Y:(offset_Y:=offset_Y+4)], byteorder='little', signed=True)
      markers.append(NatNetTypes.RB_marker(**template))
    template['markers'] = tuple(markers)
    return {template['id']:NatNetTypes.Rigid_body_description(**template)}, offset_name

  @classmethod
  def unpack_skeleton_description(cls, data:bytes) -> Tuple[Dict[int, NatNetTypes.Skeleton_description], int]:
    offset = 0
    template = {}
    name, _, _ = data[offset:].partition(b'\0')
    offset += len(name) + 1
    template['name'] = str(name, encoding="utf-8")
    template['id'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    template['num_rigid_bodies'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    rigid_bodies = deque()
    for _ in range(template['num_rigid_bodies']):
      d, offset_tmp = cls.unpack_rigid_body_description(data[offset:])
      rigid_body = list(d.values())[0]
      rigid_bodies.append(rigid_body)
      offset += offset_tmp
    template['rigid_bodies'] = tuple(rigid_bodies)
    return {template['id']:NatNetTypes.Skeleton_description(**template)}, offset

  @classmethod
  def unpack_force_plate_description(cls, data: bytes) -> Tuple[Dict[str, NatNetTypes.Force_plate_description], int]:
    offset = 0
    template = {}
    template['id'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)

    serial_number, _, _ = data[offset:].partition(b'\0')
    offset += len(serial_number) + 1
    template['serial_number'] = str(serial_number, encoding='utf-8')

    f_width:float = unpack('<f', data[offset:(offset:=offset+4)])[0]
    f_length:float = unpack('<f', data[offset:(offset:=offset+4)])[0]
    template['dimensions'] = (f_width, f_length)

    template['origin'] = NatNetTypes.Position.unpack(data[offset:(offset:=offset+12)])

    # Not tested
    template['calibration_matrix'] = tuple(unpack('<f', data[offset:(offset:=offset+4)])[0] for _ in range(12*12))
    template['corners'] = tuple(unpack('<f', data[offset:(offset:=offset+4)])[0] for _ in range(4*3))

    template['plate_type'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    template['channel_data_type'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    template['num_channels'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    channels = deque()
    for _ in range(template['num_channels']):
      channel_name, _, _ = data[offset:].partition(b'\0')
      offset += len(channel_name) + 1
      channels.append(str(channel_name, encoding='utf-8'))
    template['channels'] = tuple(channels)
    return {template['serial_number']:NatNetTypes.Force_plate_description(**template)}, offset

  @classmethod
  def unpack_device_description(cls, data: bytes) -> Tuple[Dict[str, NatNetTypes.Device_description], int]:
    offset = 0
    template = {}
    
    template['id'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    
    name, _, _ = data[offset:].partition(b'\0')
    offset += len(name) + 1
    template['name'] = str(name, encoding='utf-8')
    
    serial_number, _, _ = data[offset:].partition(b'\0')
    offset += len(serial_number) + 1
    template['serial_number'] = str(serial_number, encoding='utf-8')

    template['device_type'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    template['channel_data_type'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    template['num_channels'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    channels = deque()
    for _ in range(template['num_channels']):
      channel_name,_,_ = data[offset:].partition(b'\0')
      offset += len(channel_name) + 1
      channels.append(str(channel_name, encoding='utf-8'))
    template['channels'] = tuple(channels)
    return {template['serial_number']:NatNetTypes.Device_description(**template)}, offset

  @classmethod
  def unpack_camera_description(cls, data:bytes) -> Tuple[Dict[bytes, NatNetTypes.Camera_description], int]:
    offset = 0
    template = {}
    name, _, _ = data[offset:].partition(b'\0')
    offset += len(name) + 1
    template['name'] = str(name, encoding="utf-8")
    template['pos'] = NatNetTypes.Position.unpack(data[offset:(offset:=offset+12)])
    template['orientation'] = NatNetTypes.Quaternion.unpack(data[offset:(offset:=offset+16)])
    return {name:NatNetTypes.Camera_description(**template)}, offset

  @classmethod
  def unpack_marker_description(cls, data:bytes) -> Tuple[Dict[int, NatNetTypes.Marker_description], int]:
    offset = 0
    template = {}
    name, _, _ = data[offset:].partition(b'\0')
    offset += len(name) + 1
    template['name'] = str(name, encoding="utf-8")
    template['id'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    template['pos'] = NatNetTypes.Position.unpack(data[offset:(offset:=offset+12)])
    template['size'] = unpack('<f', data[offset:(offset:=offset+4)])[0]
    template['param'] = unpack( 'h', data[offset:(offset:=offset+2)])[0]
    return {template['id']:NatNetTypes.Marker_description(**template)}, offset

  @classmethod
  def unpack_asset_description(cls, data:bytes) -> Tuple[Dict[int, NatNetTypes.Asset_description], int]:
    offset = 0
    template = {}
    name, _, _ = data[offset:].partition(b'\0')
    offset += len(name) + 1
    template['name'] = str(name, encoding="utf-8")
    template['type'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    template['id'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    template['num_rigid_bodies'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    rigid_bodies = deque()
    for _ in range(template['num_rigid_bodies']):
      d, offset_tmp = cls.unpack_rigid_body_description(data[offset:])
      rigid_body = list(d.values())[0]
      rigid_bodies.append(rigid_body)
      offset += offset_tmp
    template['rigid_bodies'] = tuple(rigid_bodies)
    template['num_markers'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little',  signed=True)
    markers = deque()
    for _ in range(template['num_markers']):
      d,offset_tmp = cls.unpack_marker_description(data[offset:])
      marker = list(d.values())[0]
      markers.append(marker)
      offset += offset_tmp
    template['markers'] = tuple(markers)
    return {template['id']:NatNetTypes.Asset_description(**template)}, offset

class DataUnpackerV4_1(DataUnpackerV3_0):
  @classmethod
  def unpack_data_size(cls, data: bytes) -> Tuple[int, int]:
    offset = 0
    size_in_bytes = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    return size_in_bytes, offset

  @classmethod
  def unpack_asset_rigid_body(cls, data:bytes) -> Tuple[NatNetTypes.Asset_RB, int]:
    offset = 0
    template = {}
    template['id'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    template['pos'] = NatNetTypes.Position.unpack(data[offset:(offset:=offset+12)])
    template['rot'] = NatNetTypes.Quaternion.unpack(data[offset:(offset:=offset+16)])
    template['err'] = unpack('<f', data[offset:(offset:=offset+4)])[0]
    template['param'] = unpack( 'h', data[offset:(offset:=offset+2)])[0]
    return NatNetTypes.Asset_RB(**template), offset

  @classmethod
  def unpack_asset_marker(cls, data:bytes) -> Tuple[NatNetTypes.Asset_marker, int]:
    offset = 0
    template = {}
    template['id'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    template['pos'] = NatNetTypes.Position.unpack(data[offset:(offset:=offset+12)])
    template['size'] = unpack('<f', data[offset:(offset:=offset+4)])[0]
    template['param'] = unpack( 'h', data[offset:(offset:=offset+2)])[0]
    template['residual'] = unpack('<f', data[offset:(offset:=offset+4)])[0]
    return NatNetTypes.Asset_marker(**template),  offset

  @classmethod
  def unpack_asset(cls, data:bytes) -> Tuple[NatNetTypes.Asset, int]:
    offset = 0
    template = {}
    template['id'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    template['num_rigid_bodies'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    rigid_bodies = deque()
    for _ in range(template['num_rigid_bodies']):
      rigid_body, tmp_offset = cls.unpack_asset_rigid_body(data[offset:])
      offset += tmp_offset
      rigid_bodies.append(rigid_body)
    template['rigid_bodies'] = tuple(rigid_bodies)
    template['num_markers'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    markers = deque()
    for _ in range(template['num_markers']):
      marker, tmp_offset = cls.unpack_asset_marker(data[offset:])
      offset += tmp_offset
      markers.append(marker)
    template['markers'] = tuple(markers)
    return NatNetTypes.Asset(**template), offset

  @classmethod
  def unpack_asset_data(cls, data:bytes) -> Tuple[NatNetTypes.Asset_data, int]:
    offset = 0
    template = {}
    template['num_assets'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    _, tmp_offset = cls.unpack_data_size(data)
    offset += tmp_offset
    assets = deque()
    for _ in range(template['num_assets']):
      asset, tmp_offset = cls.unpack_asset(data[offset:])
      offset += tmp_offset
      assets.append(asset)
    template['assets'] = tuple(assets)
    return NatNetTypes.Asset_data(**template), offset

  @classmethod
  def unpack_frame_suffix_data(cls, data:bytes) -> Tuple[NatNetTypes.Frame_suffix, int]:
    offset = 0
    template = {}
    template['time_code'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    template['time_code_sub'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    template['timestamp'] = unpack('<d', data[offset:(offset:=offset+8)])[0]
    template['camera_mid_exposure'] = int.from_bytes(data[offset:(offset:=offset+8)], byteorder='little', signed=True)
    template['stamp_data'] = int.from_bytes(data[offset:(offset:=offset+8)], byteorder='little', signed=True)
    template['stamp_transmit'] = int.from_bytes(data[offset:(offset:=offset+8)], byteorder='little', signed=True)
    template['precision_timestamp_sec'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    template['precision_timestamp_frac_sec'] = int.from_bytes(data[offset:(offset:=offset+4)], byteorder='little', signed=True)
    param = unpack( 'h', data[offset:(offset:=offset+2)])[0]
    template['recording'] = bool(param & 0x01)
    template['tracked_models_changed'] = bool(param & 0x02)
    return NatNetTypes.Frame_suffix(**template), offset

  @classmethod
  def unpack_mocap_data(cls, data:bytes) -> Tuple[NatNetTypes.MoCap,int]:
    offset = 0
    tmp_offset = 0
    template = {}

    template['prefix_data'], tmp_offset = cls.unpack_frame_prefix_data(data[offset:])
    offset += tmp_offset

    template['marker_set_data'], tmp_offset = cls.unpack_marker_set_data(data[offset:])
    offset += tmp_offset

    template['legacy_marker_set_data'], tmp_offset = cls.unpack_legacy_other_markers(data[offset:])
    offset += tmp_offset

    template['rigid_body_data'], tmp_offset = cls.unpack_rigid_body_data(data[offset:])
    offset += tmp_offset

    template['skeleton_data'], tmp_offset = cls.unpack_skeleton_data(data[offset:])
    offset += tmp_offset

    template['asset_data'], tmp_offset = cls.unpack_asset_data(data[offset:])
    offset += tmp_offset

    template['labeled_marker_data'], tmp_offset = cls.unpack_labeled_marker_data(data[offset:])
    offset += tmp_offset

    template['force_plate_data'], tmp_offset = cls.unpack_force_plate_data(data[offset:])
    offset += tmp_offset

    template['device_data'], tmp_offset = cls.unpack_device_data(data[offset:])
    offset += tmp_offset

    template['suffix_data'], tmp_offset = cls.unpack_frame_suffix_data(data[offset:])
    offset += tmp_offset

    return NatNetTypes.MoCap(**template), offset

  @classmethod
  def unpack_rigid_body_description(cls, data: bytes) -> Tuple[Dict[int, NatNetTypes.Rigid_body_description], int]:
    d, offset = super().unpack_rigid_body_description(data)
    rb_desc = asdict(list(d.values())[0])
    markers = deque()
    for marker in rb_desc['markers']:
      template_marker = asdict(marker)
      name, _, _ = data[offset:].partition(b'\0')
      offset += len(name) + 1
      template_marker['name'] = str(name, encoding="utf-8")
      markers.append(NatNetTypes.RB_marker(**template_marker))
    rb_desc['markers'] = tuple(markers)
    return {rb_desc['id']:NatNetTypes.Rigid_body_description(**rb_desc)}, offset