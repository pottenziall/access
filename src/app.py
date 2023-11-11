#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.2.1'
#  -------------------------------------------------------------------------
import json
import logging
import re
import select
import sys
from enum import IntEnum, Enum
from pathlib import Path
from subprocess import call, DEVNULL
from typing import Type, Dict, Union, Optional, List

from src.encrypter import Encrypter

_log = logging.getLogger(__name__)

SEARCH_VALUE_PATTERN = r".{3,}"
ADD_VALUE_PATTERN = r"^\S{3,} \S{3,} \S{3,}( \S{3,40})?$"
DEFAULT_WORK_DIR = Path().absolute()

JsonContent = Dict[str, Union[str, int]]


class GetInputTimedOut(Exception):
    def __init__(self, timeout: int) -> None:
        super().__init__(f"Timeout {timeout}s reached when waiting for input value")


class Function(Enum):
    SEARCH = "search"
    ADD = "add"
    REMOVE = "remove"
    UNDEFINED = "undefined"


class Color(IntEnum):
    DEFAULT = 7
    RED = 1
    GREEN = 2


class CLIAccessManager:
    def __init__(self, encrypter_class: Type[Encrypter], *, config_path: Path, work_path: Optional[Path] = None):
        self._encrypter_class = encrypter_class
        self._config_path = config_path
        self._config = self._read_config()
        self._handle_work_path(work_path)
        self._encrypter: Optional[Encrypter] = None

    def _handle_work_path(self, path: Optional[Path] = None) -> None:
        if path is None and not self._config.get("work_dir", False):
            path = DEFAULT_WORK_DIR
            _log.warning(f"Work path not provided. A default one is used: {path}")
        if path is not None:
            if path.is_file():
                path = path.parent
            elif path.is_dir():
                path = path
            else:
                raise ValueError(f"Wrong path passed: {path}")
            self._config.update({"work_dir": str(path)})

    @staticmethod
    def _create_config_file(path: Path) -> Path:
        with open(path, "w+", encoding="utf8"):
            return path

    def _read_config(self) -> JsonContent:
        if not self._config_path.exists():
            _log.warning(f'Config file path "{self._config_path}" does not exist. Creating empty file...')
            self._create_config_file(self._config_path)
            return {}
        with open(self._config_path, "r", encoding="utf8") as f:
            content = f.read()
            if not content:
                return {}
            config_dict = json.loads(content)
            assert isinstance(config_dict, dict)
            return config_dict

    def write_config(self) -> None:
        with open(self._config_path, "w+", encoding="utf-8") as f:
            json.dump(self._config, f)
        _log.debug(f"All config data has been written to the file: {self._config_path}")

    @staticmethod
    def show_data_safely(data: List[str], color: Color = Color.DEFAULT, timeout: int = 5) -> None:
        try:
            call(["tput", "smcup", "-T", "xterm-256color"], timeout=5)
            call(["tput", "setaf", f"{color.value}"], timeout=5)
            call(["echo", "\n\n".join(data)], timeout=5, stderr=DEVNULL)
            call(f"sleep 5", shell=True, timeout=6)
        except Exception:
            call("clear", shell=True, timeout=5)
            _log.error(f"Error when show a message")
        finally:
            call(["tput", "setaf", f"{Color.DEFAULT.value}"], timeout=5)
            call(["tput", "rmcup", "-T", "xterm-256color"], timeout=5)

    # TODO: change prompt
    def run_function_with_result_save(self, selected_function: Function = Function.UNDEFINED) -> None:
        work_path = self._config.get("work_dir", None)
        assert work_path is not None, "Missing work path for build Encrypter class instance"

        with self._encrypter_class(Path(str(work_path))) as encrypter:
            while True:
                if selected_function == Function.UNDEFINED:
                    input_value = input("Please enter 'search', 'add' or 'remove' to continue: ")
                    if input_value not in [v.value for v in Function]:
                        _log.warning("Wrong input")
                        continue
                    selected_function = Function(input_value)

                if selected_function == Function.SEARCH:
                    repeat_call = self.search_credentials(encrypter)
                elif selected_function == Function.ADD:
                    repeat_call = self.add_credentials(encrypter)
                elif selected_function == Function.REMOVE:
                    repeat_call = self.remove_credentials(encrypter)
                else:
                    raise RuntimeError("Unhandled exception")
                if not repeat_call:
                    selected_function = Function.UNDEFINED

    @staticmethod
    def _is_input_valid(value: str, pattern: str) -> bool:
        if re.match(pattern, value):
            return True
        _log.warning(f"Input phrase is not valid")
        return False

    def add_credentials(self, encrypter: Encrypter) -> bool:
        input_message = "ADD mode. Please input new credentials:"
        input_value = self.get_input_value_safely(input_message, timeout=60)
        if input_value == "exit":
            _log.info("Exit adding mode")
            return False
        if input_value and self._is_input_valid(value=input_value, pattern=ADD_VALUE_PATTERN):
            encrypter.add_content(input_value)
        return True

    def search_credentials(self, encrypter: Encrypter) -> bool:
        input_message = "SEARCH mode. Type min 3 ch to search:"
        input_value = self.get_input_value_safely(input_message).lower()
        if input_value == "exit":
            _log.info("Exit searching mode")
            return False
        if input_value and self._is_input_valid(value=input_value, pattern=SEARCH_VALUE_PATTERN):
            found = encrypter.search_in_content(input_value)
            call(["echo", f"Found {len(found)} credentials"], timeout=5)
            if found:
                self.show_data_safely([str(item) for item in found], color=Color.GREEN)
        return True

    def remove_credentials(self, encrypter: Encrypter) -> bool:
        input_message = "REMOVE mode. Please input credentials pattern to remove:"
        input_pattern = self.get_input_value_safely(input_message, timeout=60)
        if input_pattern == "exit":
            _log.info("Exit removing mode")
            return False
        if input_pattern:
            credentials_to_remove = encrypter.search_in_content(pattern=input_pattern)
            call(["echo", f"Found {len(credentials_to_remove)} credentials"], timeout=5)
            if credentials_to_remove:
                self.show_data_safely([str(c) for c in credentials_to_remove], Color.RED)
                remove_message = "Enter 'yes' to remove or any key to cancel: "
                if input(remove_message) == "yes":
                    encrypter.remove_credentials(pattern=input_pattern)
                else:
                    _log.info("Skip removing")
        return True

    # TODO: clear screen in case of exception
    @staticmethod
    def get_input_value_safely(text: str, timeout: int = 30) -> str:
        call(["echo", text], timeout=5)
        input_value, _, _ = select.select([sys.stdin], [], [], timeout)
        call("tput cuu 1 && tput ed", shell=True, timeout=5)
        if input_value:
            return sys.stdin.readline().strip()
        raise GetInputTimedOut(timeout)
