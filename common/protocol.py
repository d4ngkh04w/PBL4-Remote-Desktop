import pickle
import socket
import ssl

import lz4.frame as lz4

from common.enums import PacketType
from common.packets import Packet
from common.safe_deserializer import SafeDeserializer


class Protocol:
    """
    Packet format:

        Packet-Length: <length>\r\n
        Packet-Type: <packet_type>\r\n
        Compressed: <true|false>\r\n
        \r\n
        <payload>

    """

    __MAX_PACKET_SIZE = 50 * 1024 * 1024
    __NO_COMPRESSION_PACKET_TYPES = {PacketType.VIDEO_STREAM}
    __HEADER_DELIMITER = b"\r\n\r\n"  # Delimiter giữa headers và body

    @staticmethod
    def __receive(sock: socket.socket | ssl.SSLSocket, size: int) -> bytes:
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

    @staticmethod
    def __receive_until_delimiter(
        sock: socket.socket | ssl.SSLSocket, delimiter: bytes
    ) -> bytes:
        """
        Nhận dữ liệu từ socket cho đến khi gặp delimiter
        """
        data = bytearray()
        delimiter_len = len(delimiter)

        while True:
            chunk = sock.recv(1)
            if not chunk:
                raise ConnectionError("Connection closed unexpectedly")
            data.extend(chunk)

            # Kiểm tra xem có khớp với delimiter không
            if len(data) >= delimiter_len and data[-delimiter_len:] == delimiter:
                return bytes(data[:-delimiter_len])  # Không bao gồm delimiter

    @staticmethod
    def __parse_headers(header_data: bytes) -> dict[str, str]:
        """
        Parse headers từ dữ liệu nhận được
        """
        headers = {}
        lines = header_data.decode("utf-8").strip().split("\r\n")

        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

        return headers

    @staticmethod
    def __build_headers(headers: dict[str, str]) -> bytes:
        header_lines = []
        for key, value in headers.items():
            header_lines.append(f"{key}: {value}")

        return "\r\n".join(header_lines).encode("utf-8")

    @classmethod
    def send_packet(
        cls,
        socket: socket.socket | ssl.SSLSocket,
        packet: Packet,
    ) -> None:
        """
        Gửi gói tin

        :param socket: Gói tin được gửi đến socket này
        """

        try:
            # Serialize packet
            payload = pickle.dumps(packet, protocol=pickle.HIGHEST_PROTOCOL)

            # Sử dụng PacketType.get(packet) để lấy packet type
            packet_type = PacketType.get(packet)

            is_compressed = False
            if packet_type not in cls.__NO_COMPRESSION_PACKET_TYPES:
                compressed = lz4.compress(payload)
                is_compressed = True
            else:
                compressed = payload

            length = len(compressed)
            if length > cls.__MAX_PACKET_SIZE:
                raise ValueError(f"Packet too large: {length} bytes")

            headers = {
                "Packet-Length": str(length),
                "Packet-Type": packet_type.value if packet_type else "UNKNOWN",
                "Compressed": "true" if is_compressed else "false",
            }

            header_data = cls.__build_headers(headers)

            socket.sendall(header_data + cls.__HEADER_DELIMITER + compressed)

        except pickle.PicklingError as e:
            raise ValueError(f"Failed to serialize packet: {e}") from e

    @classmethod
    def receive_packet(cls, socket: socket.socket | ssl.SSLSocket) -> Packet:
        """
        Nhận gói tin

        :param socket: Socket nhận gói tin
        """
        header_data = cls.__receive_until_delimiter(socket, cls.__HEADER_DELIMITER)

        headers = cls.__parse_headers(header_data)

        if "Packet-Length" not in headers:
            raise ValueError("Missing Packet-Length header")
        if "Packet-Type" not in headers:
            raise ValueError("Missing Packet-Type header")
        if "Compressed" not in headers:
            raise ValueError("Missing Compressed header")

        length = int(headers["Packet-Length"])
        packet_type = headers["Packet-Type"]
        is_compressed = headers["Compressed"].lower() == "true"

        if length < 0 or length > cls.__MAX_PACKET_SIZE:
            raise ValueError(f"Invalid packet length: {length}")

        valid_packet_types = {pt.value for pt in PacketType}
        if packet_type not in valid_packet_types:
            raise ValueError(f"Invalid packet type: {packet_type}")

        payload_data = cls.__receive(socket, length)
        if len(payload_data) == 0:
            raise ValueError("No payload data")

        if is_compressed:
            try:
                payload = lz4.decompress(payload_data)
            except Exception as e:
                raise ValueError(f"LZ4 decompression failed: {e}") from e
        else:
            payload = payload_data

        try:
            packet = SafeDeserializer.safe_loads(payload)
        except ValueError as e:
            raise ValueError(
                f"Failed to deserialize packet of type {packet_type}: {e}"
            ) from e

        # Kiểm tra packet type từ class name có khớp với header không
        try:
            actual_packet_type = PacketType.get(packet)
        except KeyError as e:
            raise ValueError(f"Unknown packet class: {type(packet).__name__}") from e

        if actual_packet_type.value != packet_type:
            raise ValueError(
                f"Packet type mismatch: header={packet_type}, actual={actual_packet_type.value}"
            )

        return packet
