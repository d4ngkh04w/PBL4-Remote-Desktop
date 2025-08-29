import struct
import pickle
import lz4.frame as lz4
from typing import Union
from packet import ImagePacket, KeyBoardPacket, MousePacket

HEADER_FORMAT = "!IH"  # Length (4 bytes) + Type (2 bytes)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


def serialize_packet(packet: Union[ImagePacket, KeyBoardPacket, MousePacket]) -> bytes:
    """
    Đóng gói gói tin

    :param packet: Gói tin cần đóng gói
    :return: Dữ liệu đã đóng gói
    """
    payload = pickle.dumps(packet)
    length = len(payload)
    header = struct.pack(HEADER_FORMAT, length, packet.packet_type.value)

    return header + lz4.compress(payload)
