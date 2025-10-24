import logging
from PyQt5.QtGui import QPixmap, QImage

from common.enums import Status
from client.managers.client_manager import ClientManager
from client.controllers.main_window_controller import main_window_controller
from client.managers.session_manager import SessionManager
from common.packets import (
    AssignIdPacket,
    ConnectionRequestPacket,
    ConnectionResponsePacket,
    KeyboardPacket,
    SessionPacket,
    VideoConfigPacket,
    VideoStreamPacket,
    Packet,
)
from common.h264 import H264Decoder

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
            KeyboardPacket: cls.__handle_keyboard_packet,  # Host nhận keyboard events
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
        elif packet.status == Status.SESSION_ENDED:
            logger.info(f"Received session ended for: {packet.session_id}")

            # Kiểm tra session có tồn tại không trước khi xử lý
            if SessionManager.session_exists(packet.session_id):
                session_role = SessionManager.get_session_role(packet.session_id)

                # Nếu là controller session, đóng widget nếu có
                if session_role == "controller":
                    widget = SessionManager.get_session_widget(packet.session_id)
                    if widget and hasattr(widget, "close"):
                        try:
                            widget._cleanup_done = (
                                True  # Prevent sending another end session
                            )
                            widget.close()
                            logger.debug(
                                f"Closed widget for session: {packet.session_id}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Error closing widget for session {packet.session_id}: {e}"
                            )

                # Remove session từ SessionManager
                SessionManager.remove_session(packet.session_id)

                # Thông báo cho main window controller
                main_window_controller.status_updated.emit(
                    f"Session {packet.session_id} ended by remote."
                )
            else:
                logger.warning(
                    f"Received session ended for non-existent session: {packet.session_id}"
                )

    # ----------------------------
    # Controller
    # ----------------------------

    @staticmethod
    def __handle_video_config_packet(packet: VideoConfigPacket):
        """
        Xử lý VideoConfigPacket - setup decoder.
        Packet này được gửi TRƯỚC khi gửi video frames.
        """
        try:
            session_id = packet.session_id
            # Tạo decoder cho session
            decoder = H264Decoder(extradata=packet.extradata)
            SessionManager.set_session_decoder(session_id, decoder)

            # Gửi thông tin config đến controller để cập nhật UI
            widget = SessionManager.get_session_widget(session_id)
            if widget and hasattr(widget, "controller"):
                widget.controller.handle_video_config_received(
                    packet.width, packet.height, packet.fps, packet.codec
                )

        except Exception as e:
            logger.error(f"Error handling VideoConfigPacket: {e}", exc_info=True)

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

        session_id = packet.session_id

        try:
            # Lấy decoder cho session
            decoder = SessionManager.get_session_decoder(session_id)
            if not decoder:
                logger.warning(f"No decoder found for session: {session_id}")
                return

            # Giải mã video frame
            pil_image = decoder.decode(packet.video_data)
            if not pil_image:
                return  # Frame chưa hoàn chỉnh (B-frame)

            # Chuyển PIL Image -> QPixmap
            img_data = pil_image.tobytes("raw", "RGB")
            qimage = QImage(
                img_data,
                pil_image.width,
                pil_image.height,
                pil_image.width * 3,
                QImage.Format.Format_RGB888,
            )
            pixmap = QPixmap.fromImage(qimage)

            # Gửi frame đã decode cho controller
            widget = SessionManager.get_session_widget(session_id)
            if widget and hasattr(widget, "controller"):
                widget.controller.handle_decoded_frame(pixmap)

        except Exception as e:
            logger.error(
                f"Error handling VideoStreamPacket for session {session_id}: {e}",
                exc_info=True,
            )

            # Thông báo lỗi cho controller
            widget = SessionManager.get_session_widget(session_id)
            if widget and hasattr(widget, "controller"):
                widget.controller.handle_decode_error(f"Decode error: {str(e)}")

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
        """Xử lý KeyboardPacket - thực thi sự kiện bàn phím nhận được"""
        try:
            if not hasattr(packet, "session_id") or not hasattr(packet, "event_type"):
                logger.error("Invalid keyboard packet")
                return

            if not packet.session_id:
                logger.error("Received KeyboardPacket with empty session_id")
                return

            # Lấy keyboard executor từ session
            session = SessionManager.get_session_keyboard_executor(packet.session_id)
            if not session:
                logger.warning(
                    f"No keyboard executor found for session: {packet.session_id}"
                )
                return

            # Thực thi sự kiện bàn phím
            session.execute_keyboard_packet(packet)
            logger.debug(f"Executed keyboard packet for session: {packet.session_id}")

        except Exception as e:
            logger.error(f"Error handling keyboard packet: {e}", exc_info=True)
