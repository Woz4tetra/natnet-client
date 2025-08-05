import itertools
from typing import Iterable, Tuple, Dict
from collections import deque
from struct import unpack
import logging

from natnet_client.bytes_data import Position, Quaternion
from natnet_client.mo_cap_data import (
    FramePrefix,
    MarkerData,
    MarkerSetData,
    LegacyMarkerSetData,
    RigidBody,
    RigidBodyData,
    Skeleton,
    SkeletonData,
    AssetRigidBody,
    AssetMarker,
    Asset,
    AssetData,
    LabeledMarker,
    LabeledMarkerData,
    Channel,
    ForcePlate,
    ForcePlateData,
    Device,
    DeviceData,
)
from natnet_client.descriptors import (
    FrameSuffix,
    MoCapDescription,
    MarkerSetDescription,
    RigidBodyMarker,
    RigidBodyDescription,
    SkeletonDescription,
    ForcePlateDescription,
    DeviceDescription,
    CameraDescription,
    MarkerDescription,
    AssetDescription,
    Descriptors,
)
from natnet_client.enums import NatData

logger = logging.getLogger("NatNet-Unpacker")


def batched(iterable: Iterable[int], n: int) -> Iterable[Tuple[int, ...]]:
    """Yield successive n-sized chunks from iterable."""
    it = iter(iterable)
    while chunk := tuple(itertools.islice(it, n)):
        yield chunk


class DataUnpackerV3_0:
    rigid_body_length: int = 38
    marker_length: int = 26
    frame_suffix_length: int = 42

    @classmethod
    def unpack_data_size(cls, data: bytes) -> Tuple[int, int]:
        return 0, 0

    @classmethod
    def unpack_frame_prefix_data(cls, data: bytes) -> Tuple[FramePrefix, int]:
        offset = 0
        prefix = FramePrefix(
            int.from_bytes(
                data[offset : (offset := offset + 4)], byteorder="little", signed=True
            )
        )
        return prefix, offset

    @classmethod
    def unpack_marker_set_data(cls, data: bytes) -> Tuple[MarkerSetData, int]:
        offset = 0
        num_marker_sets = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        _, tmp_offset = cls.unpack_data_size(data)
        offset += tmp_offset
        markers: deque[MarkerData] = deque()
        for _ in range(num_marker_sets):
            name_bytes, _, _ = data[offset:].partition(b"\0")
            offset += len(name_bytes) + 1
            name = str(name_bytes, encoding="utf-8")
            num_markers = int.from_bytes(
                data[offset : (offset := offset + 4)], byteorder="little", signed=True
            )
            positions = tuple(
                map(
                    lambda position_data: Position.unpack(bytes(position_data)),
                    batched(data[offset : (offset := offset + (12 * num_markers))], 12),
                )
            )
            markers.append(MarkerData(name, num_markers, positions))
        return MarkerSetData(num_marker_sets, tuple(markers)), offset

    @classmethod
    def unpack_legacy_other_markers(
        cls, data: bytes
    ) -> Tuple[LegacyMarkerSetData, int]:
        offset = 0
        num_markers = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        _, tmp_offset = cls.unpack_data_size(data)
        offset += tmp_offset
        positions = deque(
            map(
                lambda position_data: Position.unpack(bytes(position_data)),
                batched(data[offset : (offset := offset + (12 * num_markers))], 12),
            )
        )
        return LegacyMarkerSetData(num_markers, tuple(positions)), offset

    @classmethod
    def unpack_rigid_body(cls, data: bytes) -> RigidBody:
        offset = 0
        identifier = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        pos = Position.unpack(data[offset : (offset := offset + 12)])
        rot = Quaternion.unpack(data[offset : (offset := offset + 16)])
        err = unpack("<f", data[offset : (offset := offset + 4)])[0]
        param: int = unpack("h", data[offset : (offset := offset + 2)])[0]
        tracking = bool(param & 0x01)
        return RigidBody(identifier, pos, rot, err, tracking)

    @classmethod
    def unpack_rigid_body_data(cls, data: bytes) -> Tuple[RigidBodyData, int]:
        offset = 0
        num_rigid_bodies = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        _, tmp_offset = cls.unpack_data_size(data)
        offset += tmp_offset
        rigid_bodies = tuple(
            map(
                lambda rigid_body_data: cls.unpack_rigid_body(bytes(rigid_body_data)),
                batched(
                    data[
                        offset : (
                            offset := offset
                            + (cls.rigid_body_length * num_rigid_bodies)
                        )
                    ],
                    cls.rigid_body_length,
                ),
            )
        )
        return RigidBodyData(num_rigid_bodies, rigid_bodies), offset

    @classmethod
    def unpack_skeleton(cls, data: bytes) -> Tuple[Skeleton, int]:
        offset = 0
        identifier = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        num_rigid_bodies = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        rigid_bodies = tuple(
            map(
                lambda rigid_body_data: cls.unpack_rigid_body(bytes(rigid_body_data)),
                batched(
                    data[
                        offset : (
                            offset := offset
                            + (cls.rigid_body_length * num_rigid_bodies)
                        )
                    ],
                    cls.rigid_body_length,
                ),
            )
        )
        return Skeleton(identifier, num_rigid_bodies, rigid_bodies), offset

    @classmethod
    def unpack_skeleton_data(cls, data: bytes) -> Tuple[SkeletonData, int]:
        offset = 0
        num_skeletons = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        _, tmp_offset = cls.unpack_data_size(data)
        offset += tmp_offset
        skeletons: deque[Skeleton] = deque()
        for _ in range(num_skeletons):
            skeleton, tmp_offset = cls.unpack_skeleton(data[offset:])
            offset += tmp_offset
            skeletons.append(skeleton)
        return SkeletonData(num_skeletons, tuple(skeletons)), offset

    @classmethod
    def unpack_asset_rigid_body(cls, data: bytes) -> AssetRigidBody:
        raise NotImplementedError("Subclasses must implement the unpack method")

    @classmethod
    def unpack_asset_marker(cls, data: bytes) -> AssetMarker:
        raise NotImplementedError("Subclasses must implement the unpack method")

    @classmethod
    def unpack_asset(cls, data: bytes) -> Tuple[Asset, int]:
        raise NotImplementedError("Subclasses must implement the unpack method")

    @classmethod
    def unpack_asset_data(cls, data: bytes) -> Tuple[AssetData, int]:
        raise NotImplementedError("Subclasses must implement the unpack method")

    @classmethod
    def decode_marker_id(cls, identifier: int) -> Tuple[int, int]:
        return (identifier >> 16, identifier & 0x0000FFFF)

    @classmethod
    def unpack_labeled_marker(cls, data: bytes) -> LabeledMarker:
        offset = 0
        identifier = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        pos = Position.unpack(data[offset : (offset := offset + 12)])
        size = unpack("<f", data[offset : (offset := offset + 4)])[0]
        param = unpack("h", data[offset : (offset := offset + 2)])[0]
        residual = unpack("<f", data[offset : (offset := offset + 4)])[0] * 1000.0
        return LabeledMarker(identifier, pos, size, param, residual)

    @classmethod
    def unpack_labeled_marker_data(cls, data: bytes) -> Tuple[LabeledMarkerData, int]:
        offset = 0
        num_markers = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        _, tmp_offset = cls.unpack_data_size(data)
        offset += tmp_offset
        markers = tuple(
            map(
                lambda marker_data: cls.unpack_labeled_marker(bytes(marker_data)),
                batched(
                    data[
                        offset : (offset := offset + (cls.marker_length * num_markers))
                    ],
                    cls.marker_length,
                ),
            )
        )
        return LabeledMarkerData(num_markers, markers), offset

    @classmethod
    def unpack_channels(
        cls, data: bytes, num_channels: int
    ) -> Tuple[Tuple[Channel, ...], int]:
        offset = 0
        channels: deque[Channel] = deque()
        for _ in range(num_channels):
            num_frames = int.from_bytes(
                data[offset : (offset := offset + 4)], byteorder="little", signed=True
            )
            frames = tuple(
                map(
                    lambda frame_data: unpack("<f", bytes(frame_data))[0],
                    batched(data[offset : (offset := offset + (4 * num_frames))], 4),
                )
            )
            channels.append(Channel(num_frames, frames))
        return tuple(channels), offset

    @classmethod
    def unpack_force_plate_data(cls, data: bytes) -> Tuple[ForcePlateData, int]:
        offset = 0
        num_force_plates = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        _, tmp_offset = cls.unpack_data_size(data)
        offset += tmp_offset
        force_plates: deque[ForcePlate] = deque()
        for _ in range(num_force_plates):
            identifier = int.from_bytes(
                data[offset : (offset := offset + 4)], byteorder="little", signed=True
            )
            num_channels = int.from_bytes(
                data[offset : (offset := offset + 4)], byteorder="little", signed=True
            )
            channels, tmp_offset = cls.unpack_channels(data[offset:], num_channels)
            offset += tmp_offset
            force_plates.append(ForcePlate(identifier, num_channels, channels))
        return (
            ForcePlateData(num_force_plates, tuple(force_plates)),
            offset,
        )

    @classmethod
    def unpack_device_data(cls, data: bytes) -> Tuple[DeviceData, int]:
        offset = 0
        num_devices = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        _, tmp_offset = cls.unpack_data_size(data)
        offset += tmp_offset
        devices: deque[Device] = deque()
        for _ in range(num_devices):
            identifier = int.from_bytes(
                data[offset : (offset := offset + 4)], byteorder="little", signed=True
            )
            num_channels = int.from_bytes(
                data[offset : (offset := offset + 4)], byteorder="little", signed=True
            )
            channels, tmp_offset = cls.unpack_channels(data[offset:], num_channels)
            offset += tmp_offset
            devices.append(Device(identifier, num_channels, channels))
        return DeviceData(num_devices, tuple(devices)), offset

    @classmethod
    def unpack_frame_suffix_data(cls, data: bytes) -> FrameSuffix:
        offset = 0
        time_code = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        time_code_sub = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        timestamp = unpack("<d", data[offset : (offset := offset + 8)])[0]
        camera_mid_exposure = int.from_bytes(
            data[offset : (offset := offset + 8)], byteorder="little", signed=True
        )
        stamp_data = int.from_bytes(
            data[offset : (offset := offset + 8)], byteorder="little", signed=True
        )
        stamp_transmit = int.from_bytes(
            data[offset : (offset := offset + 8)], byteorder="little", signed=True
        )
        param = unpack("h", data[offset : (offset := offset + 2)])[0]
        recording = bool(param & 0x01)
        tracked_models_changed = bool(param & 0x02)
        return FrameSuffix(
            time_code,
            time_code_sub,
            timestamp,
            camera_mid_exposure,
            stamp_data,
            stamp_transmit,
            recording,
            tracked_models_changed,
        )

    @classmethod
    def unpack_mocap_data(cls, data: bytes) -> MoCapDescription:
        offset = 0
        tmp_offset = 0

        prefix_data, tmp_offset = cls.unpack_frame_prefix_data(data[offset:])
        offset += tmp_offset

        marker_set_data, tmp_offset = cls.unpack_marker_set_data(data[offset:])
        offset += tmp_offset

        legacy_marker_set_data, tmp_offset = cls.unpack_legacy_other_markers(
            data[offset:]
        )
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

        return MoCapDescription(
            prefix_data,
            marker_set_data,
            legacy_marker_set_data,
            rigid_body_data,
            skeleton_data,
            labeled_marker_data,
            force_plate_data,
            device_data,
            suffix_data,
        )

    @classmethod
    def unpack_marker_set_description(
        cls, data: bytes
    ) -> Tuple[Dict[str, MarkerSetDescription], int]:
        offset = 0
        name_bytes, _, _ = data[offset:].partition(b"\0")
        offset += len(name_bytes) + 1
        name = str(name_bytes, encoding="utf-8")
        num_markers = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        markers_names: deque[str] = deque()
        for _ in range(num_markers):
            marker_name, _, _ = data[offset:].partition(b"\0")
            offset += len(marker_name) + 1
            markers_names.append(str(marker_name, encoding="utf-8"))
        return {
            name: MarkerSetDescription(name, num_markers, tuple(markers_names))
        }, offset

    @classmethod
    def unpack_rigid_body_description(
        cls, data: bytes
    ) -> Tuple[Dict[int, RigidBodyDescription], int]:
        offset = 0
        name_bytes, _, _ = data[offset:].partition(b"\0")
        offset += len(name_bytes) + 1
        name = str(name_bytes, encoding="utf-8")
        identifier = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        parent_id = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        pos = Position.unpack(data[offset : (offset := offset + 12)])
        num_markers = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        offset_pos = offset
        offset_id = offset_pos + (12 * num_markers)
        offset_name = offset_id + (4 * num_markers)
        marker_name = ""
        markers: deque[RigidBodyMarker] = deque()
        for _ in range(num_markers):
            marker_pos = Position.unpack(
                data[offset_pos : (offset_pos := offset_pos + 12)]
            )
            marker_id = int.from_bytes(
                data[offset_id : (offset_id := offset_id + 4)],
                byteorder="little",
                signed=True,
            )
            markers.append(RigidBodyMarker(marker_name, marker_id, marker_pos))
        return {
            identifier: RigidBodyDescription(
                name, identifier, parent_id, pos, num_markers, tuple(markers)
            )
        }, offset_name

    @classmethod
    def unpack_skeleton_description(
        cls, data: bytes
    ) -> Tuple[Dict[int, SkeletonDescription], int]:
        offset = 0
        name_bytes, _, _ = data[offset:].partition(b"\0")
        offset += len(name_bytes) + 1
        name = str(name_bytes, encoding="utf-8")
        identifier = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        num_rigid_bodies = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        rigid_bodies: deque[RigidBodyDescription] = deque()
        for _ in range(num_rigid_bodies):
            d, offset_tmp = cls.unpack_rigid_body_description(data[offset:])
            rigid_body = list(d.values())[0]
            rigid_bodies.append(rigid_body)
            offset += offset_tmp
        return {
            identifier: SkeletonDescription(
                name, identifier, num_rigid_bodies, tuple(rigid_bodies)
            )
        }, offset

    @classmethod
    def unpack_force_plate_description(
        cls, data: bytes
    ) -> Tuple[Dict[str, ForcePlateDescription], int]:
        offset = 0
        identifier = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )

        serial_number_bytes, _, _ = data[offset:].partition(b"\0")
        offset += len(serial_number_bytes) + 1
        serial_number = str(serial_number_bytes, encoding="utf-8")

        f_width: float = unpack("<f", data[offset : (offset := offset + 4)])[0]
        f_length: float = unpack("<f", data[offset : (offset := offset + 4)])[0]
        dimensions = (f_width, f_length)

        origin = Position.unpack(data[offset : (offset := offset + 12)])

        # Not tested
        calibration_matrix = tuple(
            unpack("<f", data[offset : (offset := offset + 4)])[0]
            for _ in range(12 * 12)
        )
        corners = tuple(
            unpack("<f", data[offset : (offset := offset + 4)])[0] for _ in range(4 * 3)
        )

        plate_type = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        channel_data_type = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        num_channels = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )

        channels: deque[str] = deque()
        for _ in range(num_channels):
            channel_name, _, _ = data[offset:].partition(b"\0")
            offset += len(channel_name) + 1
            channels.append(str(channel_name, encoding="utf-8"))
        return {
            serial_number: ForcePlateDescription(
                identifier,
                serial_number,
                dimensions,
                origin,
                calibration_matrix,
                corners,
                plate_type,
                channel_data_type,
                num_channels,
                tuple(channels),
            )
        }, offset

    @classmethod
    def unpack_device_description(
        cls, data: bytes
    ) -> Tuple[Dict[str, DeviceDescription], int]:
        offset = 0

        identifier = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )

        name_bytes, _, _ = data[offset:].partition(b"\0")
        offset += len(name_bytes) + 1
        name = str(name_bytes, encoding="utf-8")

        serial_number_bytes, _, _ = data[offset:].partition(b"\0")
        offset += len(serial_number_bytes) + 1
        serial_number = str(serial_number_bytes, encoding="utf-8")

        device_type = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        channel_data_type = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        num_channels = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        channels: deque[str] = deque()
        for _ in range(num_channels):
            channel_name, _, _ = data[offset:].partition(b"\0")
            offset += len(channel_name) + 1
            channels.append(str(channel_name, encoding="utf-8"))
        return {
            serial_number: DeviceDescription(
                identifier,
                name,
                serial_number,
                device_type,
                channel_data_type,
                num_channels,
                tuple(channels),
            )
        }, offset

    @classmethod
    def unpack_camera_description(
        cls, data: bytes
    ) -> Tuple[Dict[str, CameraDescription], int]:
        offset = 0
        name_bytes, _, _ = data[offset:].partition(b"\0")
        offset += len(name_bytes) + 1
        name = str(name_bytes, encoding="utf-8")
        pos = Position.unpack(data[offset : (offset := offset + 12)])
        orientation = Quaternion.unpack(data[offset : (offset := offset + 16)])
        return {name: CameraDescription(name, pos, orientation)}, offset

    @classmethod
    def unpack_marker_description(
        cls, data: bytes
    ) -> Tuple[Dict[int, MarkerDescription], int]:
        offset = 0
        name_bytes, _, _ = data[offset:].partition(b"\0")
        offset += len(name_bytes) + 1
        name = str(name_bytes, encoding="utf-8")
        identifier = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        pos = Position.unpack(data[offset : (offset := offset + 12)])
        size = unpack("<f", data[offset : (offset := offset + 4)])[0]
        param = unpack("h", data[offset : (offset := offset + 2)])[0]
        return {
            identifier: MarkerDescription(name, identifier, pos, size, param)
        }, offset

    @classmethod
    def unpack_asset_description(
        cls, data: bytes
    ) -> Tuple[Dict[int, AssetDescription], int]:
        offset = 0
        name_bytes, _, _ = data[offset:].partition(b"\0")
        offset += len(name_bytes) + 1
        name = str(name_bytes, encoding="utf-8")
        asset_type = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        identifier = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        num_rigid_bodies = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        rigid_bodies: deque[RigidBodyDescription] = deque()
        for _ in range(num_rigid_bodies):
            d_r, offset_tmp = cls.unpack_rigid_body_description(data[offset:])
            rigid_body = list(d_r.values())[0]
            rigid_bodies.append(rigid_body)
            offset += offset_tmp
        num_markers = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        markers: deque[MarkerDescription] = deque()
        for _ in range(num_markers):
            d_m, offset_tmp = cls.unpack_marker_description(data[offset:])
            marker = list(d_m.values())[0]
            markers.append(marker)
            offset += offset_tmp
        return {
            identifier: AssetDescription(
                name,
                asset_type,
                identifier,
                num_rigid_bodies,
                tuple(rigid_bodies),
                num_markers,
                tuple(markers),
            )
        }, offset

    @classmethod
    def unpack_descriptors(cls, data: bytes) -> Descriptors:
        descriptors = Descriptors()
        offset = 0
        tmp_offset = 0
        dataset_count = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        size_in_bytes = -1
        for _ in range(dataset_count):
            tag = int.from_bytes(
                data[offset : (offset := offset + 4)], byteorder="little", signed=True
            )
            data_description_type = NatData(tag)
            if data_description_type is NatData.MARKER_SET:
                marker_set_description, tmp_offset = cls.unpack_marker_set_description(
                    data[offset:]
                )
                descriptors.marker_set_description.update(marker_set_description)
            elif data_description_type is NatData.RIGID_BODY:
                rigid_body_description, tmp_offset = cls.unpack_rigid_body_description(
                    data[offset:]
                )
                descriptors.rigid_body_description.update(rigid_body_description)
            elif data_description_type is NatData.SKELETON:
                skeleton_description, tmp_offset = cls.unpack_skeleton_description(
                    data[offset:]
                )
                descriptors.skeleton_description.update(skeleton_description)
            elif data_description_type is NatData.FORCE_PLATE:
                force_plate_description, tmp_offset = (
                    cls.unpack_force_plate_description(data[offset:])
                )
                descriptors.force_plate_description.update(force_plate_description)
            elif data_description_type is NatData.DEVICE:
                device_description, tmp_offset = cls.unpack_device_description(
                    data[offset:]
                )
                descriptors.device_description.update(device_description)
            elif data_description_type is NatData.CAMERA:
                camera_description, tmp_offset = cls.unpack_camera_description(
                    data[offset:]
                )
                descriptors.camera_description.update(camera_description)
            elif data_description_type is NatData.ASSET:
                asset_description, tmp_offset = cls.unpack_asset_description(
                    data[offset:]
                )
                descriptors.asset_description.update(asset_description)
            elif data_description_type is NatData.UNDEFINED:
                logger.error(f"ID: {tag} - Size: {size_in_bytes}")
                continue
            offset += tmp_offset
        return descriptors


class DataUnpackerV4_1(DataUnpackerV3_0):
    asset_rigid_body_length: int = 38
    asset_marker_length: int = 26
    frame_suffix_length: int = 50

    @classmethod
    def unpack_data_size(cls, data: bytes) -> Tuple[int, int]:
        offset = 0
        size_in_bytes = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        return size_in_bytes, offset

    @classmethod
    def unpack_asset_rigid_body(cls, data: bytes) -> AssetRigidBody:
        offset = 0
        identifier = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        pos = Position.unpack(data[offset : (offset := offset + 12)])
        rot = Quaternion.unpack(data[offset : (offset := offset + 16)])
        err = unpack("<f", data[offset : (offset := offset + 4)])[0]
        param = unpack("h", data[offset : (offset := offset + 2)])[0]
        return AssetRigidBody(identifier, pos, rot, err, param)

    @classmethod
    def unpack_asset_marker(cls, data: bytes) -> AssetMarker:
        offset = 0
        identifier = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        pos = Position.unpack(data[offset : (offset := offset + 12)])
        size = unpack("<f", data[offset : (offset := offset + 4)])[0]
        param = unpack("h", data[offset : (offset := offset + 2)])[0]
        residual = unpack("<f", data[offset : (offset := offset + 4)])[0]
        return AssetMarker(identifier, pos, size, param, residual)

    @classmethod
    def unpack_asset(cls, data: bytes) -> Tuple[Asset, int]:
        offset = 0
        identifier = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        num_rigid_bodies = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        rigid_bodies = tuple(
            map(
                lambda rigid_body_data: cls.unpack_asset_rigid_body(
                    bytes(rigid_body_data)
                ),
                batched(
                    data[
                        offset : (
                            offset := offset
                            + (cls.asset_rigid_body_length * num_rigid_bodies)
                        )
                    ],
                    cls.asset_rigid_body_length,
                ),
            )
        )
        num_markers = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        markers = tuple(
            map(
                lambda marker_data: cls.unpack_asset_marker(bytes(marker_data)),
                batched(
                    data[
                        offset : (
                            offset := offset + (cls.asset_marker_length * num_markers)
                        )
                    ],
                    cls.asset_marker_length,
                ),
            )
        )
        return (
            Asset(identifier, num_rigid_bodies, rigid_bodies, num_markers, markers),
            offset,
        )

    @classmethod
    def unpack_asset_data(cls, data: bytes) -> Tuple[AssetData, int]:
        offset = 0
        num_assets = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        _, tmp_offset = cls.unpack_data_size(data)
        offset += tmp_offset
        assets: deque[Asset] = deque()
        for _ in range(num_assets):
            asset, tmp_offset = cls.unpack_asset(data[offset:])
            offset += tmp_offset
            assets.append(asset)
        return AssetData(num_assets, tuple(assets)), offset

    @classmethod
    def unpack_frame_suffix_data(cls, data: bytes) -> FrameSuffix:
        offset = 0
        time_code = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        time_code_sub = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        timestamp = unpack("<d", data[offset : (offset := offset + 8)])[0]
        camera_mid_exposure = int.from_bytes(
            data[offset : (offset := offset + 8)], byteorder="little", signed=True
        )
        stamp_data = int.from_bytes(
            data[offset : (offset := offset + 8)], byteorder="little", signed=True
        )
        stamp_transmit = int.from_bytes(
            data[offset : (offset := offset + 8)], byteorder="little", signed=True
        )
        precision_timestamp_sec = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        precision_timestamp_frac_sec = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        param = unpack("h", data[offset : (offset := offset + 2)])[0]
        recording = bool(param & 0x01)
        tracked_models_changed = bool(param & 0x02)
        return FrameSuffix(
            time_code,
            time_code_sub,
            timestamp,
            camera_mid_exposure,
            stamp_data,
            stamp_transmit,
            recording,
            tracked_models_changed,
            precision_timestamp_sec,
            precision_timestamp_frac_sec,
        )

    @classmethod
    def unpack_mocap_data(cls, data: bytes) -> MoCapDescription:
        offset = 0
        tmp_offset = 0

        prefix_data, tmp_offset = cls.unpack_frame_prefix_data(data[offset:])
        offset += tmp_offset

        marker_set_data, tmp_offset = cls.unpack_marker_set_data(data[offset:])
        offset += tmp_offset

        legacy_marker_set_data, tmp_offset = cls.unpack_legacy_other_markers(
            data[offset:]
        )
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

        return MoCapDescription(
            prefix_data,
            marker_set_data,
            legacy_marker_set_data,
            rigid_body_data,
            skeleton_data,
            labeled_marker_data,
            force_plate_data,
            device_data,
            suffix_data,
            asset_data,
        )

    @classmethod
    def unpack_rigid_body_description(
        cls, data: bytes
    ) -> Tuple[Dict[int, RigidBodyDescription], int]:
        d, offset = super().unpack_rigid_body_description(data)
        rb_desc = tuple(d.values())[0]
        for marker in rb_desc.markers:
            name, _, _ = data[offset:].partition(b"\0")
            offset += len(name) + 1
            marker.name = str(name, encoding="utf-8")
        return d, offset

    @classmethod
    def unpack_descriptors(cls, data: bytes) -> Descriptors:
        descriptors = Descriptors()
        offset = 0
        tmp_offset = 0
        dataset_count = int.from_bytes(
            data[offset : (offset := offset + 4)], byteorder="little", signed=True
        )
        for _ in range(dataset_count):
            tag = int.from_bytes(
                data[offset : (offset := offset + 4)], byteorder="little", signed=True
            )
            data_description_type = NatData(tag)
            size_in_bytes = int.from_bytes(
                data[offset : (offset := offset + 4)], byteorder="little", signed=True
            )
            if data_description_type is NatData.MARKER_SET:
                marker_set_description, tmp_offset = cls.unpack_marker_set_description(
                    data[offset:]
                )
                descriptors.marker_set_description.update(marker_set_description)
            elif data_description_type is NatData.RIGID_BODY:
                rigid_body_description, tmp_offset = cls.unpack_rigid_body_description(
                    data[offset:]
                )
                descriptors.rigid_body_description.update(rigid_body_description)
            elif data_description_type is NatData.SKELETON:
                skeleton_description, tmp_offset = cls.unpack_skeleton_description(
                    data[offset:]
                )
                descriptors.skeleton_description.update(skeleton_description)
            elif data_description_type is NatData.FORCE_PLATE:
                force_plate_description, tmp_offset = (
                    cls.unpack_force_plate_description(data[offset:])
                )
                descriptors.force_plate_description.update(force_plate_description)
            elif data_description_type is NatData.DEVICE:
                device_description, tmp_offset = cls.unpack_device_description(
                    data[offset:]
                )
                descriptors.device_description.update(device_description)
            elif data_description_type is NatData.CAMERA:
                camera_description, tmp_offset = cls.unpack_camera_description(
                    data[offset:]
                )
                descriptors.camera_description.update(camera_description)
            elif data_description_type is NatData.ASSET:
                asset_description, tmp_offset = cls.unpack_asset_description(
                    data[offset:]
                )
                descriptors.asset_description.update(asset_description)
            elif data_description_type is NatData.UNDEFINED:
                logger.error(f"ID: {tag} - Size: {size_in_bytes}")
                continue
            offset += tmp_offset
        return descriptors
