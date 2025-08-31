import secrets
import string

import bcrypt


class PasswordManager:
    """
    Quản lý việc tạo, hash và xác thực mật khẩu một cách an toàn bằng bcrypt.
    """

    @staticmethod
    def generate_password(length: int = 8) -> str:
        """
        Tạo một mật khẩu ngẫu nhiên với độ dài cho trước.
        """
        characters = string.ascii_letters + string.digits + string.punctuation
        password = "".join(secrets.choice(characters) for _ in range(length))
        return password

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash mật khẩu bằng bcrypt.
        """
        password_bytes = password.encode()
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode()  # chuyển về string để lưu trữ

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Xác thực mật khẩu so với hash đã lưu.
        """
        password_bytes = password.encode()
        hashed_bytes = hashed.encode()
        return bcrypt.checkpw(password_bytes, hashed_bytes)
