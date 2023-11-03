#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.1.0'
#  -------------------------------------------------------------------------

import logging
from pathlib import Path


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    def __init__(self, fmt: str) -> None:
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            # logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset,
        }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setup_logging(logfile: Path) -> None:
    root = logging.getLogger()
    root.setLevel(logging.NOTSET)

    console_formatter = CustomFormatter("%(message)s")
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    file_formatter = logging.Formatter("%(asctime)s_%(levelname)s:%(name)s:%(lineno)d:%(message)s")
    file_handler = logging.FileHandler(logfile, "a", encoding="utf-8")
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)

    root.addHandler(file_handler)
    root.addHandler(console_handler)
    # disable debug messages from gnupg module
    gpg_logger = logging.getLogger("gnupg")
    gpg_logger.setLevel(logging.ERROR)
