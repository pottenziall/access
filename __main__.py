#!/usr/bin/python3

#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.2.0'
#  -------------------------------------------------------------------------

import argparse
import logging
import os
import select
import sys
from enum import Enum
from pathlib import Path

from src import utils
from src.encrypter import Encrypter
from src.logging_utils import setup_logging

APP_DIR = Path(__file__).parent
CONFIG_FILE_PATH = APP_DIR / "config.conf"
LOG_FILE_PATH = APP_DIR / "access.log"
SEARCH_VALUE_PATTERN = r".{3,}"
ADD_VALUE_PATTERN = r"^\S{3,} \S{3,} \S{3,}( \S{3,40})?$"
# TODO: use subprocess instead of os.system
# TODO: convert main to App class. Put there functions from utils

_log = logging.getLogger("main")

setup_logging(LOG_FILE_PATH)


class GetInputTimedOut(Exception):
    def __init__(self, timeout: int) -> None:
        super().__init__(f"Timeout {timeout}s reached when waiting for input value")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage encrypted file credentials")
    parser.add_argument(
        "-s",
        "--search",
        help="Search credentials for a pattern",
        action="store_true",
    )
    parser.add_argument(
        "-a",
        "--add",
        help="Update the existing credential base and save it into a new file. "
        "Input credentials, like 'gmail.com mylogin 12345678 authentication'. The last value is default.",
        action="store_true",
    )
    parser.add_argument(
        "-r",
        "--remove",
        help="Remove credentials from the base and save the base into a new file.",
        action="store_true",
    )
    parser.add_argument(
        "-w",
        "--work_path",
        help="Path to either a directory or an encrypted file or a text file with prepared credentials. "
        "The dir path (or the file's parent dir if work_path is a file path) will be stored in config.conf file. "
        "Default value is __file__ parent dir",
        default=Path(),
    )
    parser.add_argument("-d", "--debug", help="Print more logs", action="store_true")
    return parser.parse_args()


class Function(Enum):
    SEARCH = "search"
    ADD = "add"
    REMOVE = "remove"
    UNDEFINED = "undefined"


def create_config_if_not_exist() -> None:
    if not CONFIG_FILE_PATH.exists():
        with open(CONFIG_FILE_PATH, "w+", encoding="utf8"):
            pass


def get_input_value_safely(text: str, timeout: int = 30) -> str:
    os.system(f"echo {text}")
    input_value, _, _ = select.select([sys.stdin], [], [], timeout)
    os.system("tput cuu 1 && tput ed")
    if input_value:
        return sys.stdin.readline().strip()
    raise GetInputTimedOut(timeout)


def run_function_with_result_save(encrypter: Encrypter, selected_function: Function = Function.UNDEFINED) -> None:
    # TODO: change prompt
    try:
        while True:
            if selected_function == Function.UNDEFINED:
                input_value = input("Please enter 'search', 'add' or 'remove' to continue: ")
                if input_value not in [v.value for v in Function]:
                    os.system("echo Wrong input value")
                    continue
                selected_function = Function(input_value)

            if selected_function == Function.SEARCH:
                repeat_call = search(encrypter)
            elif selected_function == Function.ADD:
                repeat_call = add(encrypter)
            elif selected_function == Function.REMOVE:
                repeat_call = remove(encrypter)
            else:
                raise RuntimeError("Unhandled exception")
            if not repeat_call:
                selected_function = Function.UNDEFINED
    except Exception as e:
        _log.error(f"Program failed: {e}")
        raise RuntimeError from e
    finally:
        encrypter.encrypt_into_new_file_if_content_updated()


def search(encrypter: Encrypter) -> bool:
    input_message = "SEARCH mode. Type min 3 ch to search:"
    input_value = get_input_value_safely(input_message).lower()
    if input_value == "exit":
        _log.info("Exit searching mode")
        return False
    if input_value and utils.is_input_valid(value=input_value, pattern=SEARCH_VALUE_PATTERN):
        found = encrypter.search_in_content(input_value)
        if found:
            utils.short_show([str(item) for item in found], color=utils.Color.GREEN)
    return True


def add(encrypter: Encrypter) -> bool:
    input_message = "ADD mode. Please input new credentials:"
    input_value = get_input_value_safely(input_message, timeout=60)
    if input_value == "exit":
        _log.info("Exit adding mode")
        return False
    if input_value and utils.is_input_valid(value=input_value, pattern=ADD_VALUE_PATTERN):
        encrypter.add_content(input_value)
    return True


def remove(encrypter: Encrypter) -> bool:
    input_message = "REMOVE mode. Please input credentials pattern to remove:"
    input_pattern = get_input_value_safely(input_message, timeout=60)
    if input_pattern == "exit":
        _log.info("Exit removing mode")
        return False
    if input_pattern:
        credentials_to_remove = encrypter.search_in_content(pattern=input_pattern)
        if credentials_to_remove:
            utils.short_show([str(c) for c in credentials_to_remove], utils.Color.RED)
            remove_message = "Enter 'yes' to remove or any key to cancel: "
            if input(remove_message) == "yes":
                encrypter.remove_credentials(pattern=input_pattern)
            else:
                _log.info("Skip removing")
    return True


def set_debug_mode() -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    _log.info("Debug mode enabled")


def get_work_path(path: Path) -> Path:
    if path.is_file():
        utils.update_config(path=CONFIG_FILE_PATH, data={"work_dir": str(path.parent)})
        return path
    elif path.is_dir():
        if path != Path():
            utils.update_config(path=CONFIG_FILE_PATH, data={"work_dir": str(path)})
    else:
        _log.error(f"Wrong path passed: {path}")
        sys.exit(1)
    config = utils.read_config(path=CONFIG_FILE_PATH)
    if not config.get("work_dir", False):
        _log.warning(f"Please provide '--work_path'. It will be stored in: {CONFIG_FILE_PATH}")
        sys.exit(0)
    return Path(str(config["work_dir"]))


def main() -> None:
    try:
        input_args = parse_args()
        if input_args.debug:
            set_debug_mode()
        create_config_if_not_exist()
        work_path = get_work_path(Path(input_args.work_path))
        encrypter = Encrypter(work_path)

        if input_args.add:
            run_function_with_result_save(encrypter, Function.ADD)
        elif input_args.remove:
            run_function_with_result_save(encrypter, Function.REMOVE)
        elif input_args.search:
            run_function_with_result_save(encrypter, Function.SEARCH)
        else:
            run_function_with_result_save(encrypter, Function.SEARCH)

    except GetInputTimedOut as e:
        _log.info(f"Did not get input value: {e}")
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception:
        _log.exception("Program failed:")
        sys.exit(1)
    finally:
        _log.info("Close application")
        _log.debug(f"{150*'='}")


if __name__ == "__main__":
    main()
