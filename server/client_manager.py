import socket
import ssl
import threading
from typing import Union, TypedDict

ClientInfo = TypedDict(
    "ClientInfo",
    {
        "socket": Union[socket.socket, ssl.SSLSocket],
        "ip": str,
        "status": str,
        "send_lock": threading.Lock,
    },
)


class ClientManager:
    __active_clients: dict[str, ClientInfo] = {}

    _lock = threading.Lock()

    @classmethod
    def add_client(
        cls,
        client_socket: socket.socket | ssl.SSLSocket,
        client_id: str,
        client_ip: str,
    ):
        with cls._lock:
            cls.__active_clients[client_id] = ClientInfo(
                socket=client_socket,
                ip=client_ip,
                status="ONLINE",
                send_lock=threading.Lock(),
            )

    @classmethod
    def remove_client(cls, client_id: str) -> None:
        with cls._lock:
            if client_id in cls.__active_clients:
                del cls.__active_clients[client_id]

    @classmethod
    def update_client_status(cls, client_id: str, status: str) -> None:
        with cls._lock:
            if client_id in cls.__active_clients:
                cls.__active_clients[client_id]["status"] = status

    @classmethod
    def get_client_info(cls, client_id: str):
        with cls._lock:
            return cls.__active_clients.get(client_id)

    @classmethod
    def get_client_socket(cls, client_id: str) -> socket.socket | ssl.SSLSocket | None:
        with cls._lock:
            client_info = cls.__active_clients.get(client_id)
            if client_info:
                socket_obj = client_info.get("socket")
                if isinstance(socket_obj, (socket.socket, ssl.SSLSocket)):
                    return socket_obj
        return None

    @classmethod
    def get_client_socket_and_lock(
        cls, client_id: str
    ) -> tuple[Union[socket.socket, ssl.SSLSocket, None], Union[threading.Lock, None]]:
        """
        Lấy socket và send_lock
        """
        with cls._lock:
            client_info = cls.__active_clients.get(client_id)
            if client_info:
                return client_info.get("socket"), client_info.get("send_lock")
        return None, None

    @classmethod
    def get_all_clients(cls):
        with cls._lock:
            return cls.__active_clients.copy()

    @classmethod
    def is_client_online(cls, client_id: str) -> bool:
        with cls._lock:
            return cls.__active_clients.get(client_id, {}).get("status") == "ONLINE"
