import datetime
import pathlib
import sys

from common.config import LoggingConfig


class Logger:
    def __init__(self):

        if len(sys.argv) > 1 and sys.argv[1] == "--client":
            self.__log_file = LoggingConfig.LOG_CLIENT
        else:
            self.__log_file = LoggingConfig.LOG_SERVER

        self.__format = "[{level}] [{timestamp}] - {message}\n"

    def __get_timestamp(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def __write_log(self, level, message, log_to_file=True):
        if log_to_file:
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
            except Exception as e:
                print(f"[ERR] [{self.__get_timestamp()}] - Failed to write log: {e}")

        print(
            self.__format.format(
                level=level,
                timestamp=self.__get_timestamp(),
                message=message,
            ),
            end="",
        )

    def info(self, message, log_to_file=True):
        self.__write_log("INF", message, log_to_file)

    def warning(self, message, log_to_file=True):
        self.__write_log("WARN", message, log_to_file)

    def error(self, message, log_to_file=True):
        self.__write_log("ERR", message, log_to_file)

    def debug(self, message, log_to_file=True):
        self.__write_log("DBG", message, log_to_file)


logger = Logger()
