import os
from dotenv import load_dotenv
import datetime

load_dotenv()


class NetworkConfig:
    SERVER_HOST = os.getenv("HOST", "127.0.0.1")
    SERVER_PORT = int(os.getenv("PORT", 5000))
    MAX_CLIENTS = int(os.getenv("MAX_CLIENTS", 5))
    TIMEOUT = int(os.getenv("TIMEOUT", 30))
    BUFFER_SIZE = int(os.getenv("BUFFER_SIZE", 8192))


class DisplayConfig:
    FULLSCREEN = False
    SCREEN_QUALITY = int(os.getenv("SCREEN_QUALITY", 80))
    FRAME_RATE = int(os.getenv("FRAME_RATE", 30))
    SCREEN_WIDTH = int(os.getenv("SCREEN_WIDTH", 1920))
    SCREEN_HEIGHT = int(os.getenv("SCREEN_HEIGHT", 1080))


class SecurityConfig:
    ENCRYPTION_ENABLED = True
    SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", 3600))


class LoggingConfig:
    # LOG_FILE = os.getenv(
    #     "LOG_FILE", f"logs/remote_{datetime.datetime.now().strftime('%Y-%m-%d')}.log"
    # )
    LOG_SERVER = os.getenv(
        "LOG_SERVER", f"logs/server_{datetime.datetime.now().strftime('%Y-%m-%d')}.log"
    )
    LOG_CLIENT = os.getenv(
        "LOG_CLIENT", f"logs/client_{datetime.datetime.now().strftime('%Y-%m-%d')}.log"
    )
