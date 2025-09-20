"""
EventBus - Hệ thống pub/sub để quản lý events trong ứng dụng
"""
from typing import Any, Callable, Optional, TypedDict
import threading
from queue import Queue, Empty
import logging

logger = logging.getLogger(__name__)

Event = TypedDict(
    "Event", {
        "type": str,
        "data": Any,
        "source": str,
    }
)


class EventBus:
    """Pure static EventBus để publish/subscribe events"""
    
    # Class variables để lưu trữ state
    _subscribers: dict[str, Callable[[Any], None]] = {}
    _lock = threading.RLock()
    _event_queue: Queue[Event] = Queue()
    _processing_thread = None
    _shutdown_event = threading.Event()
    _running = False
    
    @classmethod
    def publish(cls, event_type: str, data: Optional[Any] = None, source: Optional[str] = None):
        """Publish event vào hàng đợi"""
        if not cls._running:
            logger.warning("EventBus is not running. Cannot publish events.")
            return False
        
        event: Event = {
            "type": event_type,
            "data": data,
            "source": source or "Unknown",
        }
        cls._event_queue.put(event)
        logger.debug(f"Event of type '{event_type}' published")
        return True
        
    @classmethod 
    def subscribe(cls, event_type: str, handler: Callable[[Any], None]):
        """Subscribe handler cho event type"""
        with cls._lock:
            cls._subscribers[event_type] = handler
        logger.debug(f"Handler subscribed to event type '{event_type}'")
        
    @classmethod
    def unsubscribe(cls, event_type: str, handler: Callable[[Any], None]):
        """Unsubscribe handler khỏi event type"""  
        with cls._lock:
            if event_type in cls._subscribers and cls._subscribers[event_type] == handler:
                del cls._subscribers[event_type]
                logger.debug(f"Handler unsubscribed from event type '{event_type}'")

    @classmethod
    def start(cls):
        """Bắt đầu EventBus processing thread"""
        with cls._lock:
            if cls._running:
                return
                        
            cls._running = True
            cls._shutdown_event.clear()
            cls._processing_thread = threading.Thread(
                target=cls._process_events,
                name="EventBus-Processor",
                daemon=True,
            )
            cls._processing_thread.start()                
    
    @classmethod 
    def stop(cls):
        """Dừng EventBus processing thread"""
        with cls._lock:
            if not cls._running:
                return            
            
            cls._running = False
            cls._shutdown_event.set()
            # Thêm sự kiện rỗng để đánh thức luồng nếu nó đang chờ
            cls._event_queue.put(None)

        if cls._processing_thread and cls._processing_thread.is_alive():
            cls._processing_thread.join(timeout=2)
            cls._processing_thread = None
        logger.debug("EventBus stopped")

    @classmethod
    def _process_events(cls):
        """Processing thread để xử lý events"""
        while cls._running and not cls._shutdown_event.is_set():
            try:
                event = cls._event_queue.get(timeout=0.1)
                if event is None:
                    continue
                
                with cls._lock:
                    if event["type"] in cls._subscribers:
                        cls._subscribers[event["type"]](event.get("data"))
                
                cls._event_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing event - {e}")
                continue