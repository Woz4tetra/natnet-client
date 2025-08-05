from dataclasses import dataclass, field

from natnet_client.bytes_data import Position, Quaternion
from typing import Dict, Tuple


@dataclass(frozen=True)
class FramePrefix:
    frame_number: int


@dataclass
class MarkerData:
    name: str
    num_markers: int
    positions: Tuple[Position, ...]


@dataclass
class MarkerSetData:
    num_marker_sets: int
    marker_sets: Tuple[MarkerData, ...]
    marker_sets_d: Dict[str, MarkerData] = field(init=False)

    def __post_init__(self):
        object.__setattr__(
            self,
            "marker_sets_d",
            {instance.name: instance for instance in self.marker_sets},
        )


@dataclass
class LegacyMarkerSetData:
    num_markers: int
    positions: Tuple[Position, ...]


@dataclass
class RigidBody:
    identifier: int
    pos: Position
    rot: Quaternion
    err: float
    tracking: bool


@dataclass
class RigidBodyData:
    num_rigid_bodies: int
    rigid_bodies: Tuple[RigidBody, ...]
    rigid_bodies_d: Dict[int, RigidBody] = field(init=False)

    def __post_init__(self):
        object.__setattr__(
            self,
            "rigid_bodies_d",
            {instance.identifier: instance for instance in self.rigid_bodies},
        )


@dataclass
class Skeleton:
    identifier: int
    num_rigid_bodies: int
    rigid_bodies: Tuple[RigidBody, ...]
    rigid_bodies_d: Dict[int, RigidBody] = field(init=False)

    def __post_init__(self):
        object.__setattr__(
            self,
            "rigid_bodies_d",
            {instance.identifier: instance for instance in self.rigid_bodies},
        )


@dataclass
class SkeletonData:
    num_skeletons: int
    skeletons: Tuple[Skeleton, ...]


@dataclass
class AssetRigidBody:
    identifier: int
    pos: Position
    rot: Quaternion
    err: float
    param: int


@dataclass
class AssetMarker:
    identifier: int
    pos: Position
    size: float
    param: int
    residual: float


@dataclass
class Asset:
    identifier: int
    num_rigid_bodies: int
    rigid_bodies: Tuple[AssetRigidBody, ...]
    num_markers: int
    markers: Tuple[AssetMarker, ...]
    rigid_bodies_d: Dict[int, AssetRigidBody] = field(init=False)
    markers_d: Dict[int, AssetMarker] = field(init=False)

    def __post_init__(self):
        object.__setattr__(
            self,
            "rigid_bodies_d",
            {instance.identifier: instance for instance in self.rigid_bodies},
        )
        object.__setattr__(
            self,
            "markers_d",
            {instance.identifier: instance for instance in self.markers},
        )


@dataclass
class AssetData:
    num_assets: int
    assets: Tuple[Asset, ...]
    assets_d: Dict[int, Asset] = field(init=False)

    def __post_init__(self):
        object.__setattr__(
            self,
            "assets_d",
            {instance.identifier: instance for instance in self.assets},
        )


@dataclass
class LabeledMarker:
    identifier: int
    pos: Position
    size: int
    param: int
    residual: float


@dataclass
class LabeledMarkerData:
    num_markers: int
    markers: Tuple[LabeledMarker, ...]
    markers_d: Dict[int, LabeledMarker] = field(init=False)

    def __post_init__(self):
        object.__setattr__(
            self,
            "markers_d",
            {instance.identifier: instance for instance in self.markers},
        )


@dataclass
class Channel:
    num_frames: int
    frames: Tuple[float, ...]


@dataclass
class ForcePlate:
    identifier: int
    num_channels: int
    channels: Tuple[Channel, ...]


@dataclass
class ForcePlateData:
    num_force_plates: int
    force_plates: Tuple[ForcePlate, ...]
    force_plates_d: Dict[int, ForcePlate] = field(init=False)

    def __post_init__(self):
        object.__setattr__(
            self,
            "force_plates_d",
            {instance.identifier: instance for instance in self.force_plates},
        )


@dataclass
class Device:
    identifier: int
    num_channels: int
    channels: Tuple[Channel, ...]


@dataclass
class DeviceData:
    num_devices: int
    devices: Tuple[Device, ...]
    devices_d: Dict[int, Device] = field(init=False)

    def __post_init__(self):
        object.__setattr__(
            self,
            "devices_d",
            {instance.identifier: instance for instance in self.devices},
        )
