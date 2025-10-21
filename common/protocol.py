import pickle
import socket
import ssl
import struct
from typing import Union

import lz4.frame as lz4

from common.enums import PacketType
from common.packets import Packet
from common.safe_deserializer import SafeDeserializer


class Protocol:
    __HEADER_FORMAT = "!IHB"  # length (4B) + packet_type (2B) + is_compressed (1B)
    __HEADER_SIZE = struct.calcsize(__HEADER_FORMAT)
    __MAX_PACKET_SIZE = 50 * 1024 * 1024
    __NO_COMPRESS_TYPES = {PacketType.VIDEO_STREAM}

    @staticmethod
    def __receive(sock: Union[socket.socket, ssl.SSLSocket], size: int) -> bytes:
        """
        Nhận dữ liệu từ socket
        """
        data = bytearray()
        while len(data) < size:
            chunk = sock.recv(min(size - len(data), 8 * 1024))
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
        try:
            payload = pickle.dumps(packet, protocol=pickle.HIGHEST_PROTOCOL)
            if packet.packet_type in cls.__NO_COMPRESS_TYPES:
                compressed = payload
                is_compressed = 0
            else:
                compressed = lz4.compress(payload)
                is_compressed = 1

            length = len(compressed)
            if length > cls.__MAX_PACKET_SIZE:
                raise ValueError(f"Packet too large: {length} bytes")

            header = struct.pack(
                cls.__HEADER_FORMAT, length, packet.packet_type.value, is_compressed
            )

            socket.sendall(header + compressed)
        except pickle.PicklingError as e:
            raise ValueError(f"Failed to serialize packet: {e}") from e

    @classmethod
    def receive_packet(cls, socket: Union[socket.socket, ssl.SSLSocket]) -> Packet:
        """
        Nhận gói tin

        :param socket: Socket nhận gói tin
        """
        header = cls.__receive(socket, cls.__HEADER_SIZE)

        length, packet_type, is_compressed = struct.unpack(cls.__HEADER_FORMAT, header)

        if length < 0 or length > cls.__MAX_PACKET_SIZE:
            raise ValueError("Invalid packet length")

        valid_packet_types = {pt.value for pt in PacketType}
        if packet_type not in valid_packet_types:
            raise ValueError(f"Invalid packet type: {packet_type}")

        payload_data = cls.__receive(socket, length)
        if len(payload_data) == 0:
            raise ValueError("No compressed payload data")

        if is_compressed:
            try:
                payload = lz4.decompress(payload_data)
            except Exception as e:
                raise ValueError(
                    f"LZ4 decompression failed: {e}. "
                    f"Packet type={packet_type}, compressed_size={len(payload_data)}"
                ) from e
        else:
            payload = payload_data

        try:
            packet = SafeDeserializer.safe_loads(payload)
        except ValueError as e:
            raise ValueError(
                f"Failed to deserialize packet of type {packet_type}: {e}"
            ) from e

        if packet.packet_type.value != packet_type:
            raise ValueError(
                f"Packet type mismatch: header={packet_type}, object={packet.packet_type.value}"
            )

        return packet
