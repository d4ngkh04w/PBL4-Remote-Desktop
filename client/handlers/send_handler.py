import logging

from common.packets import (
    AuthenticationPasswordPacket,
    ConnectionRequestPacket,
    KeyboardPacket,
    SessionPacket,
    VideoConfigPacket,
    VideoStreamPacket,
    CursorInfoPacket,
)
from common.enums import Status, KeyBoardEventType, KeyBoardType
from client.managers.client_manager import ClientManager
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
        logger.info(f"Sent end session packet for: {session_id}")

    @classmethod
    def send_video_config_packet(
        cls,
        session_id: str,
        width: int,
        height: int,
        fps: int,
        codec: str,
        extradata: bytes,
    ):
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
            session_id=None,
            video_data=video_data,
        )
        SenderService.send_packet(video_stream_packet)

    @classmethod
    def send_cursor_info_packet(
        cls, cursor_type: str, position: tuple[int, int], visible: bool = True
    ):
        """Gửi CursorInfoPacket broadcast - server sẽ relay cho tất cả controller sessions"""
        cursor_info_packet = CursorInfoPacket(
            session_id=None,
            cursor_type=cursor_type,
            position=position,
            visible=visible,
        )
        SenderService.send_packet(cursor_info_packet)

    @classmethod
    def send_keyboard_packet(
        cls,
        event_type: KeyBoardEventType,
        key_type: KeyBoardType,
        key_value: str | int | list[str],
        session_id: str,
    ):
        """Gửi KeyboardPacket"""

        keyboard_packet = KeyboardPacket(
            event_type=event_type,
            key_type=key_type,
            key_value=key_value,
            session_id=session_id,
        )
        SenderService.send_packet(keyboard_packet)
