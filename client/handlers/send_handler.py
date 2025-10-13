import logging

from common.packets import (
    AuthenticationPasswordPacket,
    ConnectionRequestPacket,
    SessionPacket,
    Packet,
)
from common.enums import Status
from client.managers.client_manager import ClientManager
from client.managers.session_manager import SessionManager
from client.services.sender_service import SenderService

logger = logging.getLogger(__name__)


class SendHandler:

    @classmethod
    def send_packet(cls, packet: Packet):
        """Phân loại và xử lý packet nhận được."""
        packet_handlers = {
            # AssignIdPacket: cls.__handle_assign_id_packet,
            # ConnectionResponsePacket: cls.__handle_connection_response_packet,
            # SessionPacket: cls.__handle_session_packet,
            # ConnectionRequestPacket: cls.__handle_connection_request_packet,  # Host nhận
            # VideoConfigPacket: cls.__handle_video_config_packet,
            # VideoStreamPacket: cls.__handle_video_stream_packet,
            AuthenticationPasswordPacket: cls.__send_authentication_password_packet,
            ConnectionRequestPacket: cls.__send_connection_request,
            SessionPacket: cls.__send_end_session_packet,
        }
        handler = packet_handlers.get(type(packet))
        if handler:
            handler(packet)
        else:
            logger.debug(f"Unhandled packet type: {type(packet)}")

    @classmethod
    def __send_connection_request(cls, host_id: str, host_pass: str):
        """Gửi ConnectionRequestPacket"""
        connection_request_packet = ConnectionRequestPacket(
            sender_id=ClientManager.get_client_id(),
            receiver_id=host_id,
            password=host_pass,
        )
        SenderService.send_packet(connection_request_packet)

    @classmethod
    def __send_authentication_password_packet(cls, receiver_id: str, status: Status):
        """Gửi AuthenticationPasswordPacket"""
        auth_packet = AuthenticationPasswordPacket(
            receiver_id=receiver_id,
            status=status,
        )
        SenderService.send_packet(auth_packet)

    @classmethod
    def __send_end_session_packet(cls, session_id: str):
        """Gửi SessionPacket để kết thúc phiên"""
        end_session_packet = SessionPacket(
            status=Status.SESSION_ENDED,
            session_id=session_id,
        )
        SenderService.send_packet(end_session_packet)
        SessionManager.remove_session(session_id)
