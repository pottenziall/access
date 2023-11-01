#!/usr/bin/python3

#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.0.5'
#  -------------------------------------------------------------------------

import argparse
import logging
import os
import select
import sys
from pathlib import Path
from typing import Callable

from src import utils
from src.access_manager import Access

APP_DIR = Path(__file__).parent
CONFIG_FILE_PATH = APP_DIR / "config.conf"
LOG_FILE_PATH = APP_DIR / "access.log"
SEARCH_VALUE_PATTERN = r".{3,}"
ADD_VALUE_PATTERN = r"^\S{3,} \S{3,} \S{3,}( \S{3,40})?$"

_log = logging.getLogger("main")

root = logging.getLogger()
root.setLevel(logging.NOTSET)
stdout_formatter = logging.Formatter("%(message)s")
console_handler = logging.StreamHandler()
console_handler.setFormatter(stdout_formatter)
console_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter("%(asctime)s_%(levelname)s:%(name)s:%(lineno)d:%(message)s")
file_handler = logging.FileHandler(LOG_FILE_PATH, "a", encoding="utf-8")
file_handler.setFormatter(file_formatter)
file_handler.setLevel(logging.DEBUG)
root.addHandler(file_handler)
root.addHandler(console_handler)

gpg_logger = logging.getLogger("gnupg")
gpg_logger.setLevel(logging.ERROR)


class GetInputTimedOut(Exception):
    def __init__(self, timeout: int) -> None:
        super().__init__(f"Timeout {timeout}s reached when waiting for input value")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search for credentials in an encrypted archive.")
    parser.add_argument(
        "-a",
        "--add",
        help="Update the existing credential base and save it into a new archive. "
        "Input credentials, like 'gmail.com mylogin 12345678 authentication'. The last value is default.",
        action="store_true",
    )
    parser.add_argument(
        "-r",
        "--remove",
        help="Remove credentials from the base and save the base into a new archive.",
        action="store_true",
    )
    parser.add_argument(
        "-w",
        "--work_path",
        help="Path to either a directory or an encrypted archive to work with. "
        "The path will be stored in config.conf file.",
        default=None,
    )
    parser.add_argument("-d", "--debug", help="Enable debug mode", action="store_true")
    return parser.parse_args()


def _cycle_with_saving_results(func: Callable[[Access], None], access: Access) -> None:
    try:
        while True:
            func(access)
    finally:
        access.encrypt_and_export_to_new_file_if_content_updated()


def _get_input_value_safely(text: str, timeout: int = 30) -> str:
    _log.info(text)
    input_value, _, _ = select.select([sys.stdin], [], [], timeout)
    os.system("tput cuu 1 && tput ed")
    if input_value:
        return sys.stdin.readline().strip().lower()
    raise GetInputTimedOut(timeout)


def _search(access: Access) -> None:
    input_message = "Type a phrase to search (min 3 ch):"
    input_value = _get_input_value_safely(input_message)
    if input_value and utils.is_input_valid(value=input_value, pattern=SEARCH_VALUE_PATTERN):
        found = access.search_in_content(input_value)
        if found:
            utils.short_show([str(item) for item in found], color=utils.Color.GREEN)


def _add(access: Access) -> None:
    input_message = "Input new credentials:"
    input_value = _get_input_value_safely(input_message, timeout=60)
    if input_value and utils.is_input_valid(value=input_value, pattern=ADD_VALUE_PATTERN):
        access.add_content(input_value)


def _remove(access: Access) -> None:
    input_message = "Please input credentials pattern to remove:"
    input_pattern = _get_input_value_safely(input_message, timeout=60)
    if input_pattern:
        credentials_to_remove = access.search_in_content(pattern=input_pattern)
        if credentials_to_remove:
            utils.short_show([str(c) for c in credentials_to_remove], utils.Color.RED)
            remove_message = "Enter 'yes' to remove or any key to cancel: "
            if input(remove_message) == "yes":
                access.remove_credentials(pattern=input_pattern)
            else:
                _log.info("Skip removing")


def _set_debug_mode() -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    _log.info("Debug mode enabled")


def main() -> None:
    try:
        input_args = _parse_args()
        if input_args.debug:
            _set_debug_mode()

        if input_args.work_path is not None:
            assert Path(input_args.work_path).exists(), f"Path does not exist: {input_args.work_path}"
            utils.add_to_config(path=CONFIG_FILE_PATH, data={"work_path": input_args.work_path})

        config = utils.read_config(path=CONFIG_FILE_PATH)
        assert config.get("work_path", False), "Provide '--work_path'. It will be stored in a config file"
        access = Access(Path(str(config["work_path"])))

        if input_args.add:
            _cycle_with_saving_results(_add, access)
        elif input_args.remove:
            _cycle_with_saving_results(_remove, access)
        else:
            if access.archive_path is None:
                _log.warning("No encrypted archive found to search in")
            else:
                _cycle_with_saving_results(_search, access)

    except GetInputTimedOut as e:
        _log.info(f"Did not get input value: {e}")
    except Exception:
        _log.exception("Program failed:")
    finally:
        _log.info("Close application")
        _log.debug(f"{150*'='}")
        sys.exit(0)


if __name__ == "__main__":
    main()
