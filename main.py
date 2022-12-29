import logging
import os
import re
import select
import sys
import time
from typing import List

from access import Access, PRIVACY_ARCHIVE_EXTENSION

DISPLAY_TIMEOUT = 20
PRIVACY_FILE_PATH = "/home/vova/My/bases/dos"
APP = "gpg"
INPUT_VALUE_PATTERN = "^[A-Za-z0-9]{3,}$"

_log = logging.getLogger(__name__)
_log.setLevel(logging.DEBUG)
_log.addHandler(logging.StreamHandler())


def _program_exist(name: str) -> bool:
    exit_code = os.system(f"which {name}")
    if exit_code == 0:
        return True
    _log.error(f'Program "{name}" does not installed')
    return False


def _is_valid(phrase: str, pattern: str = INPUT_VALUE_PATTERN) -> bool:
    if re.match(pattern, phrase):
        return True
    _log.info("Wrong input")
    return False


def print_and_clear(data: List[str], timeout: int = 5) -> None:
    for item in data:
        _log.info(item)
    time.sleep(timeout)
    os.system("clear")


def clear_sensitives(path: str):
    _log.info("Clear sensitives...")
    files = [file for file in os.listdir(path) if not file.endswith(f".{PRIVACY_ARCHIVE_EXTENSION}")]
    if files:
        for name in files:
            os.remove(os.path.join(PRIVACY_FILE_PATH, name))


def main():
    if not _program_exist(APP):
        return
    try:
        access = Access(PRIVACY_FILE_PATH)
        access.search_and_decrypt_file()
        while True:
            _log.info("Please, type phrase to search: ")
            inp, o, e = select.select([sys.stdin], [], [], 30)
            if not inp:
                break
            phrase = sys.stdin.readline().strip()
            if _is_valid(phrase):
                found = access.search(phrase)
                if found:
                    print_and_clear(found)
                _log.info(f'Phrase "{phrase}" not found')
            continue
        raise KeyboardInterrupt
    except Exception:
        _log.exception(f"Program failed")
    except KeyboardInterrupt:
        sys.exit(1)
    finally:
        clear_sensitives(PRIVACY_FILE_PATH)
        os.system("clear")
        _log.info("End program")


if __name__ == "__main__":
    main()
