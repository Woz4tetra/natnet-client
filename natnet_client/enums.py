from enum import Enum


class NatData(Enum):
    MARKER_SET = 0
    RIGID_BODY = 1
    SKELETON = 2
    FORCE_PLATE = 3
    DEVICE = 4
    CAMERA = 5
    ASSET = 6
    UNDEFINED = -1

    @classmethod
    def _missing_(cls, value):
        return cls.UNDEFINED


class NatMessages(Enum):
    # Client/server message ids
    CONNECT = 0
    SERVER_INFO = 1
    REQUEST = 2
    RESPONSE = 3
    REQUEST_MODEL_DEF = 4
    MODEL_DEF = 5
    REQUEST_FRAME_OF_DATA = 6
    FRAME_OF_DATA = 7
    MESSAGE_STRING = 8
    DISCONNECT = 9
    KEEP_ALIVE = 10
    UNRECOGNIZED_REQUEST = 100
    UNDEFINED = 999999

    @classmethod
    def _missing_(cls, value):
        return cls.UNDEFINED