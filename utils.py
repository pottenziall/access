import logging
import os
import re
import time
from typing import List

_log = logging.getLogger(__name__)


def program_exists(name: str) -> bool:
    program_exist_command = f"which {name}"
    exit_code = os.system(program_exist_command)
    if exit_code == 0:
        return True
    return False


def validate_input(value: str, pattern: str) -> bool:
    if re.match(pattern, value):
        return True
    _log.info(f'Phrase "{value}" is not valid')
    return False


def print_and_clear(data: List[str], timeout: int = 5) -> None:
    if not data:
        return
    _log.info(f'{40 * ">"}')
    for item in data:
        _log.info(item)
    _log.info(f'{40 * "<"}')
    time.sleep(timeout)
    os.system("clear && clear")


def clear_sensitives(path: str, exclude: str) -> None:
    _log.info("Clear sensitives...")
    for directory, _, files in os.walk(path):
        files_to_remove = [file for file in files if not file.endswith(f".{exclude}")]
        if files_to_remove:
            for file in files_to_remove:
                os.remove(os.path.join(directory, file))
            _log.debug(f'"{len(files_to_remove)}" files removed')


def get_file_content(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding='utf8') as f:
            return f.read()
    except Exception:
        _log.exception(f'Error when reading "{file_path}" file')
        return ""


def remove_file(file_path: str, tries: int = 5) -> None:
    if not os.path.exists(file_path):
        raise AssertionError(f"Try to remove non-existing file: {file_path}")
    for _ in range(tries):
        os.remove(file_path)
        if not os.path.exists(file_path):
            return
    raise AssertionError(f"Not possible to remove file: {file_path}")
