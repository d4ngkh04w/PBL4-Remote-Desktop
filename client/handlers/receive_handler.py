import logging

from common.enums import Status
from client.managers.client_manager import ClientManager
from client.controllers.main_window_controller import main_window_controller
from client.managers.session_manager import SessionManager
from client.services.keyboard_executor_service import KeyboardExecutorService
from client.services.mouse_executor_service import MouseExecutorService
from common.packets import (
    AssignIdPacket,
    ConnectionRequestPacket,
    ConnectionResponsePacket,
    KeyboardPacket,
    MousePacket,
    SessionPacket,
    VideoConfigPacket,
    VideoStreamPacket,
    AuthenticationPasswordPacket,
    ChatMessagePacket,
    FileMetadataPacket,
    FileAcceptPacket,
    FileRejectPacket,
    FileChunkPacket,
    FileCompletePacket,
    Packet,
)

logger = logging.getLogger(__name__)


class ReceiveHandler:

    @classmethod
    def handle_packet(cls, packet: Packet):
        """Phân loại và xử lý packet nhận được."""
        packet_handlers = {
            AssignIdPacket: cls.__handle_assign_id_packet,
            ConnectionResponsePacket: cls.__handle_connection_response_packet,
            SessionPacket: cls.__handle_session_packet,
            ConnectionRequestPacket: cls.__handle_connection_request_packet,  # Host nhận
            AuthenticationPasswordPacket: cls.__handle_authentication_password_packet,  # Host nhận
            VideoConfigPacket: cls.__handle_video_config_packet,
            VideoStreamPacket: cls.__handle_video_stream_packet,
            KeyboardPacket: cls.__handle_keyboard_packet,
            MousePacket: cls.__handle_mouse_packet,
            ChatMessagePacket: cls.__handle_chat_message_packet,
            FileMetadataPacket: cls.__handle_file_metadata_packet,
            FileAcceptPacket: cls.__handle_file_accept_packet,
            FileRejectPacket: cls.__handle_file_reject_packet,
            FileChunkPacket: cls.__handle_file_chunk_packet,
            FileCompletePacket: cls.__handle_file_complete_packet,
        }
        handler = packet_handlers.get(type(packet))
        if handler:
            handler(packet)
        else:
            logger.debug(f"Unhandled packet type: {type(packet)}")

    @staticmethod
    def __handle_assign_id_packet(packet: AssignIdPacket):
        """Xử lý AssignIdPacket"""
        if not packet.client_id:
            logger.error("Received AssignIdPacket with empty fields.")
            return
        ClientManager.set_client_id(packet.client_id)
        main_window_controller.on_client_id_received()

    @staticmethod
    def __handle_authentication_password_packet(packet: AuthenticationPasswordPacket):
        """Xử lý AuthenticationPasswordPacket"""
        if packet.status == Status.INVALID_PASSWORD:
            main_window_controller.on_connection_rejected()
            main_window_controller.on_ui_show_notification(
                "Connection rejected: Invalid password.", "error"
            )

    @staticmethod
    def __handle_connection_response_packet(packet: ConnectionResponsePacket):
        """Xử lý ConnectionResponsePacket"""
        if packet.connection_status == Status.ALREADY_CONNECTED:
            main_window_controller.on_connection_rejected()
            main_window_controller.on_ui_show_notification(
                "Connection rejected: Already connected to this host.", "error"
            )

        elif packet.connection_status == Status.SERVER_FULL:
            if main_window_controller:
                main_window_controller.on_connection_rejected()
                main_window_controller.on_ui_show_notification(
                    "Connection rejected: Server is full.", "error"
                )

        elif packet.connection_status == Status.RECEIVER_NOT_FOUND:
            if packet.message:
                if main_window_controller:
                    main_window_controller.on_connection_rejected()
                    main_window_controller.on_ui_show_notification(
                        packet.message, "error"
                    )

    @staticmethod
    def __handle_session_packet(packet: SessionPacket):
        """Xử lý gói tin SessionPacket."""
        if not packet.session_id or not packet.status:
            logger.error("Received SessionPacket with empty fields.")
            return

        if packet.status == Status.SESSION_STARTED:
            if not packet.role:
                logger.error("SessionPacket missing role")
                return
            logger.info(f"Session started: {packet.session_id} as {packet.role}")

            SessionManager.create_session(
                packet.session_id,
                packet.role,
                partner_hostname=packet.partner_hostname or "Unknown",
            )

        # Nếu session kết thúc, dọn dẹp
        elif (
            packet.status == Status.SESSION_ENDED
            or packet.status == Status.SESSION_TIMEOUT
        ):
            logger.debug(f"Received session ended for: {packet.session_id}")
            SessionManager.remove_session(packet.session_id, False)

    # ----------------------------
    # Controller
    # ----------------------------

    @staticmethod
    def __handle_video_config_packet(packet: VideoConfigPacket):
        """
        Xử lý VideoConfigPacket - setup decoder.
        Packet này được gửi TRƯỚC khi gửi video frames.
        """
        SessionManager.handle_config_data(
            packet.session_id,
            packet.extradata,
            packet.width,
            packet.height,
            packet.fps,
            packet.codec,
        )

    @staticmethod
    def __handle_video_stream_packet(packet: VideoStreamPacket):
        """
        Xử lý VideoStreamPacket - decode và gửi frame cho controller.
        """
        if not packet.session_id or not packet.video_data:
            logger.error("Received VideoStreamPacket with empty fields.")
            return
        # Forward video data and optional cursor info to SessionManager
        SessionManager.handle_video_data(
            packet.session_id,
            packet.video_data,
            cursor_type=getattr(packet, "cursor_type", None),
            cursor_position=getattr(packet, "cursor_position", None),
        )

    # ----------------------------
    # Host
    # ----------------------------

    @staticmethod
    def __handle_connection_request_packet(packet: ConnectionRequestPacket):
        """Xử lý ConnectionRequestPacket"""
        if not packet.sender_id or not packet.password:
            logger.error("Received ConnectionRequestPacket with empty fields.")
            return

        status = (
            Status.SUCCESS
            if ClientManager.verify_password(packet.password)
            else Status.INVALID_PASSWORD
        )

        from client.handlers.send_handler import SendHandler

        SendHandler.send_authentication_password_packet(
            receiver_id=packet.sender_id,
            status=status,
        )

    @staticmethod
    def __handle_keyboard_packet(packet: KeyboardPacket):
        """Xử lý KeyboardPacket - thực thi sự kiện bàn phím trên máy host"""
        if not packet.event_type or not packet.key_type or packet.key_value is None:
            logger.error("Received KeyboardPacket with empty fields.")
            return

        # Thực thi sự kiện bàn phím
        KeyboardExecutorService.execute_keyboard_event(packet)
        logger.debug(
            f"Executed keyboard event: {packet.event_type.value} - {packet.key_type.value} - {packet.key_value}"
        )

    @staticmethod
    def __handle_mouse_packet(packet: MousePacket):
        """Xử lý MousePacket - thực thi sự kiện chuột trên máy host"""
        if not packet.event_type or packet.position is None:
            logger.error("Received MousePacket with empty fields.")
            return

        # Thực thi sự kiện chuột
        MouseExecutorService.execute_mouse_event(packet)
        logger.debug(
            f"Executed mouse event: {packet.event_type.value} - Position: {packet.position} - Button: {packet.button.value}"
        )

    @staticmethod
    def __handle_chat_message_packet(packet: ChatMessagePacket):
        """Xử lý ChatMessagePacket - hiển thị tin nhắn chat"""
        if not packet.session_id or not packet.message:
            logger.error("Received ChatMessagePacket with empty fields.")
            return

        SessionManager.handle_chat_message(
            packet.session_id, packet.sender_role, packet.message, packet.timestamp
        )

    @staticmethod
    def __handle_file_metadata_packet(packet: FileMetadataPacket):
        """Xử lý FileMetadataPacket - nhận thông tin file"""
        if not packet.session_id or not packet.file_id or not packet.filename:
            logger.error("Received FileMetadataPacket with empty fields.")
            return

        SessionManager.handle_file_metadata(
            packet.session_id,
            packet.file_id,
            packet.filename,
            packet.filesize,
            packet.sender_role,
        )

    @staticmethod
    def __handle_file_accept_packet(packet: FileAcceptPacket):
        """Xử lý FileAcceptPacket - bên gửi nhận được xác nhận"""
        if not packet.session_id or not packet.file_id:
            logger.error("Received FileAcceptPacket with empty fields.")
            return

        SessionManager.handle_file_accept(packet.session_id, packet.file_id)

    @staticmethod
    def __handle_file_reject_packet(packet: FileRejectPacket):
        """Xử lý FileRejectPacket - bên gửi nhận được từ chối"""
        if not packet.session_id or not packet.file_id:
            logger.error("Received FileRejectPacket with empty fields.")
            return

        SessionManager.handle_file_reject(packet.session_id, packet.file_id)

    @staticmethod
    def __handle_file_chunk_packet(packet: FileChunkPacket):
        """Xử lý FileChunkPacket - nhận chunk dữ liệu file"""
        if not packet.session_id or not packet.file_id or packet.chunk_data is None:
            logger.error("Received FileChunkPacket with empty fields.")
            return

        SessionManager.handle_file_chunk(
            packet.session_id,
            packet.file_id,
            packet.chunk_index,
            packet.chunk_data,
            packet.total_chunks,
        )

    @staticmethod
    def __handle_file_complete_packet(packet: FileCompletePacket):
        """Xử lý FileCompletePacket - file đã được gửi xong"""
        if not packet.session_id or not packet.file_id:
            logger.error("Received FileCompletePacket with empty fields.")
            return

        SessionManager.handle_file_complete(
            packet.session_id, packet.file_id, packet.success, packet.message
        )
