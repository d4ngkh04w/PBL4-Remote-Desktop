class SessionService:
    """Quản lý các phiên làm việc của client (controller / host)."""
    
    _sessions: dict[str, str] = {}  # session_id: role

    @classmethod
    def add_session(cls, session_id: str, role: str):
        """Thêm phiên làm việc mới."""
        cls._sessions[session_id] = role

    @classmethod
    def remove_session(cls, session_id: str):
        """Xóa phiên làm việc."""
        cls._sessions.pop(session_id, None)

    # ---------------------------
    # Các hàm kiểm tra trạng thái
    # ---------------------------
    
    @classmethod
    def is_in_session(cls) -> bool:
        """Kiểm tra có đang trong bất kỳ phiên làm việc nào không."""
        return bool(cls._sessions)

    @classmethod
    def is_in_hosting_session(cls) -> bool:
        """Kiểm tra có đang trong phiên làm việc với vai trò host không."""
        return "host" in cls._sessions.values()

    @classmethod
    def is_in_controlling_session(cls) -> bool:
        """Kiểm tra có đang trong phiên làm việc với vai trò controller không."""
        return "controller" in cls._sessions.values()

    # ---------------------------
    # Hàm lấy thông tin vai trò
    # ---------------------------
    
    @classmethod
    def get_roles(cls) -> set[str]:
        """Lấy danh sách vai trò hiện có (ví dụ: {'host', 'controller'})."""
        return set(cls._sessions.values())

    @classmethod
    def get_role(cls, session_id: str) -> str | None:
        """Lấy vai trò của client trong một phiên cụ thể."""
        return cls._sessions.get(session_id)
