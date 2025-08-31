from common.logger import logger
from common.packet import AssignIdPacket
from client.network.network_client import NetworkClient


class AuthManager:
    """Quản lý ID và Password cho client"""

    def __init__(self, network_client: NetworkClient):
        self.network_client = network_client
        self.client_id = 123456789
        self.temp_password = "abc123"
        self.is_authenticated = True

    # def request_id_from_server(self):
    #     """Yêu cầu ID từ server"""
    #     try:
    #         # Gửi yêu cầu cấp ID đến server
    #         request_packet = IDRequestPacket()
    #         self.network_client.send(request_packet)
    #         logger.info("Requested ID from server")
    #     except Exception as e:
    #         logger.error(f"Error requesting ID from server: {e}")

    # def handle_ASSIGN_ID(self, packet: AssignIdPacket):
    #     """Xử lý phản hồi cấp ID từ server"""
    #     if hasattr(packet, "client_id") and hasattr(packet, "temp_password"):
    #         self.client_id = packet.client_id
    #         self.temp_password = packet.temp_password
    #         self.is_authenticated = True
    #         logger.info(
    #             f"Received ID: {self.client_id} and temporary password from server"
    #         )
    #         return True
    #     return False

    def get_client_id(self):
        """Lấy ID của client"""
        return self.client_id if self.is_authenticated else "Connecting ..."

    def get_temp_password(self):
        """Lấy mật khẩu tạm thời của client"""
        return self.temp_password if self.is_authenticated else "Connecting ..."
