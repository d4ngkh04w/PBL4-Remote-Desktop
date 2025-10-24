import logging

from common.packets import (
    AuthenticationPasswordPacket,
    ConnectionRequestPacket,
    SessionPacket,
    VideoConfigPacket,
    VideoStreamPacket,   
)
from common.enums import Status
from client.managers.client_manager import ClientManager
from client.managers.session_manager import SessionManager
from client.services.sender_service import SenderService

logger = logging.getLogger(__name__)


class SendHandler:
    @classmethod
    def send_connection_request_packet(cls, host_id: str, host_pass: str):
        """Gửi ConnectionRequestPacket"""
        connection_request_packet = ConnectionRequestPacket(
            sender_id=ClientManager.get_client_id(),
            receiver_id=host_id,
            password=host_pass,
        )
        SenderService.send_packet(connection_request_packet)

    @classmethod
    def send_authentication_password_packet(cls, receiver_id: str, status: Status):
        """Gửi AuthenticationPasswordPacket"""
        auth_packet = AuthenticationPasswordPacket(
            receiver_id=receiver_id,
            status=status,
        )
        SenderService.send_packet(auth_packet)

    @classmethod
    def send_end_session_packet(cls, session_id: str):
        """Gửi SessionPacket để kết thúc phiên"""
        end_session_packet = SessionPacket(
            status=Status.SESSION_ENDED,
            session_id=session_id,
        )
        SenderService.send_packet(end_session_packet)
        SessionManager.remove_session(session_id)

    @classmethod
    def send_video_config_packet(cls, session_id: str, width: int, height: int, fps: int, codec: str, extradata: bytes):
        """Gửi VideoConfigPacket"""        
        video_config_packet = VideoConfigPacket(
            session_id=session_id,
            width=width,
            height=height,
            fps=fps,
            codec=codec,
            extradata=extradata,
        )
        SenderService.send_packet(video_config_packet)

    @classmethod
    def send_video_stream_packet(cls, video_data: bytes):
        """Gửi VideoStreamPacket broadcast - server sẽ relay cho tất cả controller sessions"""
        video_stream_packet = VideoStreamPacket(
            session_id= None,  
            video_data=video_data,
        )
        SenderService.send_packet(video_stream_packet)
        

    

   
