#!/usr/bin/python3

#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.0.2'
#  -------------------------------------------------------------------------

import argparse
import logging
import os
import select
import sys
import time
from pathlib import Path

from src import utils
from src.access_manager import Access

APP_DIR = Path(f"{__file__}").parent
CONFIG_FILE_PATH = APP_DIR / "config.conf"
SEARCH_VALUE_PATTERN = r"^[A-Za-z0-9.]{3,}$"
ADDING_VALUE_PATTERN = r"^\S{3,} \S{3,} \S{3,}$"

_log = logging.getLogger("main")
logging.basicConfig(format="%(message)s", level=logging.INFO, handlers=[logging.StreamHandler()])
# TODO: create a function: run_in_safe_cycle


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search for credentials in an encrypted archive")
    parser.add_argument(
        "-a",
        "--add",
        help="Update the existing credential base and save it into a new archive",
        action="store_true",
    )
    parser.add_argument(
        "-r",
        "--remove",
        help="Remove credentials from the base and save the base into a new archive",
        action="store_true",
    )
    parser.add_argument(
        "-w",
        "--work_path",
        help="Path to either a directory or an encrypted archive to work with. "
             "The path will be stored in config.conf file",
        default=None,
    )
    parser.add_argument("-d", "--debug", help="Enable debug mode", action="store_true")
    return parser.parse_args()


def _get_input_value(timeout: int = 30) -> str:
    while True:
        # TODO: improve the method
        inp, o, e = select.select([sys.stdin], [], [], timeout)
        if not inp:
            break
        return sys.stdin.readline().strip().lower()
    _log.info("Timeout reached, closing the application...")
    raise KeyboardInterrupt


def _search(access: Access) -> None:
    while True:
        _log.info("Type a phrase to search (min 3 ch):")
        value = _get_input_value()
        if utils.is_input_valid(value=value, pattern=SEARCH_VALUE_PATTERN):
            found = access.search_in_content(value)
            if found:
                utils.short_show([str(item) for item in found])
                time.sleep(5)


def _add(access: Access) -> None:
    _log.info(f"Please, enter credentials, like 'gmail.com mylogin 12345678 authentication'. The last is default")
    try:
        while True:
            _log.info(f"New credentials:")
            os.system("tput sc")
            value = _get_input_value(timeout=60)
            os.system("tput rc && tput ed")
            if utils.is_input_valid(value=value, pattern=ADDING_VALUE_PATTERN):
                access.add_content(value)
            else:
                _log.info(f'Input phrase is not valid')
    except KeyboardInterrupt:
        access.encrypt_and_export_to_new_file_if_content_updated()
        raise


def _remove(access: Access) -> None:
    lines_to_remove = 0
    try:
        while True:
            _log.info(f"Please input credentials pattern to remove")
            pattern = _get_input_value(timeout=60)
            if not pattern:
                continue
            found = access.search_in_content(pattern=pattern)
            if not found:
                continue
            found_elements = [f"\n\t{str(c)}\n" for c in found]
            _log.info(f"Found {len(found)} credentials for the pattern '{pattern}': ")
            os.system("tput setaf 1")
            _log.info(f"{''.join(found_elements)}")
            lines_to_remove = len(found)
            os.system("tput setaf 7")
            # TODO: use timeout
            is_accepted = input("Enter 'yes' to remove or any key to cancel: ")

            if is_accepted == "yes":
                access.remove_credentials(pattern=pattern)
            else:
                _log.info("Skip removing")
            os.system(f"echo -en '\033[{2 * len(found) + 4}A' && tput ed")
    finally:
        if lines_to_remove:
            os.system(f"echo -en '\033[{2 * lines_to_remove + 4}A' && tput ed")
        access.encrypt_and_export_to_new_file_if_content_updated()


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
            if not Path(input_args.work_path).exists():
                raise AssertionError(f"Path does not exist: {input_args.work_path}")
            utils.add_to_config(path=CONFIG_FILE_PATH, data={"work_path": input_args.work_path}, assert_ok=True)
        config_content = utils.read_config(path=CONFIG_FILE_PATH)
        access = Access(Path(str(config_content["work_path"])))

        if input_args.add:
            _add(access)
        elif input_args.remove:
            _remove(access)
        else:
            if access.archive_path is None:
                _log.warning("No encrypted archive found to search in")
            else:
                _search(access)
    except Exception:
        _log.exception("Program failed:")
    except KeyboardInterrupt:
        sys.exit(0)
    finally:
        os.system("tput setaf 7")
        _log.info("Application closed")


if __name__ == "__main__":
    main()
