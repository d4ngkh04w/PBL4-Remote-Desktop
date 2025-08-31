import datetime
import os

from dotenv import load_dotenv

load_dotenv()


class ServerConfig:
    SERVER_HOST = os.getenv("HOST", "127.0.0.1")
    SERVER_PORT = int(os.getenv("PORT", 5000))


class DisplayConfig:
    FULLSCREEN = False
    SCREEN_QUALITY = int(os.getenv("SCREEN_QUALITY", 80))
    FRAME_RATE = int(os.getenv("FRAME_RATE", 30))
    SCREEN_WIDTH = int(os.getenv("SCREEN_WIDTH", 1920))
    SCREEN_HEIGHT = int(os.getenv("SCREEN_HEIGHT", 1080))


class SecurityConfig:
    SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", 3600))
    CERT_FILE = os.getenv("CERT_FILE", "cert.pem")
    KEY_FILE = os.getenv("KEY_FILE", "key.pem")


class LoggingConfig:
    LOG_SERVER = os.getenv(
        "LOG_SERVER", f"logs/server_{datetime.datetime.now().strftime('%Y-%m-%d')}.log"
    )
    LOG_CLIENT = os.getenv(
        "LOG_CLIENT", f"logs/client_{datetime.datetime.now().strftime('%Y-%m-%d')}.log"
    )
