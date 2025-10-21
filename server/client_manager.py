import socket
import ssl
import threading
from typing import TypedDict
from queue import Queue
import logging

from common.packets import Packet

logger = logging.getLogger(__name__)

ClientInfo = TypedDict(
    "ClientInfo",
    {
        "socket": socket.socket | ssl.SSLSocket,
        "ip": str,
        "id": str,
        "queue": Queue[Packet],  # Hàng đợi để gửi gói tin
    },
)


class ClientManager:
    __active_clients: dict[str, ClientInfo] = {}
    __socket_to_id: dict[socket.socket | ssl.SSLSocket, str] = (
        {}
    )  # Mapping nhanh từ socket đến ID
    __lock = threading.Lock()

    @classmethod
    def add_client(
        cls,
        client_socket: socket.socket | ssl.SSLSocket,
        client_id: str,
        client_ip: str,
    ):
        with cls.__lock:
            client_info = ClientInfo(
                socket=client_socket,
                ip=client_ip,
                id=client_id,
                queue=Queue(maxsize=2048),
            )
            cls.__active_clients[client_id] = client_info
            cls.__socket_to_id[client_socket] = client_id

    @classmethod
    def remove_client(cls, client_id: str) -> None:
        with cls.__lock:
            if client_id in cls.__active_clients:
                client_info = cls.__active_clients.pop(client_id)
                # Xóa mapping
                cls.__socket_to_id.pop(client_info["socket"], None)

                if not client_info["queue"].empty():
                    logger.warning(
                        f"Client {client_id} disconnected. Discarding {client_info['queue'].qsize()} unsent packets"
                    )
                    client_info["queue"].queue.clear()

    @classmethod
    def get_client_info(cls, client: str | socket.socket | ssl.SSLSocket):
        with cls.__lock:
            if isinstance(client, str):
                return cls.__active_clients.get(client)
            elif isinstance(client, (socket.socket, ssl.SSLSocket)):
                client_id = cls.__socket_to_id.get(client)
                if client_id:
                    return cls.__active_clients.get(client_id)
            return None

    @classmethod
    def get_client_socket(cls, client_id: str) -> socket.socket | ssl.SSLSocket | None:
        with cls.__lock:
            client_info = cls.__active_clients.get(client_id)
            if client_info:
                socket_obj = client_info.get("socket")
                if isinstance(socket_obj, (socket.socket, ssl.SSLSocket)):
                    return socket_obj
            return None

    @classmethod
    def get_client_queue(cls, client_id: str) -> Queue[Packet] | None:
        with cls.__lock:
            client_info = cls.__active_clients.get(client_id)
            return client_info["queue"] if client_info else None

    @classmethod
    def is_client_exist(cls, client_id: str) -> bool:
        with cls.__lock:
            return client_id in cls.__active_clients

    @classmethod
    def get_client_count(cls) -> int:
        with cls.__lock:
            return len(cls.__active_clients)

    @classmethod
    def shutdown(cls):
        with cls.__lock:
            client_ids = list(cls.__active_clients.keys())
            for client_id in client_ids:
                info = cls.__active_clients.pop(client_id, None)

                if info:
                    # Xóa mapping
                    cls.__socket_to_id.pop(info["socket"], None)

                    while not info["queue"].empty():
                        try:
                            info["queue"].get_nowait()
                        except:
                            break

                    try:
                        info["socket"].shutdown(socket.SHUT_RDWR)
                        info["socket"].close()
                    except Exception as e:
                        logger.error(
                            f"Error shutting down socket for client {client_id}: {e}"
                        )

            cls.__socket_to_id.clear()
            logger.info("All clients cleared")
