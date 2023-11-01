#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.0.5'
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
    try:
        os.system("tput smcup")
        os.system(f"tput setaf {color.value}")
        lines = "\n\n".join(data)
        os.system(f"echo $'{lines}' && sleep {timeout}")
    except Exception as e:
        _log.error(f"Error when show messages: {e}")
    finally:
        os.system(f"tput setaf {Color.DEFAULT.value}")
        os.system("tput rmcup")


def read_config(path: Path) -> JsonContent:
    if not path.is_file():
        _log.warning(f"Config path does not exist or is not a file: {path}")
        return {}
    with open(path, encoding="utf8") as f:
        content = f.read()
        if not content:
            return {}
        config_dict = json.loads(content)
        assert isinstance(config_dict, dict)
        return config_dict


def add_to_config(path: Path, data: Dict[str, str]) -> None:
    content = read_config(path)
    with open(path, "w+", encoding="utf-8") as f:
        content.update(data)
        json.dump(content, f)
    _log.debug(f"Added data to the config file: {data}")
