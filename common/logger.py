import logging
import sys
import pathlib

from colorama import Fore, Style, Back, init

init(autoreset=True)


class CustomFormatter(logging.Formatter):
    """
    Lớp định dạng log tùy chỉnh
    """

    SHORT_LEVELS = {
        "DEBUG": "DBG",
        "INFO": "INF",
        "WARNING": "WRN",
        "ERROR": "ERR",
        "CRITICAL": "CRT",
    }

    LEVEL_COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED + Style.BRIGHT,
        logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT + Back.WHITE,
    }

    def __init__(self, use_color: bool = True):
        super().__init__()
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        record.levelname = self.SHORT_LEVELS.get(record.levelname, record.levelname)

        if self.use_color:
            log_color = self.LEVEL_COLORS.get(record.levelno, "")
            log_format = (
                f"{log_color}[%(levelname)s]{Style.RESET_ALL} "
                f"[{Fore.BLUE}%(asctime)s{Style.RESET_ALL}] - %(message)s"
            )
        else:
            log_format = "[%(levelname)s] [%(asctime)s] - %(message)s"

        formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logger(is_client: bool = False, debug: bool = False, log_dir: str = "logs"):
    """
    Thiết lập và cấu hình logger
    """
    log_file = f"{log_dir}/client.log" if is_client else f"{log_dir}/server.log"

    pathlib.Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    log_level = logging.DEBUG if debug else logging.INFO

    console_formatter = CustomFormatter(use_color=True)
    file_formatter = CustomFormatter(use_color=False)

    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setFormatter(file_formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(console_formatter)

    logging.basicConfig(
        level=log_level,
        handlers=[file_handler, stream_handler],
    )

    return logging.getLogger(__name__)
