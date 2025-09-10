import pickle
import socket
import ssl
import struct
from typing import Union

import lz4.frame as lz4

from common.enum import PacketType
from common.packet import Packet
from common.safe_deserializer import SafeDeserializer


class Protocol:
    _HEADER_FORMAT = "!IH"
    _HEADER_SIZE = struct.calcsize(_HEADER_FORMAT)

    @staticmethod
    def _receive(sock: Union[socket.socket, ssl.SSLSocket], n: int) -> bytes:
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
        socket: Union[socket.socket, ssl.SSLSocket],
        packet: Packet,
    ) -> None:
        """
        Gửi gói tin

        :param socket: Gói tin được gửi đến socket này
        """
        payload = pickle.dumps(packet)
        compressed_payload = lz4.compress(payload)
        length = len(compressed_payload)
        header = struct.pack(cls._HEADER_FORMAT, length, packet.packet_type.value)
        socket.sendall(header + compressed_payload)

    @classmethod
    def receive_packet(cls, socket: Union[socket.socket, ssl.SSLSocket]) -> Packet:
        """
        Nhận gói tin

        :param socket: Socket nhận gói tin
        """
        header = cls._receive(socket, cls._HEADER_SIZE)

        length, packet_type = struct.unpack(cls._HEADER_FORMAT, header)

        if length < 0:
            raise ValueError("Invalid packet length")

        valid_packet_types = {
            PacketType.IMAGE.value,
            PacketType.KEYBOARD.value,
            PacketType.MOUSE.value,
            PacketType.ASSIGN_ID.value,
            PacketType.REQUEST_CONNECTION.value,
            PacketType.AUTHENTICATION_RESPONSE.value,
            PacketType.AUTHENTICATION_REQUEST.value,
            PacketType.AUTHENTICATION_RESULT.value,
            PacketType.RESPONSE_CONNECTION.value,
            PacketType.SEND_PASSWORD.value,
            PacketType.SESSION.value,
        }

        if packet_type not in valid_packet_types:
            raise ValueError(f"Invalid packet type: {packet_type}")

        compressed_payload = cls._receive(socket, length)
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
