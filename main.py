import argparse
import logging
import select
import sys
from typing import Dict

import utils
from access import Access, PRIVACY_ARCHIVE_EXTENSION

# TODO: error when wrong password
DISPLAY_TIMEOUT = 20
PRIVACY_DIR_PATH = "/home/vova/My/bases/dos/tes_dos"
APP = "gpg"
SEARCH_VALUE_PATTERN = r"^[A-Za-z0-9]{3,}$"
ADDING_VALUE_PATTERN = r"^\S{3,} \S{3,} \S{3,}$"

_log = logging.getLogger(__name__)

logging.basicConfig(
    format="%(message)s",
    level=logging.DEBUG,
    handlers=[logging.StreamHandler()],
)

parser = argparse.ArgumentParser(description='Access')
parser.add_argument("-a", "--add", help="Add credentials", action="store_true")
app_args = vars(parser.parse_args())


def _get_input_value(timeout: int = 30) -> str:
    while True:
        inp, o, e = select.select([sys.stdin], [], [], timeout)
        if not inp:
            break
        return sys.stdin.readline().strip()
    _log.info("Timeout reached, closing the application...")
    raise KeyboardInterrupt


def main(args: Dict[str, str]):
    if not utils.program_exists(APP):
        _log.error(f'Program "{APP}" not found. Please, install')
        return
    try:
        access = Access(PRIVACY_DIR_PATH)
        access.search_and_decrypt_latest_file()
        if args.get("add", False):
            i = 5
            while i > 0:
                _log.info("Please, enter credentials (like gmail.com mylogin 12345678")
                value = _get_input_value(timeout=60)
                if utils.validate_input(value=value, pattern=ADDING_VALUE_PATTERN):
                    access.add_content(value)
                i -= 1
            access.pack_content_to_gpg()
        else:
            while True:
                _log.info("Please, type a phrase to search: ")
                value = _get_input_value()
                if utils.validate_input(value=value, pattern=SEARCH_VALUE_PATTERN):
                    found = access.search(value)
                    utils.print_and_clear(found)
    except Exception:
        _log.exception(f"Program failed")
    except KeyboardInterrupt:
        sys.exit(1)
    finally:
        # os.system("clear")
        utils.clear_sensitives(PRIVACY_DIR_PATH, exclude=PRIVACY_ARCHIVE_EXTENSION)


if __name__ == "__main__":
    # TODO: try gnupg below

    # gpg = gnupg.GPG(gnupghome="/home/vova/My/bases/dos/tes_dos/")
    # gpg.encrypt("12345", "12", symmetric=True,  output="/home/vova/My/bases/dos/tes_dos/new.gpg")
    # gpg.encrypt("some data", "me", symmetric=True, passphrase="12345678", output="/home/vova/My/bases/dos/tes_dos/new.gpg")

    # bf = io.BytesIO(b'123')
    # os.system(f"gpg --symmetric --output {'/home/vova/My/bases/dos/tes_dos/dos_06012023.gpg'} --no-symkey-cache {bf}")
    try:
        main(app_args)
    finally:
        utils.clear_sensitives(PRIVACY_DIR_PATH, exclude=PRIVACY_ARCHIVE_EXTENSION)
        _log.info("End program")
