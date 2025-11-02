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
            VideoConfigPacket: cls.__handle_video_config_packet,
            VideoStreamPacket: cls.__handle_video_stream_packet,
            KeyboardPacket: cls.__handle_keyboard_packet,
            MousePacket: cls.__handle_mouse_packet,
        }
        handler = packet_handlers.get(type(packet))
        if handler:
            handler(packet)
        else:
            logger.debug(f"Unhandled packet type: {type(packet)}")

    @staticmethod
    def __handle_assign_id_packet(packet: AssignIdPacket):
        """Xử lý AssignIdPacket"""
        if not hasattr(packet, "client_id"):
            logger.error("Invalid assign ID packet")
            return
        if not packet.client_id:
            logger.error("Received AssignIdPacket with empty fields.")
            return
        ClientManager.set_client_id(packet.client_id)
        main_window_controller.on_client_id_received()

    @staticmethod
    def __handle_connection_response_packet(packet: ConnectionResponsePacket):
        """Xử lý ConnectionResponsePacket"""
        if not hasattr(packet, "connection_status") or not hasattr(packet, "message"):
            logger.error("Invalid connection response packet")
            return

        if packet.connection_status == Status.INVALID_PASSWORD:
            main_window_controller.on_ui_show_notification(
                "Connection rejected: Invalid password.", "error"
            )
            main_window_controller.on_ui_update_status(
                "Connection rejected: Invalid password."
            )

        elif packet.connection_status == Status.ALREADY_CONNECTED:
            main_window_controller.on_ui_show_notification(
                "Connection rejected: Already connected to this host.", "error"
            )
            main_window_controller.on_ui_update_status(
                "Connection rejected: Already connected to this host."
            )

        elif packet.connection_status == Status.SERVER_FULL:
            logger.info("Connection rejected: Server is full.")
            if main_window_controller:
                main_window_controller.on_ui_show_notification(
                    "Connection rejected: Server is full.", "error"
                )
                main_window_controller.on_ui_update_status(
                    "Connection rejected: Server is full."
                )

        elif packet.connection_status == Status.RECEIVER_NOT_FOUND:
            logger.info("Connection rejected: Receiver not found.")
            if packet.message:
                if main_window_controller:
                    main_window_controller.on_ui_show_notification(
                        packet.message, "error"
                    )
                    main_window_controller.on_ui_update_status(packet.message)
            else:
                if main_window_controller:
                    main_window_controller.on_ui_show_notification(
                        "Receiver not found.", "error"
                    )
                    main_window_controller.on_ui_update_status("Receiver not found.")

    @staticmethod
    def __handle_session_packet(packet: SessionPacket):
        """Xử lý gói tin SessionPacket."""
        if (
            not hasattr(packet, "session_id")
            or not hasattr(packet, "status")
            or not hasattr(packet, "role")
        ):
            logger.error("Invalid session packet")
            return

        if not packet.session_id or not packet.status:
            logger.error("Received SessionPacket with empty fields.")
            return

        if packet.status == Status.SESSION_STARTED:
            if not packet.role:
                logger.error("SessionPacket missing role")
                return
            logger.info(f"Session started: {packet.session_id} as {packet.role}")

            SessionManager.create_session(packet.session_id, packet.role)

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
        if (
            not hasattr(packet, "session_id")
            or not hasattr(packet, "extradata")
            or not hasattr(packet, "width")
            or not hasattr(packet, "height")
            or not hasattr(packet, "fps")
            or not hasattr(packet, "codec")
        ):
            logger.error("Invalid video config packet")
            return
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
        if not hasattr(packet, "session_id") or not hasattr(packet, "video_data"):
            logger.error("Invalid video stream packet")
            return
        if not packet.session_id or not packet.video_data:
            logger.error("Received VideoStreamPacket with empty fields.")
            return

        SessionManager.handle_video_data(packet.session_id, packet.video_data)

    # ----------------------------
    # Host
    # ----------------------------

    @staticmethod
    def __handle_connection_request_packet(packet: ConnectionRequestPacket):
        """Xử lý ConnectionRequestPacket"""

        if not hasattr(packet, "password") or not hasattr(packet, "sender_id"):
            logger.error("Invalid connection request packet")
            return

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
        if (
            not hasattr(packet, "event_type")
            or not hasattr(packet, "key_type")
            or not hasattr(packet, "key_value")
        ):
            logger.error("Invalid keyboard packet")
            return

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
        if (
            not hasattr(packet, "event_type")
            or not hasattr(packet, "position")
            or not hasattr(packet, "button")
            or not hasattr(packet, "scroll_delta")
        ):
            logger.error("Invalid mouse packet")
            return

        if not packet.event_type or packet.position is None:
            logger.error("Received MousePacket with empty fields.")
            return

        # Thực thi sự kiện chuột
        MouseExecutorService.execute_mouse_event(packet)
        logger.debug(
            f"Executed mouse event: {packet.event_type.value} - Position: {packet.position} - Button: {packet.button.value}"
        )
