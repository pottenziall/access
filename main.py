import logging
import os
import sys
import re
import time

from access import Access

DISPLAY_TIMEOUT = 20
PATH = "/home/vova/My/bases/dos"

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
_logger.addHandler(logging.StreamHandler())

# TODO check gpg program exist


def _is_valid(phrase: str) -> bool:
    pattern = "^[A-Za-z0-9]{3,}$"
    if re.search(pattern, phrase):
        return True
    _logger.info("Wrong input")
    return False


def clear_sensitives(path: str):
    _logger.info("Clear sensitives...")
    files = [file for file in os.listdir(path) if not file.endswith(".gpg")]
    if files:
        for name in files:
            os.remove(os.path.join(PATH, name))


try:
    access = Access(PATH)
    while True:
        phrase = input("\nPlease, input phrase to search: ")
        if not _is_valid(phrase):
            continue
        found = access.search(phrase)
        if found:
            for item in found:
                _logger.info(item)
            time.sleep(5)
            os.system("clear")
        else:
            _logger.info(f"Phrase '{phrase}' not found")
    raise KeyboardInterrupt
except Exception as e:
    _logger.info(f"Program failed with error: {e}")
except KeyboardInterrupt:
    sys.exit(1)
finally:
    clear_sensitives(PATH)
    os.system("clear")
    _logger.info("End program")
