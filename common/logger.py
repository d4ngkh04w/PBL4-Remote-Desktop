import logging
import sys
import pathlib
import datetime


def setup_logger(is_client: bool = False, debug: bool = False, log_dir: str = "logs"):
    log_file = (
        f"{log_dir}/client_{datetime.datetime.now().strftime('%Y-%m-%d')}.log"
        if is_client
        else f"{log_dir}/server_{datetime.datetime.now().strftime('%Y-%m-%d')}.log"
    )

    pathlib.Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    log_format = "[%(levelname)s] [%(asctime)s] - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    log_level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_file, mode="a", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    return logging.getLogger(__name__)
