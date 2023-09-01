#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.0'
#  -------------------------------------------------------------------------

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_log = logging.getLogger(__name__)


def validate_input(value: str, pattern: str) -> bool:
    if re.match(pattern, value):
        return True
    _log.info(f'Phrase "{value}" is not valid')
    return False


def print_data(data: List[str]) -> None:
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


def clear_sensitives(path: Path, exclude: str) -> None:
    _log.info("Clear sensitives...")
    for directory, _, files in os.walk(path):
        files_to_remove = [file for file in files if not file.endswith(f".{exclude}")]
        if files_to_remove:
            for file in files_to_remove:
                os.remove(os.path.join(directory, file))
            _log.debug(f"{len(files_to_remove)} files have been removed from {path}")


def read_config(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        _log.warning(f"Config file does not exist or is not a file: {path}")
        return None
    with open(path, encoding="utf8") as f:
        return json.loads(f.read())


def add_to_config(path: Path, data: Dict[str, Any]) -> None:
    with open(path, "w+", encoding="utf-8") as f:
        content = json.load(f) if f.read() else {}
        content.update(data)
        json.dump(content, f)
