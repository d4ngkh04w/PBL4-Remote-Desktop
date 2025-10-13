import logging


from common.enums import Status
from client.managers.client_manager import ClientManager
from client.controllers.main_window_controller import MainWindowController
from client.managers.session_manager import SessionManager
from common.packets import (
    AssignIdPacket,
    ConnectionRequestPacket,
    ConnectionResponsePacket,
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
        main_window_controller = MainWindowController.get_instance()
        if main_window_controller:
            main_window_controller.on_client_id_received()

    @staticmethod
    def __handle_connection_response_packet(packet: ConnectionResponsePacket):
        """Xử lý ConnectionResponsePacket"""
        if not hasattr(packet, "connection_status") or not hasattr(packet, "message"):
            logger.error("Invalid connection response packet")
            return
        main_window_controller = MainWindowController.get_instance()
        if not main_window_controller:
            logger.error("MainWindowController instance not found.")
            return

        if packet.connection_status == Status.INVALID_PASSWORD:
            if main_window_controller:
                main_window_controller.on_ui_show_notification(
                    "Connection rejected: Invalid password.", "error"
                )
                main_window_controller.on_ui_update_status(
                    "Connection rejected: Invalid password."
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
        logger.info(f"Handling SessionPacket: {packet}")
        # Thực hiện xử lý gói tin SessionPacket

    @staticmethod
    def __handle_video_config_packet(packet: VideoConfigPacket):
        """
        Xử lý VideoConfigPacket - setup decoder.
        Packet này được gửi TRƯỚC khi gửi video frames.
        """
        try:
            session_id = packet.session_id
            logger.info(f"Received VideoConfigPacket for session: {session_id}")

            # Lấy controller handler cho session
            # from client.handlers.controller_handler import ControllerHandler

            # controller = ControllerHandler.get_session_handler(session_id)
            # if controller:
            #     controller.handle_video_config_packet(packet)
            # else:
            #     logger.warning(f"No controller found for session: {session_id}")

        except Exception as e:
            logger.error(f"Error handling VideoConfigPacket: {e}", exc_info=True)

    @staticmethod
    def __handle_video_stream_packet(packet: VideoStreamPacket):
        """
        Xử lý VideoStreamPacket - decode and display.
        """
        try:
            session_id = packet.session_id

            # Lấy controller cho session
            # from client.handlers.controller_handler import ControllerHandler

            # controller = ControllerHandler.get_session_handler(session_id)
            # if controller:
            #     controller.handle_video_stream_packet(packet)
            # else:
            #     logger.warning(f"No controller found for session: {session_id}")

        except Exception as e:
            logger.error(f"Error handling VideoStreamPacket: {e}")

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
