#!/usr/bin/python3

#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.2.1'
#  -------------------------------------------------------------------------

import argparse
import logging
import sys
from pathlib import Path

from src.app import CLIAccessManager, Function, GetInputTimedOut
from src.encrypter import Encrypter
from src.logging_utils import setup_logging

APP_DIR = Path(__file__).parent
CONFIG_FILE_PATH = APP_DIR / "config.conf"
LOG_FILE_PATH = APP_DIR / "access.log"
SEARCH_VALUE_PATTERN = r".{3,}"
ADD_VALUE_PATTERN = r"^\S{3,} \S{3,} \S{3,}( \S{3,40})?$"

_log = logging.getLogger("main")

setup_logging(LOG_FILE_PATH)


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
             "The dir path (or the file's parent dir if work_path is a file path) will be stored in config.conf file. ",
        type=Path,
        default=None,
    )
    parser.add_argument("-d", "--debug", help="Print more logs", action="store_true")
    return parser.parse_args()


def set_debug_mode() -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    _log.info("Debug mode enabled")


def main() -> None:
    input_args = parse_args()
    access = CLIAccessManager(Encrypter, config_path=CONFIG_FILE_PATH, work_path=input_args.work_path)
    try:
        if input_args.debug:
            set_debug_mode()
        if input_args.add:
            access.run_function_with_result_save(Function.ADD)
        elif input_args.remove:
            access.run_function_with_result_save(Function.REMOVE)
        else:
            access.run_function_with_result_save(Function.SEARCH)

    except GetInputTimedOut as e:
        _log.info(f"Did not get input value: {e}")
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception:
        _log.exception("Program failed:")
        sys.exit(1)
    finally:
        access.write_config()
        _log.debug(f"\n{150 * '='}")


if __name__ == "__main__":
    main()
