#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.0.4'
#  -------------------------------------------------------------------------

import json
import logging
import os
import re
from enum import IntEnum
from pathlib import Path
from typing import Dict, List, Union

_log = logging.getLogger(__name__)

JsonContent = Dict[str, Union[str, int]]


class Color(IntEnum):
    DEFAULT = 7
    RED = 1
    GREEN = 2


def is_input_valid(value: str, pattern: str) -> bool:
    if re.match(pattern, value):
        return True
    _log.warning(f'Input phrase is not valid')
    return False


def short_show(data: List[str], color: Color = Color.DEFAULT, timeout: int = 5) -> None:
    os.system("tput smcup")
    os.system(f"tput setaf {color.value}")
    lines = "\n\n".join(data)
    os.system(f"echo $'{lines}' | timeout --foreground {timeout} less -e")
    restore_screen()


def restore_screen() -> None:
    os.system(f"tput setaf {Color.DEFAULT.value}")
    os.system("tput rmcup")


def read_config(path: Path) -> JsonContent:
    if not path.is_file():
        _log.warning(f"Config path does not exist or is not a file: {path}")
        return {}
    with open(path, encoding="utf8") as f:
        content = json.loads(f.read())
        assert isinstance(content, dict)
        return content


def add_to_config(path: Path, data: Dict[str, str], assert_ok: bool = False) -> None:
    with open(path, "w+", encoding="utf-8") as f:
        content = json.load(f) if f.read() else {}
        if assert_ok:
            data = {k: v for k, v in data.items() if content.get(k, None) != v}
        content.update(data)
        json.dump(content, f)
    _log.debug(f"Added data to the config file: {data}")
