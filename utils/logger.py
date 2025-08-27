import datetime
import pathlib
from utils.config import LoggingConfig


class Logger:
    def __init__(self):
        self.__log_file = LoggingConfig.LOG_FILE
        self.__format = "[{level}] [{timestamp}] - {message}\n"

    def __get_timestamp(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def __write_log(self, level, message):
        if not pathlib.Path(self.__log_file).parent.exists():
            pathlib.Path(self.__log_file).parent.mkdir(parents=True)
        try:
            with open(self.__log_file, "a") as f:
                f.write(
                    self.__format.format(
                        level=level,
                        timestamp=self.__get_timestamp(),
                        message=message,
                    )
                )
            print(
                self.__format.format(
                    level=level,
                    timestamp=self.__get_timestamp(),
                    message=message,
                ),
                end="",
            )
        except Exception as e:
            print(f"[ERROR] [{self.__get_timestamp()}] - Failed to write log: {e}")

    def info(self, message):
        self.__write_log("INFO", message)

    def error(self, message):
        self.__write_log("ERROR", message)

    def debug(self, message):
        self.__write_log("DEBUG", message)


logger = Logger()
