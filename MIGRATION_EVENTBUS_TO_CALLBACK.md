# Migration từ EventBus sang CallbackManager

## Thay đổi

Đã loại bỏ hoàn toàn EventBus và thay thế bằng CallbackManager đơn giản hơn.

## Chi tiết thay đổi

### Thêm mới

-   `client/core/callback_manager.py`: Hệ thống callback mới thay thế EventBus

### Đã cập nhật

-   `client/client.py`: Loại bỏ EventBus.start() và EventBus.stop()
-   `client/controllers/main_window_controller.py`: Thay EventBus bằng callback_manager
-   `client/service/connection_service.py`: Thay EventBus bằng callback_manager
-   `client/service/auth_service.py`: Thay EventBus bằng callback_manager
-   `client/network/socket_client.py`: Thay EventBus bằng callback_manager

### Có thể xóa

-   `client/core/event_bus.py`: Không còn sử dụng

## Ưu điểm của CallbackManager so với EventBus

1. **Đơn giản hơn**: Không cần thread riêng và queue
2. **Hiệu năng tốt hơn**: Gọi trực tiếp callback mà không qua queue
3. **Ít phức tạp**: Không có thread synchronization
4. **Dễ debug**: Callback được gọi đồng bộ, dễ trace lỗi

## API mới

```python
from client.core.callback_manager import callback_manager

# Đăng ký callback
callback_manager.register_callback("event_type", callback_function)

# Gọi callbacks
callback_manager.trigger_callbacks("event_type", data)

# Hủy đăng ký
callback_manager.unregister_callback("event_type", callback_function)
```

## Lưu ý

Tất cả các chức năng cũ vẫn hoạt động bình thường, chỉ thay đổi cách thức nội bộ từ EventBus sang CallbackManager.
