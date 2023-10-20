#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.0.2'
#  -------------------------------------------------------------------------

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Union

_log = logging.getLogger(__name__)

JsonContent = Dict[str, Union[str, int]]


def is_input_valid(value: str, pattern: str) -> bool:
    if re.match(pattern, value):
        return True
    return False


def pretty_print(data: List[str]) -> None:
    if not data:
        data = ["no data"]
    os.system(f"tput setaf 2")
    for item in data[:-1]:
        _log.info(item + "\n")
    _log.info(data[-1])
    os.system("tput setaf 7")
    c = 0
    for i in data:
        c += len(i.split("\n"))
    c = c + 2
    time.sleep(5)
    os.system(f"tput cuu {c} && tput ed")


def read_config(path: Path) -> Optional[JsonContent]:
    if not path.is_file():
        _log.warning(f"Config file does not exist or is not a file: {path}")
        return None
    with open(path, encoding="utf8") as f:
        content = json.loads(f.read())
        assert isinstance(content, dict)
        return content


def add_to_config(path: Path, data: Dict[str, Union[str, int]]) -> None:
    with open(path, "w+", encoding="utf-8") as f:
        content = json.load(f) if f.read() else {}
        content.update(data)
        json.dump(content, f)
    _log.debug(f"Added data to config file: {data}")
