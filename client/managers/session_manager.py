import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from PyQt5.QtGui import QPixmap, QImage
from common.h264 import H264Decoder

logger = logging.getLogger(__name__)


@dataclass
class SessionResources:
    """Lưu trữ tất cả tài nguyên của một session."""

    role: str
    decoder: Optional[Any] = None
    widget: Optional[Any] = None


class SessionManager:
    """Quản lý các phiên làm việc của client (controller / host)."""

    _sessions: Dict[str, SessionResources] = {}

    @classmethod
    def create_session(cls, session_id: str, role: str):
        """Tạo session mới và khởi tạo các resources cần thiết."""
        cls._sessions[session_id] = SessionResources(role=role)

        try:
            if role == "controller":
                from client.controllers.main_window_controller import main_window_controller 
                main_window_controller.widget_creation_requested.emit(session_id)
            elif role == "host":
                from client.services.screen_share_service import screen_share_service
                screen_share_service.add_session(session_id)
            else:
                logger.warning(f"Unknown role: {role} for session: {session_id}")

        except Exception as e:
            logger.error(f"Error creating session {session_id}: {e}", exc_info=True)

    #---------
    #Xử lý dữ liệu liên quan đến session
    #---------

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

        if (
            not session
            or not session.widget
            or not hasattr(session.widget, "controller")
        ):
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
    def handle_video_data(cls, session_id: str, video_data: bytes):
        """Xử lý dữ liệu video nhận được cho session."""
        session = cls._sessions.get(session_id)
        if not session:
            logger.warning(f"Received video data for unknown session: {session_id}")
            return

        decoder = session.decoder
        if not decoder:
            logger.warning(f"No decoder found for session: {session_id}")
            return

        session = cls._sessions.get(session_id)
        if (
            not session
            or not session.decoder
            or not session.widget
            or not hasattr(session.widget, "controller")
        ):
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

            session.widget.controller.handle_decoded_frame(pixmap)

        except Exception as e:
            logger.error(
                f"Error handling video data for session {session_id}: {e}",
                exc_info=True,
            )

    #---------
    #Xử lý khi session kết thúc
    #---------
    @classmethod
    def remove_widget_session(cls, session_id: str):
        """Xóa session controller và dọn dẹp tài nguyên."""
        if (
            session_id in cls._sessions
            and cls._sessions[session_id].role == "controller"
        ):
            del cls._sessions[session_id]
            from client.handlers.send_handler import SendHandler

            SendHandler.send_end_session_packet(session_id)
        else:
            logger.warning(f"Attempted to remove non-controller session: {session_id}")

    @classmethod
    def remove_session(cls, session_id: str, send_end_packet: bool = True):
        """Xóa phiên làm việc và dọn dẹp tài nguyên."""
        if session_id in cls._sessions:
            if cls._sessions[session_id].role == "controller":
                widget = cls._sessions[session_id].widget
                if widget and hasattr(widget, "close"):
                    widget.close()
                decoder = cls._sessions[session_id].decoder
                if decoder and hasattr(decoder, "close"):
                    decoder.close()
            elif cls._sessions[session_id].role == "host":
                from client.services.screen_share_service import screen_share_service
                screen_share_service.remove_session(session_id)                
            else:
                logger.warning(
                    f"Attempted to remove session with unknown role: {session_id}"
                )

            del cls._sessions[session_id]
            if send_end_packet:
                from client.handlers.send_handler import SendHandler
                SendHandler.send_end_session_packet(session_id)
        else:
            logger.warning(f"Attempted to remove non-existent session: {session_id}")    

    @classmethod
    def cleanup_all_sessions(cls):
        """Dọn dẹp tất cả sessions - dùng khi đóng ứng dụng."""
        session_ids = list(cls._sessions.keys())
        for session_id in session_ids:
            cls.remove_session(session_id, send_end_packet=True)
        logger.info("All sessions cleaned up")

    
    

    
