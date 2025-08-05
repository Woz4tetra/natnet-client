from typing import Dict, Tuple
from natnet_client.bytes_data import Position, Quaternion
from natnet_client.mo_cap_data import AssetData, DeviceData, ForcePlateData, FramePrefix, LabeledMarkerData, LegacyMarkerSetData, MarkerSetData, RigidBodyData, SkeletonData


from dataclasses import dataclass, field


@dataclass
class FrameSuffix:
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


@dataclass
class MoCapDescription:
    prefix_data: FramePrefix
    marker_set_data: MarkerSetData
    legacy_marker_set_data: LegacyMarkerSetData
    rigid_body_data: RigidBodyData
    skeleton_data: SkeletonData
    labeled_marker_data: LabeledMarkerData
    force_plate_data: ForcePlateData
    device_data: DeviceData
    suffix_data: FrameSuffix
    asset_data: AssetData | None = None


@dataclass
class MarkerSetDescription:
    name: str
    num_markers: int
    markers_names: Tuple[str, ...]


@dataclass
class RigidBodyMarker:
    name: str
    identifier: int
    pos: Position


@dataclass
class RigidBodyDescription:
    name: str
    identifier: int
    parent_id: int
    pos: Position
    num_markers: int
    markers: Tuple[RigidBodyMarker, ...]
    markers_d: Dict[int, RigidBodyMarker] = field(init=False)

    def __post_init__(self):
        object.__setattr__(
            self,
            "markers_d",
            {instance.identifier: instance for instance in self.markers},
        )


@dataclass
class SkeletonDescription:
    name: str
    identifier: int
    num_rigid_bodies: int
    rigid_bodies: Tuple[RigidBodyDescription, ...]
    rigid_bodies_d: Dict[int, RigidBodyDescription] = field(init=False)

    def __post_init__(self):
        object.__setattr__(
            self,
            "rigid_bodies_d",
            {instance.identifier: instance for instance in self.rigid_bodies},
        )


@dataclass
class ForcePlateDescription:
    identifier: int
    serial_number: str
    dimensions: Tuple[float, float]
    origin: Position
    calibration_matrix: Tuple[float, ...]
    corners: Tuple[float, ...]
    plate_type: int
    channel_data_type: int
    num_channels: int
    channels: Tuple[str, ...]


@dataclass
class DeviceDescription:
    identifier: int
    name: str
    serial_number: str
    type: int
    channel_type: int
    num_channels: int
    channels: Tuple[str, ...]


@dataclass
class CameraDescription:
    name: str
    pos: Position
    orientation: Quaternion


@dataclass
class MarkerDescription:
    name: str
    identifier: int
    pos: Position
    size: float
    param: int


@dataclass
class AssetDescription:
    name: str
    type: int
    identifier: int
    num_rigid_bodies: int
    rigid_bodies: Tuple[RigidBodyDescription, ...]
    num_markers: int
    markers: Tuple[MarkerDescription, ...]
    rigid_bodies_d: Dict[int, RigidBodyDescription] = field(init=False)

    def __post_init__(self):
        object.__setattr__(
            self,
            "rigid_bodies_d",
            {instance.identifier: instance for instance in self.rigid_bodies},
        )


@dataclass
class Descriptors:
    """
    Object for storing descriptions
    """

    marker_set_description: Dict[str, MarkerSetDescription] = field(
        init=False, default_factory=dict
    )
    rigid_body_description: Dict[int, RigidBodyDescription] = field(
        init=False, default_factory=dict
    )
    skeleton_description: Dict[int, SkeletonDescription] = field(
        init=False, default_factory=dict
    )
    force_plate_description: Dict[str, ForcePlateDescription] = field(
        init=False, default_factory=dict
    )
    device_description: Dict[str, DeviceDescription] = field(
        init=False, default_factory=dict
    )
    camera_description: Dict[str, CameraDescription] = field(
        init=False, default_factory=dict
    )
    asset_description: Dict[int, AssetDescription] = field(
        init=False, default_factory=dict
    )