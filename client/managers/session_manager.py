import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from PyQt5.QtGui import QPixmap, QImage
from common.h264 import H264Decoder

logger = logging.getLogger(__name__)


@dataclass
class SessionResources:
    """Lưu trữ tất cả tài nguyên của một session."""

    role: str
    partner_hostname: str = "Unknown"
    decoder: Optional[Any] = None
    widget: Optional[Any] = None
    chat_window: Optional[Any] = None  # Chat window for host role
    pending_file_transfers: Dict[str, Dict[str, Any]] = field(
        default_factory=dict
    )  # File transfer state


class SessionManager:
    """Quản lý các phiên làm việc của client (controller / host)."""

    _sessions: Dict[str, SessionResources] = {}

    @classmethod
    def create_session(
        cls, session_id: str, role: str, partner_hostname: str = "Unknown"
    ):
        """Tạo session mới và khởi tạo các resources cần thiết."""
        cls._sessions[session_id] = SessionResources(
            role=role, partner_hostname=partner_hostname
        )

        try:
            if role == "controller":
                from client.controllers.main_window_controller import (
                    main_window_controller,
                )

                main_window_controller.widget_creation_requested.emit(session_id)

                # Create chat window for controller
                from PyQt5.QtCore import QMetaObject, Qt, Q_ARG

                QMetaObject.invokeMethod(
                    main_window_controller,
                    "create_controller_chat_window",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, session_id),
                    Q_ARG(str, partner_hostname),
                )

            elif role == "host":
                from client.services.screen_share_service import screen_share_service

                screen_share_service.add_session(session_id)

                # Request chat window creation in main thread
                from client.controllers.main_window_controller import (
                    main_window_controller,
                )
                from PyQt5.QtCore import QMetaObject, Qt, Q_ARG

                # Use invokeMethod to create chat window in main Qt thread
                QMetaObject.invokeMethod(
                    main_window_controller,
                    "create_host_chat_window",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, session_id),
                    Q_ARG(str, partner_hostname),
                )

                logger.info(
                    f"Host session {session_id} created, chat window will be initialized in main thread"
                )
            else:
                logger.warning(f"Unknown role: {role} for session: {session_id}")

            # Notify controller that a new session was created
            from client.controllers.main_window_controller import main_window_controller

            main_window_controller.on_session_created()

        except Exception as e:
            logger.error(f"Error creating session {session_id}: {e}", exc_info=True)

    # ---------
    # Xử lý dữ liệu liên quan đến session
    # ---------

    @classmethod
    def handle_config_data(
        cls,
        session_id: str,
        extradata: bytes,
        width: int,
        height: int,
        fps: int,
        codec: str,
    ):
        """Xử lý dữ liệu config video cho session."""
        session = cls._sessions.get(session_id)

        if not session or not session.widget:
            logger.warning(
                f"Cannot handle config data for unknown or incomplete session: {session_id}"
            )
            return

        session.decoder = H264Decoder(extradata=extradata)

        try:
            session.widget.controller.handle_video_config_received(
                width, height, fps, codec
            )
        except Exception as e:
            logger.error(
                f"Error handling config data for session {session_id}: {e}",
                exc_info=True,
            )

    @classmethod
    def handle_video_data(
        cls,
        session_id: str,
        video_data: bytes,
        cursor_type: str | None = None,
        cursor_position: tuple[int, int] | None = None,
    ):
        """Xử lý dữ liệu video nhận được cho session. Có thể kèm cursor info."""
        session = cls._sessions.get(session_id)
        if not session:
            logger.warning(f"Received video data for unknown session: {session_id}")
            return

        decoder = session.decoder
        if not decoder:
            logger.warning(f"No decoder found for session: {session_id}")
            return

        if not session or not session.decoder or not session.widget:
            logger.warning(f"Incomplete session resources for session: {session_id}")
            return

        try:
            pil_image = session.decoder.decode(video_data)
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

            # Gửi frame cho widget
            session.widget.controller.handle_decoded_frame(pixmap)

            # Nếu có thông tin con trỏ, gửi luôn để overlay vẽ lên frame
            if cursor_type and cursor_position is not None:
                try:
                    # visible default là True (chúng ta không gửi visible riêng)
                    session.widget.controller.handle_cursor_info(
                        cursor_type, cursor_position, True
                    )
                except Exception:
                    logger.debug(
                        f"Failed to deliver cursor info for session {session_id}",
                        exc_info=True,
                    )

        except Exception as e:
            logger.error(
                f"Error handling video data for session {session_id}: {e}",
                exc_info=True,
            )

    @classmethod
    def handle_cursor_info(
        cls, session_id: str, cursor_type: str, position: tuple[int, int], visible: bool
    ):
        """Xử lý thông tin cursor nhận được cho session."""
        session = cls._sessions.get(session_id)
        if not session or not session.widget:
            logger.warning(
                f"Cannot handle cursor info for unknown or incomplete session: {session_id}"
            )
            return

        try:
            session.widget.controller.handle_cursor_info(cursor_type, position, visible)
        except Exception as e:
            logger.error(
                f"Error handling cursor info for session {session_id}: {e}",
                exc_info=True,
            )

    # ---------
    # Xử lý khi session kết thúc
    # ---------
    @classmethod
    def remove_widget_session(cls, session_id: str):
        """Xóa session controller và dọn dẹp tài nguyên."""
        if (
            session_id in cls._sessions
            and cls._sessions[session_id].role == "controller"
        ):
            session = cls._sessions[session_id]

            # Close chat window before deleting session
            if session.chat_window and hasattr(session.chat_window, "close"):
                from PyQt5.QtCore import QMetaObject, Qt

                QMetaObject.invokeMethod(
                    session.chat_window, "close", Qt.ConnectionType.QueuedConnection
                )
                logger.info(f"Chat window closed for controller session {session_id}")

            del cls._sessions[session_id]
            from client.handlers.send_handler import SendHandler

            logger.info(f"Send end session packet for: {session_id}")
            SendHandler.send_end_session_packet(session_id)

            # Notify controller that session ended
            from client.controllers.main_window_controller import main_window_controller

            main_window_controller.on_session_ended()
        else:
            logger.warning(f"Attempted to remove non-controller session: {session_id}")

    @classmethod
    def remove_session(cls, session_id: str, send_end_packet: bool = True):
        """Xóa phiên làm việc và dọn dẹp tài nguyên."""
        if session_id in cls._sessions:
            session = cls._sessions[session_id]

            if session.role == "controller":
                # Cleanup decoder trước
                if session.decoder and hasattr(session.decoder, "close"):
                    session.decoder.close()

                # Đóng widget sau - phải đóng trong Qt main thread
                if session.widget and hasattr(session.widget, "close"):
                    # Đặt flag để widget biết đang được đóng từ SessionManager
                    # Tránh emit disconnect_requested signal
                    session.widget._closed_by_manager = True

                    # Đóng widget trong main thread để tránh Qt threading issues
                    from PyQt5.QtCore import QMetaObject, Qt

                    QMetaObject.invokeMethod(
                        session.widget, "close", Qt.ConnectionType.QueuedConnection
                    )

                # Close chat window for controller
                if session.chat_window and hasattr(session.chat_window, "close"):
                    from PyQt5.QtCore import QMetaObject, Qt

                    QMetaObject.invokeMethod(
                        session.chat_window, "close", Qt.ConnectionType.QueuedConnection
                    )
                    logger.info(
                        f"Chat window closed for controller session {session_id}"
                    )

            elif session.role == "host":
                from client.services.screen_share_service import screen_share_service

                screen_share_service.remove_session(session_id)

                # Close chat window
                if session.chat_window and hasattr(session.chat_window, "close"):
                    from PyQt5.QtCore import QMetaObject, Qt

                    QMetaObject.invokeMethod(
                        session.chat_window, "close", Qt.ConnectionType.QueuedConnection
                    )
                    logger.info(f"Chat window closed for session {session_id}")
            else:
                logger.warning(
                    f"Attempted to remove session with unknown role: {session_id}"
                )

            del cls._sessions[session_id]

            # Chỉ gửi end packet khi được yêu cầu (chủ động disconnect)
            if send_end_packet:
                from client.handlers.send_handler import SendHandler

                logger.info(f"Sending end session packet for: {session_id}")
                SendHandler.send_end_session_packet(session_id)
            else:
                logger.info(f"Session ended by remote for: {session_id}")

            # Notify controller that session ended
            from client.controllers.main_window_controller import main_window_controller

            main_window_controller.on_session_ended()
        else:
            logger.warning(f"Attempted to remove non-existent session: {session_id}")

    @classmethod
    def cleanup_all_sessions(cls):
        """Dọn dẹp tất cả sessions - dùng khi đóng ứng dụng."""
        session_ids = list(cls._sessions.keys())
        for session_id in session_ids:
            cls.remove_session(session_id, send_end_packet=True)

        logger.info("All sessions cleaned up")

    # ---------
    # Chat and File Transfer handlers
    # ---------

    @classmethod
    def set_chat_window(cls, session_id: str, chat_window: Any):
        """Set chat window for a session"""
        session = cls._sessions.get(session_id)
        if session:
            session.chat_window = chat_window
            logger.info(f"Chat window set for session {session_id}")

    @classmethod
    def handle_chat_message(
        cls, session_id: str, sender_role: str, message: str, timestamp: float
    ):
        """Handle incoming chat message"""
        session = cls._sessions.get(session_id)
        if not session:
            logger.warning(f"Received chat message for unknown session: {session_id}")
            return

        # Display message in chat window (both host and controller have chat window now)
        if session.chat_window:
            logger.debug(f"Displaying chat message in window for session {session_id}")
            # Use QMetaObject.invokeMethod to ensure add_message runs in main thread
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG

            QMetaObject.invokeMethod(
                session.chat_window,
                "add_message",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, sender_role),
                Q_ARG(str, message),
                Q_ARG(float, timestamp),
            )
        else:
            logger.warning(
                f"No chat window for session {session_id}, cannot display message from {sender_role}: {message[:50]}"
            )

    @classmethod
    def handle_file_metadata(
        cls,
        session_id: str,
        file_id: str,
        filename: str,
        filesize: int,
        sender_role: str,
    ):
        """Handle incoming file metadata"""
        session = cls._sessions.get(session_id)
        if not session:
            logger.warning(f"Received file metadata for unknown session: {session_id}")
            return

        # Store file transfer info
        session.pending_file_transfers[file_id] = {
            "filename": filename,
            "filesize": filesize,
            "chunks_received": [],
            "save_path": None,
        }

        # Show accept/reject dialog in main thread
        if session.chat_window:
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG

            QMetaObject.invokeMethod(
                session.chat_window,
                "show_file_accept_dialog",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, file_id),
                Q_ARG(str, filename),
                Q_ARG(int, filesize),
                Q_ARG(str, sender_role),
            )

    @classmethod
    def handle_file_accept(cls, session_id: str, file_id: str):
        """Handle file accept notification (sender receives this)"""
        session = cls._sessions.get(session_id)
        if not session:
            logger.warning(f"Received file accept for unknown session: {session_id}")
            return

        # Add to pending so we can track completion (sender doesn't have save_path)
        session.pending_file_transfers[file_id] = {
            "save_path": None,
        }

        # Start sending chunks
        from client.services.file_transfer_service import FileTransferService

        FileTransferService.start_sending_chunks(file_id)

    @classmethod
    def handle_file_reject(cls, session_id: str, file_id: str):
        """Handle file reject notification (sender receives this)"""
        session = cls._sessions.get(session_id)
        if not session:
            return

        # Cancel the pending transfer
        from client.services.file_transfer_service import FileTransferService

        FileTransferService.cancel_transfer(file_id)

        # Update UI
        if session.chat_window:
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG

            QMetaObject.invokeMethod(
                session.chat_window,
                "update_file_transfer_status",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, file_id),
                Q_ARG(str, "Rejected"),
            )

    @classmethod
    def handle_file_chunk(
        cls,
        session_id: str,
        file_id: str,
        chunk_index: int,
        chunk_data: bytes,
        total_chunks: int,
    ):
        """Handle incoming file chunk"""
        session = cls._sessions.get(session_id)
        if not session:
            return

        transfer = session.pending_file_transfers.get(file_id)
        if not transfer:
            return

        # Store chunk
        transfer["chunks_received"].append((chunk_index, chunk_data))

    @classmethod
    def handle_file_complete(
        cls, session_id: str, file_id: str, success: bool, message: str
    ):
        """Handle file transfer completion"""
        session = cls._sessions.get(session_id)
        if not session:
            logger.warning(f"Received file complete for unknown session: {session_id}")
            return

        transfer = session.pending_file_transfers.get(file_id)
        if not transfer:
            logger.warning(
                f"File transfer {file_id} not found for session {session_id}"
            )
            return

        # Receiver has save_path, sender doesn't
        is_receiver = transfer.get("save_path") is not None

        if is_receiver:
            if success:
                # Write all chunks to file
                try:
                    # Sort chunks by index
                    chunks = sorted(transfer["chunks_received"], key=lambda x: x[0])
                    with open(transfer["save_path"], "wb") as f:
                        for _, chunk_data in chunks:
                            f.write(chunk_data)

                    logger.info(f"File {file_id} saved to {transfer['save_path']}")

                    # Send confirmation back to sender
                    from client.handlers.send_handler import SendHandler

                    SendHandler.send_file_complete_packet(
                        session_id=session_id,
                        file_id=file_id,
                        success=True,
                        message="File saved successfully",
                    )

                    # Update UI in main thread
                    if session.chat_window:
                        from PyQt5.QtCore import QMetaObject, Qt, Q_ARG

                        QMetaObject.invokeMethod(
                            session.chat_window,
                            "update_file_transfer_status",
                            Qt.ConnectionType.QueuedConnection,
                            Q_ARG(str, file_id),
                            Q_ARG(str, "File Received"),
                        )
                except Exception as e:
                    logger.error(f"Error saving file {file_id}: {e}")

                    # Send failure confirmation back to sender
                    from client.handlers.send_handler import SendHandler

                    SendHandler.send_file_complete_packet(
                        session_id=session_id,
                        file_id=file_id,
                        success=False,
                        message=str(e),
                    )

                    if session.chat_window:
                        from PyQt5.QtCore import QMetaObject, Qt, Q_ARG

                        QMetaObject.invokeMethod(
                            session.chat_window,
                            "update_file_transfer_status",
                            Qt.ConnectionType.QueuedConnection,
                            Q_ARG(str, file_id),
                            Q_ARG(str, "Failed"),
                        )
            else:
                logger.warning(f"File transfer {file_id} failed: {message}")
                if session.chat_window:
                    from PyQt5.QtCore import QMetaObject, Qt, Q_ARG

                    QMetaObject.invokeMethod(
                        session.chat_window,
                        "update_file_transfer_status",
                        Qt.ConnectionType.QueuedConnection,
                        Q_ARG(str, file_id),
                        Q_ARG(str, "Failed"),
                    )
        else:
            # Sender side
            if session.chat_window:
                from PyQt5.QtCore import QMetaObject, Qt, Q_ARG

                status = "File Sent" if success else "Failed"
                QMetaObject.invokeMethod(
                    session.chat_window,
                    "update_file_transfer_status",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, file_id),
                    Q_ARG(str, status),
                )

        # Remove from pending
        if file_id in session.pending_file_transfers:
            del session.pending_file_transfers[file_id]

    @classmethod
    def get_all_sessions_info(cls) -> Dict[str, Dict[str, Any]]:
        """Get information about all active sessions for UI display"""
        sessions_info = {}
        for session_id, session in cls._sessions.items():
            sessions_info[session_id] = {
                "role": session.role,
                "partner_hostname": session.partner_hostname,
                "has_chat": session.chat_window is not None,
            }
        return sessions_info
