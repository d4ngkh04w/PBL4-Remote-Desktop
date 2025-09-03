from common.database import get_db_instance
from common.logger import logger

class SessionManager:
    def __init__(self):
        self.db = get_db_instance()
        self.active_sessions = {}  # key: session_id, value: session_info

    def create_session(self, controller_id: str, host_id: str):
        """Tạo session mới"""
        try:
            if not self.db.is_client_online(controller_id):
                raise ValueError(f"Controller {controller_id} is not online")
            if not self.db.is_client_online(host_id):
                raise ValueError(f"Host {host_id} is not online")

            # Tạo session mới
            session_id = self.db.create_session(controller_id, host_id)            

            # Cập nhật status clients
            self.db.update_client_status(controller_id, 'IN_SESSION_CONTROLLER')
            self.db.update_client_status(host_id, 'IN_SESSION_HOST')

            # Lưu session vào memory
            self.active_sessions[session_id] = {
                'controller_id': controller_id,
                'host_id': host_id,
                'status': 'ACTIVE'
            }

            logger.info(f"Session {session_id} created between controller {controller_id} and host {host_id}")
            return session_id, "Session created successfully"
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise e
        
    def end_session(self, session_id):
        """Kết thúc session"""
        try:
            if session_id in self.active_sessions:
                session_info = self.active_sessions[session_id]

                # Cập nhật status clients về ONLINE
                self.db.update_client_status(session_info['controller_id'], 'ONLINE')
                self.db.update_client_status(session_info['host_id'], 'ONLINE')

                # Xoá session khỏi memory
                del self.active_sessions[session_id]

                logger.info(f"Session {session_id} ended")
                return True
        except Exception as e:
            logger.error(f"Failed to end session {session_id}: {e}")
            return False
        
    def get_session_info(self, session_id):
        """Lấy thông tin session"""
        return self.active_sessions.get(session_id)
    
    def is_client_in_session(self, client_id):
        """Kiểm tra xem client có đang trong session không"""
        for session in self.active_sessions.values():
            if session['controller_id'] == client_id or session['host_id'] == client_id:
                return True
        return False