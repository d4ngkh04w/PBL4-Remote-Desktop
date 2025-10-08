"""
CallbackManager - Hệ thống callback để thay thế EventBus
"""

from typing import Any, Callable, Dict, List
import threading
import logging

logger = logging.getLogger(__name__)


class CallbackManager:
    """Manager để đăng ký và gọi callbacks thay thế cho EventBus"""

    def __init__(self):
        self._callbacks: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()

    def register_callback(self, event_type: str, callback: Callable[[Any], None]):
        """Đăng ký callback cho event type"""
        with self._lock:
            if event_type not in self._callbacks:
                self._callbacks[event_type] = []
            self._callbacks[event_type].append(callback)
        logger.debug(f"Callback registered for event type '{event_type}'")

    def unregister_callback(self, event_type: str, callback: Callable[[Any], None]):
        """Hủy đăng ký callback"""
        with self._lock:
            if (
                event_type in self._callbacks
                and callback in self._callbacks[event_type]
            ):
                self._callbacks[event_type].remove(callback)
                if not self._callbacks[event_type]:
                    del self._callbacks[event_type]
        logger.debug(f"Callback unregistered for event type '{event_type}'")

    def trigger_callbacks(self, event_type: str, data: Any = None):
        """Gọi tất cả callbacks đã đăng ký cho event type"""
        with self._lock:
            if event_type in self._callbacks:
                for callback in self._callbacks[event_type][
                    :
                ]:  # Copy để tránh concurrent modification
                    try:
                        callback(data)
                    except Exception as e:
                        logger.error(f"Error in callback for event '{event_type}': {e}")
        logger.debug(f"Triggered callbacks for event type '{event_type}'")

    def clear_callbacks(self, event_type: str | None = None):
        """Xóa callbacks"""
        with self._lock:
            if event_type:
                if event_type in self._callbacks:
                    del self._callbacks[event_type]
            else:
                self._callbacks.clear()
        logger.debug(
            f"Cleared callbacks for event type '{event_type if event_type else 'all'}'"
        )


# Global instance để sử dụng
callback_manager = CallbackManager()
