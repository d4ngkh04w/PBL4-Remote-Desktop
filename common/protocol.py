import pickle
import socket
import ssl
import struct
from typing import Union

import lz4.frame as lz4

from common.enums import PacketType
from common.packets import Packet, ImagePacket
from common.safe_deserializer import SafeDeserializer


class Protocol:
    _HEADER_FORMAT = "!IH"
    _HEADER_SIZE = struct.calcsize(_HEADER_FORMAT)

    @staticmethod
    def _receive(sock: Union[socket.socket, ssl.SSLSocket], size: int) -> bytes:
        """
        Nhận dữ liệu từ socket
        """
        data = bytearray()
        while len(data) < size:
            chunk = sock.recv(size - len(data))
            if not chunk:
                raise ConnectionError("Connection closed unexpectedly")
            data.extend(chunk)
        return bytes(data)

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
        payload = lz4.compress(payload)

        length = len(payload)
        header = struct.pack(cls._HEADER_FORMAT, length, packet.packet_type.value)
        socket.sendall(header + payload)

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
            PacketType.FRAME_UPDATE.value,
            PacketType.KEYBOARD.value,
            PacketType.MOUSE.value,
            PacketType.ASSIGN_ID.value,
            PacketType.CONNECTION_REQUEST.value,
            PacketType.CONNECTION_RESPONSE.value,  
            PacketType.SEND_PASSWORD.value,            
        }

        if packet_type not in valid_packet_types:
            raise ValueError(f"Invalid packet type: {packet_type}")

        payload_from_socket = cls._receive(socket, length)
        if len(payload_from_socket) == 0:
            raise ValueError("No compressed payload data")

        if len(payload_from_socket) != length:
            raise ValueError("Compressed payload length mismatch")

        payload = b""
        try:
            payload = lz4.decompress(payload_from_socket)
        except Exception as e:
            error_message = (
                f"LZ4 decompression failed: {e}. "
                f"Packet Type in header was {packet_type}. "
                f"Received {len(payload_from_socket)} bytes, expected {length} bytes."
            )
            raise ValueError(error_message) from e

        packet = SafeDeserializer.safe_loads(payload)
        if packet.packet_type.value != packet_type:
            raise ValueError(
                f"Packet type mismatch: header={packet_type}, object={packet.packet_type.value}"
            )

        return packet
