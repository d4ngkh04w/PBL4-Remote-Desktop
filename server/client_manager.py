import socket
import ssl


class ClientManager:
    __active_clients: dict[str, dict[str, str | socket.socket | ssl.SSLSocket]] = {}

    @classmethod
    def add_client(
        cls,
        client_socket: socket.socket | ssl.SSLSocket,
        client_id: str,
        client_ip: str,
    ):
        cls.__active_clients[client_id] = {
            "socket": client_socket,
            "ip": client_ip,
            "status": "ONLINE",
        }

    @classmethod
    def remove_client(cls, client_id: str) -> None:
        if client_id in cls.__active_clients:
            del cls.__active_clients[client_id]

    @classmethod
    def update_client_status(cls, client_id: str, status: str) -> None:
        if client_id in cls.__active_clients:
            cls.__active_clients[client_id]["status"] = status

    @classmethod
    def get_client_info(cls, client_id: str):
        return cls.__active_clients.get(client_id)

    @classmethod
    def get_client_socket(cls, client_id: str) -> socket.socket | ssl.SSLSocket | None:
        client_info = cls.__active_clients.get(client_id)
        if client_info:
            socket_obj = client_info.get("socket")
            if isinstance(socket_obj, (socket.socket, ssl.SSLSocket)):
                return socket_obj
        return None

    @classmethod
    def get_all_clients(cls):
        return cls.__active_clients

    @classmethod
    def is_client_online(cls, client_id: str) -> bool:
        return cls.__active_clients.get(client_id, {}).get("status") == "ONLINE"
