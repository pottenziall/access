import logging
import os
import re
import sys
import time

from access import Access

DISPLAY_TIMEOUT = 20
PRIVACY_FILE_PATH = "/home/vova/My/bases/dos"
APP = "gpg"
INPUT_VALUE_PATTERN = "^[A-Za-z0-9]{3,}$"

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
_logger.addHandler(logging.StreamHandler())


def _program_exist(name: str) -> bool:
    exit_code = os.system(f"which {name}")
    if exit_code == 0:
        return True
    _logger.error(f'Program "{name}" does not installed')
    return False


def _is_valid(phrase: str, pattern: str = INPUT_VALUE_PATTERN) -> bool:
    if re.match(pattern, phrase):
        return True
    _logger.info("Wrong input")
    return False


def clear_sensitives(path: str):
    _logger.info("Clear sensitives...")
    files = [file for file in os.listdir(path) if not file.endswith(".gpg")]
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
            phrase = input("\nPlease, type phrase to search: ")
            if not _is_valid(phrase):
                continue
            found = access.search(phrase)
            if found:
                for item in found:
                    _logger.info(item)
                time.sleep(5)
                os.system("clear")
            else:
                _logger.info(f'Phrase "{phrase}" not found')
        raise KeyboardInterrupt
    except Exception:
        _logger.exception(f"Program failed")
    except KeyboardInterrupt:
        sys.exit(1)
    finally:
        clear_sensitives(PRIVACY_FILE_PATH)
        os.system("clear")
        _logger.info("End program")


if __name__ == "__main__":
    main()
