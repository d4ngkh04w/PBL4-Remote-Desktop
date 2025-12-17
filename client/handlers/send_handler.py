import logging

from common.packets import (
    AuthenticationPasswordPacket,
    ConnectionRequestPacket,
    KeyboardPacket,
    SessionPacket,
    VideoConfigPacket,
    VideoStreamPacket,
    ChatMessagePacket,
    FileMetadataPacket,
    FileAcceptPacket,
    FileRejectPacket,
    FileChunkPacket,
    FileCompletePacket,
)
from common.enums import Status, KeyBoardEventType, KeyBoardType
from client.managers.client_manager import ClientManager
from client.services.sender_service import SenderService

logger = logging.getLogger(__name__)


class SendHandler:
    @classmethod
    def send_connection_request_packet(cls, host_id: str, host_pass: str):
        """Gửi ConnectionRequestPacket"""
        from common.utils import get_hostname

        connection_request_packet = ConnectionRequestPacket(
            sender_id=ClientManager.get_client_id(),
            receiver_id=host_id,
            password=host_pass,
            sender_hostname=get_hostname(),
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
    def send_video_stream_packet(
        cls,
        video_data: bytes,
        cursor_type: str | None = None,
        cursor_position: tuple[int, int] | None = None,
    ):
        """Gửi VideoStreamPacket broadcast với thông tin cursor - server sẽ relay cho tất cả controller sessions"""
        video_stream_packet = VideoStreamPacket(
            session_id=None,
            video_data=video_data,
            cursor_type=cursor_type,
            cursor_position=cursor_position,
        )
        SenderService.send_packet(video_stream_packet)

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

    @classmethod
    def send_chat_message_packet(
        cls, session_id: str, sender_role: str, message: str, timestamp: float
    ):
        """Gửi ChatMessagePacket"""
        chat_packet = ChatMessagePacket(
            session_id=session_id,
            sender_role=sender_role,
            message=message,
            timestamp=timestamp,
        )
        SenderService.send_packet(chat_packet)

    @classmethod
    def send_file_metadata_packet(
        cls,
        session_id: str,
        file_id: str,
        filename: str,
        filesize: int,
        sender_role: str,
    ):
        """Gửi FileMetadataPacket"""
        file_metadata_packet = FileMetadataPacket(
            session_id=session_id,
            file_id=file_id,
            filename=filename,
            filesize=filesize,
            sender_role=sender_role,
        )
        SenderService.send_packet(file_metadata_packet)

    @classmethod
    def send_file_accept_packet(cls, session_id: str, file_id: str):
        """Gửi FileAcceptPacket"""
        file_accept_packet = FileAcceptPacket(
            session_id=session_id,
            file_id=file_id,
        )
        SenderService.send_packet(file_accept_packet)

    @classmethod
    def send_file_reject_packet(cls, session_id: str, file_id: str):
        """Gửi FileRejectPacket"""
        file_reject_packet = FileRejectPacket(
            session_id=session_id,
            file_id=file_id,
        )
        SenderService.send_packet(file_reject_packet)

    @classmethod
    def send_file_chunk_packet(
        cls,
        session_id: str,
        file_id: str,
        chunk_index: int,
        chunk_data: bytes,
        total_chunks: int,
    ):
        """Gửi FileChunkPacket"""
        file_chunk_packet = FileChunkPacket(
            session_id=session_id,
            file_id=file_id,
            chunk_index=chunk_index,
            chunk_data=chunk_data,
            total_chunks=total_chunks,
        )
        SenderService.send_packet(file_chunk_packet)

    @classmethod
    def send_file_complete_packet(
        cls, session_id: str, file_id: str, success: bool, message: str = ""
    ):
        """Gửi FileCompletePacket"""
        file_complete_packet = FileCompletePacket(
            session_id=session_id,
            file_id=file_id,
            success=success,
            message=message,
        )
        SenderService.send_packet(file_complete_packet)
