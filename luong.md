🔄 Luồng Hoạt Động Client-New
1. Khởi Động Application
client-new/client.py (main entry point)
    ↓
Initialize EventBus
    ↓
Start Services: Session, Connection, Auth, Display, Input, ScreenSharing
    ↓
Create MainWindow + MainWindowController
    ↓
Connect to Server
2. Kết Nối Đến Server
User clicks "Connect to Server"
    ↓
MainWindowController.connect_to_server()
    ↓
ConnectionService.connect_to_server()
    ↓
SocketClient.connect()
    ↓
Server assigns ID → AssignIdPacket
    ↓
SessionService.handle_assign_id_packet()
    ↓
EventBus publishes SESSION_INFO_UPDATE
    ↓
MainWindowController updates UI (ID display)
3. Luồng HOST (Chia Sẻ Màn Hình)
Another client requests connection
    ↓
ConnectionService receives RequestConnectionPacket
    ↓
EventBus publishes UI_SHOW_MESSAGE
    ↓
MainWindowController shows dialog "Accept connection?"
    ↓
User accepts → ConnectionService.accept_connection_request()
    ↓
Send RequestPasswordPacket to controller
    ↓
Receive SendPasswordPacket from controller
    ↓
ConnectionService.handle_password_verification()
    ↓
If correct → EventBus publishes AUTH_SUCCESS
    ↓
SessionService creates session with role=HOST
    ↓
EventBus publishes SESSION_START
    ↓
ScreenSharingService.start_sharing()
    ↓
Capture screen → compress → send ImagePacket/FrameUpdatePacket
4. Luồng CONTROLLER (Điều Khiển Từ Xa)
User enters Host ID + Password, clicks "Connect"
    ↓
MainWindowController.connect_to_partner()
    ↓
AuthService.set_entered_password()
    ↓
SessionService.initiate_controller_session()
    ↓
ConnectionService.send_connection_request()
    ↓
Receive RequestPasswordPacket from host
    ↓
ConnectionService automatically sends password
    ↓
Receive AuthenticationResultPacket
    ↓
If success → EventBus publishes AUTH_SUCCESS
    ↓
SessionService creates session with role=CONTROLLER
    ↓
EventBus publishes SESSION_START
    ↓
MainWindowController creates RemoteWidget
    ↓
DisplayService ready to receive frames
    ↓
Receive ImagePacket/FrameUpdatePacket
    ↓
DisplayService processes → EventBus publishes UI_UPDATE_FRAME
    ↓
RemoteWidget updates display
5. EventBus Communication Flow
Services communicate via EventBus:

NetworkClient → ConnectionService → EventBus → Other Services
                                      ↓
SessionService ← EventBus ← ConnectionService
        ↓
SessionService → EventBus → ScreenSharingService (HOST)
                     ↓
SessionService → EventBus → DisplayService (CONTROLLER)
                     ↓
All Services → EventBus → MainWindowController → UI Updates
6. Threading Model
Main Thread (UI):
- MainWindow, MainWindowController
- EventBus processes events
- UI updates via Qt signals

Background Threads:
- SocketClient: listener_thread, sender_thread
- EventBus: processing_thread
- ScreenSharingService: sharing_thread + compression_pool
- Services: all thread-safe
7. Key Components Interaction
EventBus làm trung tâm giao tiếp:

Không có direct calls giữa services
Mọi communication qua events
Thread-safe, decoupled
Services tự quản lý:

Mỗi service có lifecycle riêng
Subscribe events quan tâm
Publish events khi có update
Controllers chỉ làm UI coordination:

Subscribe UI events từ EventBus
Delegate business logic cho Services
Update UI thread-safe
8. Luồng Dữ Liệu Cụ Thể
capture_screen() → compress blocks → SocketClient.send_packet()
    ↓
Network → Controller SocketClient.receive_packet()
    ↓
ConnectionService._handle_packet() → EventBus.publish(FRAME_RECEIVED)
    ↓
DisplayService._on_frame_received() → process frame
    ↓
EventBus.publish(UI_UPDATE_FRAME) → MainWindowController
    ↓
RemoteWidget updates pixmap

Input (Controller → Host):
User mouse/keyboard → RemoteWidget events
    ↓
EventBus.publish(MOUSE_EVENT/KEYBOARD_EVENT)
    ↓
InputService._on_mouse/keyboard_event()
    ↓
Transform coordinates → SocketClient.send_packet()
    ↓
Network → Host receives input → apply to system

