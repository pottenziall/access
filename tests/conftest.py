#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.2.3'
#  -------------------------------------------------------------------------

from pathlib import Path
from typing import Any, Tuple

import pytest

from src.encrypter import FILE_ITEMS_SEPARATOR


@pytest.fixture(scope="session")
def tmp_dir(tmp_path_factory: Any) -> Path:
    tmp_dir: Path = tmp_path_factory.mktemp("access")
    return tmp_dir


@pytest.fixture(scope="session")
def txt_file(request: Any, tmp_dir: Path) -> Tuple[Path, str]:
    txt_file_path = tmp_dir / "txt_with_content_example"
    with open(txt_file_path, "w+", encoding="utf8") as f:
        f.write(request.param)
    return txt_file_path, request.param.split(FILE_ITEMS_SEPARATOR)
