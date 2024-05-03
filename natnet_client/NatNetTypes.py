from dataclasses import dataclass, field
import struct
from math import atan2, asin
from typing import Tuple
from enum import Enum

class NAT_Data(Enum):
  MARKER_SET     = 0
  RIGID_BODY    = 1
  SKELETON      = 2
  FORCE_PLATE   = 3
  DEVICE        = 4
  CAMERA        = 5
  ASSET         = 6
  UNDEFINED     = -1

  @classmethod
  def _missing_(cls, _: object):
    return cls.UNDEFINED

class NAT_Messages(Enum):
  # Client/server message ids
  CONNECT               = 0
  SERVER_INFO           = 1
  REQUEST               = 2
  RESPONSE              = 3
  REQUEST_MODEL_DEF     = 4
  MODEL_DEF             = 5
  REQUEST_FRAME_OF_DATA = 6
  FRAME_OF_DATA         = 7
  MESSAGE_STRING        = 8
  DISCONNECT            = 9
  KEEP_ALIVE            = 10
  UNRECOGNIZED_REQUEST  = 100
  UNDEFINED             = 999999

  @classmethod
  def _missing_(cls, _: object):
    return cls.UNDEFINED

class Data:
  @classmethod
  def unpack(cls, data:bytes):
    raise NotImplementedError("Subclasses must implement the unpack method")

@dataclass(frozen=True)
class Position(Data):
  x: float
  y: float
  z: float
  @classmethod
  def unpack(cls, data:bytes):
    return cls(*(struct.unpack('<fff', data)))

@dataclass(frozen=True)
class Quaternion(Data):
  x: float
  y: float
  z: float
  w: float
  roll: float = field(init=False, default=0.0)
  pitch: float = field(init=False, default=0.0)
  jaw: float = field(init=False, default=0.0)
  def __post_init__(self):
    object.__setattr__(self, "roll", atan2(2*(self.w*self.x + self.y*self.z), 1-2*(self.x**2 + self.y**2)))
    object.__setattr__(self, "pitch", asin(2*(self.w*self.y - self.x*self.z)))
    object.__setattr__(self, "jaw", atan2(2*(self.w*self.z + self.x*self.y), 1-2*(self.y**2 + self.z**2)))
  @classmethod
  def unpack(cls, data:bytes):
    return cls(*(struct.unpack('<ffff', data)))

class MoCapData:
  ...

@dataclass(frozen=True)
class Frame_prefix(MoCapData):
  frame_number: int

@dataclass(frozen=True)
class Marker_data:
  name: str
  num_markers: int
  positions: Tuple[Position, ...]

@dataclass(frozen=True)
class Marker_set_data(MoCapData):
  num_marker_sets: int
  marker_sets: Tuple[Marker_data, ...]

@dataclass(frozen=True)
class Legacy_marker_set_data(MoCapData):
  num_markers: int
  positions: Tuple[Position, ...]

@dataclass(frozen=True)
class Rigid_body:
  id: int
  pos: Position
  rot: Quaternion
  err: float
  tracking: bool

@dataclass(frozen=True)
class Rigid_body_data(MoCapData):
  num_rigid_bodies: int
  rigid_bodies: Tuple[Rigid_body, ...]

@dataclass(frozen=True)
class Skeleton:
  num_rigid_bodies: int
  rigid_bodies: Tuple[Rigid_body, ...]

@dataclass(frozen=True)
class Skeleton_data(MoCapData):
  num_skeletons: int
  skeletons: Tuple[Skeleton, ...]

@dataclass(frozen=True)
class Asset_RB:
  id: int
  pos: Position
  rot: Quaternion
  err: float
  param: int

@dataclass(frozen=True)
class Asset_marker:
  id: int
  pos: Position
  size: float
  param: int
  residual: float

@dataclass(frozen=True)
class Asset:
  id: int
  num_rigid_bodies: int
  rigid_bodies: Tuple[Asset_RB, ...]
  num_markers: int
  markers: Tuple[Asset_marker, ...]

@dataclass(frozen=True)
class Asset_data(MoCapData):
  num_assets: int
  assets: Tuple[Asset, ...]

@dataclass(frozen=True)
class Labeled_marker:
  id: int
  pos: Position
  size: int
  param: int
  residual: float

@dataclass(frozen=True)
class Labeled_marker_data(MoCapData):
  num_markers: int
  markers: Tuple[Labeled_marker, ...]

@dataclass(frozen=True)
class Channel:
  num_frames: int
  frames: Tuple[float, ...]

@dataclass(frozen=True)
class Force_plate:
  id: int
  num_channels: int
  channels: Tuple[Channel, ...]

@dataclass(frozen=True)
class Force_plate_data(MoCapData):
  num_force_plates: int
  force_plates: Tuple[Force_plate, ...]

@dataclass(frozen=True)
class Device:
  id: int
  num_channels: int
  channels: Tuple[Channel, ...]

@dataclass(frozen=True)
class Device_data(MoCapData):
  num_devices: int
  devices: Tuple[Device, ...]

@dataclass(frozen=True)
class Frame_suffix:
  time_code: int
  time_code_sub: int
  timestamp: float
  camera_mid_exposure: int
  stamp_data: int
  stamp_transmit: int
  recording: bool
  tracked_models_changed: bool
  precision_timestamp_sec: int | None = None
  precision_timestamp_frac_sec: int | None = None

@dataclass(frozen=True)
class MoCap:
  prefix_data: Frame_prefix
  marker_set_data: Marker_set_data
  legacy_marker_set_data: Legacy_marker_set_data
  rigid_body_data: Rigid_body_data
  skeleton_data: Skeleton_data
  labeled_marker_data: Labeled_marker_data
  force_plate_data: Force_plate_data
  device_data: Device_data
  suffix_data: Frame_suffix
  asset_data: Asset_data | None = None

class Descriptor:
  ...

@dataclass(frozen=True)
class Marker_set_description(Descriptor):
  name: str
  num_markers:int
  markers_names: Tuple[str, ...]

@dataclass(frozen=True)
class RB_marker:
  name:str
  id: int
  pos: Position

@dataclass(frozen=True)
class Rigid_body_description(Descriptor):
  name: str
  id: int
  parent_id: int
  pos: Position
  num_markers:int
  markers: Tuple[RB_marker, ...]

@dataclass(frozen=True)
class Skeleton_description(Descriptor):
  name: str
  id: int
  num_rigid_bodies: int
  rigid_bodies: Tuple[Rigid_body_description, ...]

@dataclass(frozen=True)
class Force_plate_description(Descriptor):
  id:int
  serial_number: str
  dimensions: Tuple[float, float]
  origin: Position
  calibration_matrix: Tuple[float, ...]
  corners: Tuple[float, ...]
  plate_type: int
  channel_data_type: int
  num_channels: int
  channels: Tuple[str, ...]

@dataclass(frozen=True)
class Device_description(Descriptor):
  id: int
  name: str
  serial_number: str
  type: int
  channel_type: int
  num_channels: int
  channels: Tuple[str, ...]

@dataclass(frozen=True)
class Camera_description(Descriptor):
  name: str
  pos: Position
  orientation: Quaternion

@dataclass(frozen=True)
class Marker_description(Descriptor):
  name: str
  id: int
  pos: Position
  size: float
  param: int

@dataclass(frozen=True)
class Asset_description(Descriptor):
  name: str
  type: int
  id: int
  num_rigid_bodies: int
  rigid_bodies: Tuple[Rigid_body_description, ...]
  num_markers: int
  markers: Tuple