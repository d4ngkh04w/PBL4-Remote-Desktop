from common.protocol import Protocol
from common.packet import *
from common.logger import logger
from common.database import get_db_instance
from common.enum import PacketType

class ClientHandler:
    active_clients = {}
    def __init__(self, client_socket, client_id, client_addr):
        self.client_socket = client_socket
        self.client_id = client_id
        self.client_addr = client_addr
        self.db = get_db_instance()
        self.is_active = True
        self.session_manager = None
        #Lưu vào memory cache
        ClientHandler.active_clients[client_id] = self     

    @classmethod
    def get_client_socket(cls, client_id):
        client_handler = cls.active_clients.get(client_id)
        if client_handler and client_handler.is_active:
            return client_handler.client_socket
        return None
    @classmethod
    def get_client_handler(cls, client_id):
        """Lấy handler của client"""
        return cls.active_clients.get(client_id)

    def handle(self):
        """Main handler loop cho client"""
        try:
            # Thêm client vào db
            self.db.add_client(self.client_id, self.client_addr[0])
            logger.info(f"Client {self.client_id} connected from {self.client_addr}")

            while self.is_active:
                packet = Protocol.receive_packet(self.client_socket)
                if not packet:                    
                    break
                self._process_packet(packet)

        except Exception as e:
            logger.error(f"Error handling client {self.client_id}: {e}")
        finally:
            self._cleanup()

    def _process_packet(self, packet):
        """Xử lí các loại packet khác nhau"""  
        if packet.type == PacketType.REQUEST_CONNECTION:
            self._handle_request_connection(packet)
        elif packet.type == PacketType.REQUEST_PASSWORD:
            self._handle_request_password(packet)
        elif packet.type == PacketType.SEND_PASSWORD:
            self._handle_send_password(packet)       
        else:
            logger.warning(f"Unknown packet type from client {self.client_id}: {packet.type}")

    def _handle_request_connection(self, packet: RequestConnectionPacket):
        """Xử lí REQUEST_CONNECTION"""
        logger.info(f"Client {self.client_id} requests connection to {packet.target_id}")

        # Kiểm tra target_id có online không
        if not self.db.is_client_online(packet.target_id):
            response = ResponseConnectionPacket(
                success=False,
                message=f"Target client {packet.target_id} is not online"
            )
            Protocol.send_packet(self.client_socket, response)
            logger.info(f"Client {self.client_id} connection to {packet.target_id} failed: target offline")
            return

        # lấy socket từ memory cache
        target_socket = ClientHandler.get_client_socket(packet.target_id)
        if target_socket:
            Protocol.send_packet(target_socket, packet)
            logger.info(f"Client {self.client_id} connection request sent to {packet.target_id}")
        else:
            logger.warning(f"Client {self.client_id} connection request failed: target offline")
            response = ResponseConnectionPacket(
                success=False,
                message=f"Target client {packet.target_id} is not online"
            )
            Protocol.send_packet(self.client_socket, response)

    def _handle_request_password(self, packet: RequestPasswordPacket):
        """Xử lí REQUEST_PASSWORD - Host yêu cầu password từ controller"""
        logger.info(f"Host {self.client_id} requests password from controller")
        # Gửi yêu cầu mật khẩu đến controller
        controller_socket = ClientHandler.get_client_socket(packet.controller_id)
        if controller_socket:
            Protocol.send_packet(controller_socket, packet)
            logger.info(f"Password request sent to controller {packet.controller_id}")
        else:
            logger.warning(f"Controller {packet.controller_id} not found")
        # Gửi response lỗi về host
        response = ResponseConnectionPacket(
            success=False,
            message="Controller not available"
        )
        Protocol.send_packet(self.client_socket, response)
    def _handle_send_password(self, packet: SendPasswordPacket):
        """Xử lí SEND_PASSWORD - Controller gửi password đến host"""
        logger.info(f"Client {self.client_id} sends password")
        
        # Forward password đến host
        target_socket = ClientHandler.get_client_socket(packet.target_id)
        if target_socket:
            Protocol.send_packet(target_socket, packet)
            logger.info(f"Password sent to host {packet.target_id}")
        else:
            response = ResponseConnectionPacket(
                success=False,
                message=f"Target host {packet.target_id} is not online"
            )
            Protocol.send_packet(self.client_socket, response)

    def _cleanup(self):
        """Cleanup khi client disconnect"""
        try:
            self.db.remove_client(self.client_id)
            self.client_socket.close()
            
            # Xóa khỏi memory cache
            if self.client_id in ClientHandler.active_clients:
                del ClientHandler.active_clients[self.client_id]
                
            logger.info(f"Client {self.client_id} disconnected")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
