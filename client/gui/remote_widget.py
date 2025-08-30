
from client.auth.auth_manager import AuthManager
from client.network.network_client import NetworkClient


class RemoteWidget(QLabel):
    """Widget hiển thị màn hình điều khiển từ xa"""

    def __init__(self):
        super().__init__()
        self.network_client = NetworkClient()
        self.auth_manager = AuthManager(self.network_client)
        self.remote_widget = None # Chưa tạo, chờ auth thành công
        self.init_ui()
        
    