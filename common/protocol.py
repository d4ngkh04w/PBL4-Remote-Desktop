import socket
from typing import Union
from common.packet import ImagePacket, KeyBoardPacket, MousePacket
import struct, pickle
import lz4.frame as lz4
from common.enum import PacketType
from common.safe_deserializer import SafeDeserializer


class Protocol:
    _HEADER_FORMAT = "!IH"
    _HEADER_SIZE = struct.calcsize(_HEADER_FORMAT)

    @staticmethod
    def _receive(sock: socket.socket, n: int) -> bytes:
        """
        Nhận dữ liệu từ socket
        """
        data = b""
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Connection closed unexpectedly")
            data += chunk
        return data

    @classmethod
    def send_packet(
        cls,
        sock: socket.socket,
        packet: Union[ImagePacket, KeyBoardPacket, MousePacket],
    ) -> None:
        """
        Gửi gói tin
        """
        payload = pickle.dumps(packet)
        compressed_payload = lz4.compress(payload)
        length = len(compressed_payload)
        header = struct.pack(cls._HEADER_FORMAT, length, packet.packet_type.value)
        sock.sendall(header + compressed_payload)

    @classmethod
    def receive_packet(
        cls,
        sock: socket.socket,
    ) -> Union[ImagePacket, KeyBoardPacket, MousePacket]:
        """
        Nhận gói tin
        """
        header = cls._receive(sock, cls._HEADER_SIZE)
        length, packet_type = struct.unpack(cls._HEADER_FORMAT, header)

        if length < 0:
            raise ValueError("Invalid packet length")

        valid_packet_types = {
            PacketType.IMAGE.value,
            PacketType.KEYBOARD.value,
            PacketType.MOUSE.value,
        }

        if packet_type not in valid_packet_types:
            raise ValueError(f"Invalid packet type: {packet_type}")

        compressed_payload = cls._receive(sock, length)
        if len(compressed_payload) == 0:
            raise ValueError("No compressed payload data")

        if len(compressed_payload) != length:
            raise ValueError("Compressed payload length mismatch")

        payload = lz4.decompress(compressed_payload)
        packet = SafeDeserializer.safe_loads(payload)

        if packet.packet_type.value != packet_type:
            raise ValueError(
                f"Packet type mismatch: header={packet_type}, object={packet.packet_type.value}"
            )

        return packet
