import argparse
import logging
import os
import select
import sys
from pathlib import Path

import utils
from access import Access

# TODO: error when wrong password
DISPLAY_TIMEOUT = 20
APP_DIR = Path(f"{__file__}").parent
CONFIG_FILE_PATH = APP_DIR / "config"
APP = "gpg"
SEARCH_VALUE_PATTERN = r"^[A-Za-z0-9]{3,}$"
ADDING_VALUE_PATTERN = r"^\S{3,} \S{3,} \S{3,}$"

_log = logging.getLogger("main")

logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search for credentials in an encrypted archive"
    )
    parser.add_argument(
        "--add",
        help="Add credentials and save it in a new archive",
        action="store_true",
    )
    parser.add_argument(
        "-w",
        "--work_dir",
        help="Work directory, otherwise - default path will be used. The path will be stored in config file",
    )
    parser.add_argument("-d", "--debug", help="Enable debug mode", action="store_true")
    return parser.parse_args()


def _get_input_value(timeout: int = 30) -> str:
    while True:
        inp, o, e = select.select([sys.stdin], [], [], timeout)
        if not inp:
            break
        return sys.stdin.readline().strip().lower()
    _log.info("Timeout reached, closing the application...")
    raise KeyboardInterrupt


def _set_loggers_debug_level() -> None:
    loggers = ["main", "utils", "access"]
    for name in loggers:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
    # _log.setLevel(logging.DEBUG)


def _search(access: Access) -> None:
    # access = Access(DEFAULT_PRIVACY_DIR_PATH)
    while True:
        # os.system("tput sc")
        _log.info("Type a phrase to search (min 3 ch):")
        value = _get_input_value()
        if utils.validate_input(value=value, pattern=SEARCH_VALUE_PATTERN):
            found = access.search_in_content(value)
            utils.print_data(found)


def _add(access: Access) -> None:
    _log.info(f"Please, enter credentials, like gmail.com mylogin 12345678)")
    try:
        while True:
            _log.info(f"New credentials:")
            # TODO: Is case valid when cut input data after 30s?
            value = _get_input_value(timeout=60)
            if utils.validate_input(value=value, pattern=ADDING_VALUE_PATTERN):
                access.add_content(value)
    except KeyboardInterrupt:
        access.encrypt_and_export_to_new_file_if_content_updated()
        raise


def main(args: argparse.Namespace) -> None:
    enabled_args = [a for a in vars(args) if vars(args)[a]]
    if enabled_args:
        _log.info(f"Run app with args: {enabled_args}")
    try:
        if args.debug:
            _set_loggers_debug_level()
            _log.info("Debug mode enabled")
        if args.work_dir:
            work_dir = Path(args.work_dir)
            utils.add_to_config(path=CONFIG_FILE_PATH, data={"work_dir": args.work_dir})
        else:
            config_content = utils.read_config(path=CONFIG_FILE_PATH)
            if config_content and "work_dir" in config_content:
                work_dir = Path(config_content["work_dir"])
            else:
                work_dir = APP_DIR
                utils.add_to_config(
                    path=CONFIG_FILE_PATH, data={"work_dir": str(work_dir)}
                )
        access = Access(work_dir)
        if args.add:
            _add(access)
        else:
            _search(access)
    except Exception:
        if _log.level == 0:
            _log.error("Program failed")
        else:
            _log.exception("Program failed:")
    except KeyboardInterrupt:
        os.system("tput rc && tput rc && tput ed")
        sys.exit(1)
    finally:
        # utils.clear_sensitives(DEFAULT_PRIVACY_DIR_PATH, exclude=APP)
        _log.info("Application closed")


if __name__ == "__main__":
    app_args = _parse_args()
    main(app_args)
