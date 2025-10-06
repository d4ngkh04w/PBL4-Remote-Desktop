from typing import Any, Callable
from client.network.socket_client import SocketClient
import threading
import logging
from client.core.event_bus import EventBus
from common.packets import (
    AssignIdPacket,
    ConnectionRequestPacket,
    ConnectionResponsePacket,
    RequestPasswordPacket,
    SendPasswordPacket,
    
)
from common.enums import ConnectionStatus
from common.enums import EventType, PacketType

logger = logging.getLogger(__name__)


class ConnectionService:
    """Dịch vụ quản lý kết nối mạng và truyền nhận dữ liệu - Pure Static Methods"""

    # Class variables để lưu trữ state
    _config: dict | None = None
    _socket_client: SocketClient | None = None
    _lock = threading.RLock()
    _running = False
    _initialized = False

    @classmethod
    def initialize(cls, config: dict):
        """Khởi tạo ConnectionService với config"""
        with cls._lock:
            cls._config = config
            cls._socket_client = None
            cls._running = False

            if not cls._initialized:
                # Subscribe to packet events
                cls._setup_event_subscriptions()
                cls._initialized = True

    @classmethod
    def _setup_event_subscriptions(cls):
        """Thiết lập subscription cho các packet events"""
        EventBus.subscribe(f"PACKET_{PacketType.ASSIGN_ID.name}", cls._handle_assign_id_packet)
        EventBus.subscribe(
            f"PACKET_{PacketType.CONNECTION_RESPONSE.name}", cls._handle_response_connection_packet
        )
        EventBus.subscribe(
            f"PACKET_{PacketType.CONNECTION_REQUEST.name}", cls._handle_request_connection_packet
        )
        EventBus.subscribe(
            f"PACKET_{PacketType.REQUEST_PASSWORD.name}", cls._handle_request_password_packet
        )       
        EventBus.subscribe(f"PACKET_{PacketType.SEND_PASSWORD.name}", cls._handle_send_password_packet)
        EventBus.subscribe(EventType.PASSWORD_CORRECT.name, cls._handle_password_correct)
        EventBus.subscribe(EventType.PASSWORD_INCORRECT.name, cls._handle_password_incorrect)
        EventBus.subscribe(EventType.UI_SEND_HOST_PASSWORD.name, cls._handle_send_host_password)

    @classmethod
    def start(cls):
        """Bắt đầu dịch vụ kết nối"""
        with cls._lock:
            if cls._running:
                return

            cls._running = True
            logger.info("ConnectionService started")

    @classmethod
    def stop(cls):
        """Dừng dịch vụ kết nối"""
        with cls._lock:
            if not cls._running:
                return

            cls._running = False

            if cls._socket_client:
                cls._socket_client.disconnect()
                cls._socket_client = None

            logger.debug("ConnectionService stopped")

    # ====== Controller and Host Methods ======
    @classmethod
    def connect_to_server(cls) -> bool:
        """Kết nối đến server để nhận ID"""
        try:
            if cls._config is None:
                logger.error("ConnectionService config is not initialized")
                return False
            if cls._socket_client is None:
                cls._socket_client = SocketClient(
                    cls._config["host"],
                    cls._config["port"],
                    cls._config.get("use_ssl", False),
                    cls._config.get("cert_file", None),
                )

            success = cls._socket_client.connect()
            if success:
                EventBus.publish(
                    EventType.UI_UPDATE_STATUS.name,
                    {
                        "message": "Connected to server, waiting for ID...",
                        "type": "info",
                    },
                    source="ConnectionService",
                )
                EventBus.publish(
                    EventType.NETWORK_CONNECTED.name, None, source="ConnectionService"
                )
            else:
                EventBus.publish(
                    EventType.UI_UPDATE_STATUS.name,
                    {
                        "message": "Failed to connect to server",
                        "type": "error",
                    },
                    source="ConnectionService",
                )
                cls._socket_client = None

            return success
        except Exception as e:
            logger.error("Error occurred while connecting to server: %s", e)
            EventBus.publish(
                EventType.NETWORK_CONNECTION_FAILED.name,
                {"error": str(e)},
                source="ConnectionService",
            )
            return False

    @classmethod
    def disconnect_from_server(cls):
        """Ngắt kết nối khỏi server"""
        with cls._lock:
            if cls._socket_client:
                cls._socket_client.disconnect()
                cls._socket_client = None

    @classmethod
    def _handle_assign_id_packet(cls, packet: AssignIdPacket):
        """Xử lý gói tin gán ID từ server"""
        if hasattr(packet, "client_id"):
            EventBus.publish(
                EventType.UI_SHOW_CLIENT_ID.name,
                {"client_id": packet.client_id},
                source="ConnectionService",
            )

            EventBus.publish(
                EventType.UI_UPDATE_STATUS.name,
                {"message": f"Ready - Your ID: {packet.client_id}", "type": "success"},
                source="ConnectionService",
            )
        else:
            logger.error("Invalid assign ID packet received")

    # ====== Controller Methods ======
    @classmethod
    def send_connection_request(cls, host_id: str) -> bool:
        """Gửi yêu cầu kết nối đến host"""
        if not cls._socket_client or not cls._socket_client.running:
            logger.error("Not connected to server")
            return False
        try:
            controller_id = cls._socket_client.client_id
            if controller_id is None:
                logger.error("Client ID is not assigned")
                return False
            request_packet = ConnectionRequestPacket(
                controller_id=controller_id, host_id=host_id
            )
            success = cls._socket_client.send_packet(request_packet)
            if success:
                logger.info("Connection request sent to host %s", host_id)
            else:
                logger.error("Failed to send connection request")
            return success
        except Exception as e:
            logger.error("Error sending connection request: %s", e)
            return False

    @classmethod
    def _handle_response_connection_packet(cls, packet: ConnectionResponsePacket):
        """Xử lý gói tin phản hồi kết nối từ host"""
        if not hasattr(packet, "connection_status") or not hasattr(packet, "message"):
            logger.error("Invalid response connection packet")
            return

        logger.info("Received connection response: %s", packet.message)
        # if packet.connection_status == ConnectionStatus.FAILED:
        #     EventBus.publish(
        #         EventType.UI_UPDATE_STATUS.name,
        #         {"message": f"Connection failed: {packet.message}", "type": "error"},
        #         source="ConnectionService",
        #     )
        # elif packet.connection_status == ConnectionStatus.REJECTED:
        #     EventBus.publish(
        #         EventType.UI_UPDATE_STATUS.name,
        #         {"message": f"Connection rejected: {packet.message}", "type": "error"},
        #         source="ConnectionService",
        #     )
        if packet.connection_status == ConnectionStatus.SESSION_STARTED:
            EventBus.publish(
                EventType.UI_UPDATE_STATUS.name,
                {"message": "Connection established!", "type": "success"},
                source="ConnectionService",
            )
        else: 
            EventBus.publish(
                EventType.UI_UPDATE_STATUS.name,
                {"message": f"Connection error: {packet.message}", "type": "error"},
                source="ConnectionService",
            )
            EventBus.publish(
                EventType.DISCONNECTED_WITH_HOST.name, None, source="ConnectionService"
            )

    @classmethod
    def _handle_request_password_packet(cls, packet: RequestPasswordPacket):
        """Xử lý gói tin yêu cầu xác thực password từ host"""
        if not hasattr(packet, "host_id") or not hasattr(packet, "controller_id"):
            logger.error("Invalid request password packet")
            return

        logger.info("Received password_request from host %s", packet.host_id)

        if not cls._socket_client or not cls._socket_client.running:
            logger.error("Not connected to server")
            return
        try:
            # Publish event để request password từ UI
            EventBus.publish(
                EventType.GET_HOST_PASSWORD_FROM_UI.name,
                {"controller_id": packet.controller_id, "host_id": packet.host_id},
                source="ConnectionService",
            )

            # Note: Password sẽ được gửi qua event khác sau khi UI respond
        except Exception as e:
            logger.error("Error sending password: %s", e)

    # ====== Host Methods ======
    @classmethod
    def _handle_request_connection_packet(cls, packet: ConnectionRequestPacket):
        """Xử lý gói tin yêu cầu kết nối từ controller"""
        if not hasattr(packet, "controller_id") or not hasattr(packet, "host_id"):
            logger.error("Invalid request connection packet")
            return

        logger.info(
            "Received connection request from controller %s", packet.controller_id
        )
        EventBus.publish(
            EventType.UI_SHOW_NOTIFICATION.name,
            {
                "controller_id": packet.controller_id,
                "host_id": packet.host_id,
            },
            source="ConnectionService",
        )

    @classmethod
    def _accept_connection_request(cls, controller_id, host_id):
        """Chấp nhận yêu cầu kết nối từ controller"""
        try:
            logger.info(
                "Accepting connection request from controller %s", controller_id
            )
            request_password_packet = RequestPasswordPacket(
                controller_id=controller_id, host_id=host_id
            )
            if cls._socket_client:
                cls._socket_client.send_packet(request_password_packet)
                logger.info("Sent password request to controller %s", controller_id)
        except Exception as e:
            logger.error("Error accepting connection: %s", e)

    @classmethod
    def _reject_connection_request(cls, controller_id, host_id):
        """Từ chối yêu cầu kết nối từ controller"""
        try:
            logger.info(
                "Rejecting connection request from controller %s", controller_id
            )
            response_packet = ConnectionResponsePacket(
                controller_id=controller_id,
                host_id=host_id,
                connection_status=ConnectionStatus.REJECTED,
                message="Connection rejected by host",
            )
            if cls._socket_client:
                cls._socket_client.send_packet(response_packet)
                logger.info("Connection rejected for controller %s", controller_id)
        except Exception as e:
            logger.error("Error rejecting connection: %s", e)

    @classmethod
    def _handle_send_password_packet(cls, packet: SendPasswordPacket):
        """Xử lý gói tin gửi password"""
        logger.debug("Received send password packet")

        if (
            not hasattr(packet, "controller_id")
            or not hasattr(packet, "host_id")
            or not hasattr(packet, "password")
        ):
            logger.error("Invalid send password packet")
            return

        EventBus.publish(
            EventType.VERIFY_PASSWORD.name,
            {
                "controller_id": packet.controller_id,
                "host_id": packet.host_id,
                "password": packet.password,
            },
            source="ConnectionService",
        )

    @classmethod
    def _handle_password_correct(cls, data):
        """Xử lý khi mật khẩu đúng"""
        try:
            logger.info("Accepted password, sending authentication success")
            controller_id = data.get("controller_id")
            host_id = data.get("host_id")
            connectionResponsePacket = ConnectionResponsePacket(
                controller_id=controller_id,
                host_id=host_id,
                connection_status=ConnectionStatus.SUCCESS,
                message="Authentication successful",
            )
            if cls._socket_client:
                cls._socket_client.send_packet(connectionResponsePacket)
                logger.debug(
                    "Sent authentication success to controller %s", controller_id
                )

        except Exception as e:
            logger.error("Error handling correct password: %s", e)

    @classmethod
    def _handle_password_incorrect(cls, data):
        """Xử lý khi mật khẩu sai"""
        try:
            logger.info("Password incorrect, sending authentication failure")
            controller_id = data.get("controller_id")
            host_id = data.get("host_id")
            connectionResponsePacket = ConnectionResponsePacket(
                controller_id=controller_id,
                host_id=host_id,
                connection_status=ConnectionStatus.INVALID_PASSWORD,
                message="Authentication failed",
            )
            if cls._socket_client:
                cls._socket_client.send_packet(connectionResponsePacket)
                logger.debug(
                    "Sent authentication failure to controller %s", controller_id
                )

        except Exception as e:
            logger.error("Error handling incorrect password: %s", e)

    @classmethod
    def _handle_send_host_password(cls, data):
        """Xử lý việc gửi password từ UI để authentication"""
        try:
            controller_id = data.get("controller_id")
            host_id = data.get("host_id")
            password = data.get("password")

            if not all([controller_id, host_id, password]):
                logger.error("Missing data for sending host password")
                return

            password_packet = SendPasswordPacket(
                controller_id=controller_id, host_id=host_id, password=password
            )

            if cls._socket_client:
                cls._socket_client.send_packet(password_packet)
                logger.info("Sent password to host %s", host_id)
            else:
                logger.error("No socket client available")

        except Exception as e:
            logger.error("Error sending host password: %s", e)


# Convenience functions for easier access
def initialize_connection_service(config: dict):
    """Initialize the connection service"""
    return ConnectionService.initialize(config)


def start_connection_service():
    """Start the connection service"""
    return ConnectionService.start()


def stop_connection_service():
    """Stop the connection service"""
    return ConnectionService.stop()


def connect_to_server() -> bool:
    """Connect to server"""
    return ConnectionService.connect_to_server()


def disconnect_from_server():
    """Disconnect from server"""
    return ConnectionService.disconnect_from_server()


def send_connection_request(host_id: str) -> bool:
    """Send connection request to host"""
    return ConnectionService.send_connection_request(host_id)
