from argparse import Namespace


class Config:
    client: bool = False
    server: bool = False
    debug: bool = False
    ip: str = "127.0.0.1"
    port: int = 5000
    fps: int = 20
    max_clients: int = 10
    session_timeout: int = 3600
    ssl: bool = False
    cert: str | None = None
    key: str | None = None

    @classmethod
    def save(cls, args: Namespace):
        for key, value in vars(args).items():
            setattr(cls, key, value)
