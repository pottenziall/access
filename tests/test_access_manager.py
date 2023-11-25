#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.2.3'
#  -------------------------------------------------------------------------

import logging
from pathlib import Path
from typing import Any, Dict, Tuple, List

import pytest

from src.app import CLIAccessManager, DEFAULT_WORK_DIR
from src.encrypter import Encrypter

_log = logging.getLogger(__name__)

TestItems = Tuple[Path, List[str]]

CONFIG_FILE_CONTENT = f'{{"work_dir": "{str(DEFAULT_WORK_DIR)}"}}'


@pytest.fixture(scope="function")
def config_file(request: Any, txt_file: TestItems) -> Path:
    txt_path, _ = txt_file
    with open(txt_path, "r", encoding="utf8") as f:
        f.write(request.param)
    return txt_path


class TestCreateCLIAccessManager:
    @pytest.mark.parametrize(
        "txt_file, work_path, result",
        [
            ("", None, {"work_dir": str(DEFAULT_WORK_DIR)}),
            (CONFIG_FILE_CONTENT, None, {"work_dir": str(DEFAULT_WORK_DIR)}),
            ("", Path(__file__), {"work_dir": str(Path(__file__).parent)}),
            (CONFIG_FILE_CONTENT, Path(__file__), {"work_dir": str(Path(__file__).parent)}),
            (CONFIG_FILE_CONTENT, Path(__file__).parent, {"work_dir": str(Path(__file__).parent)}),
        ],
        indirect=["txt_file"],
    )
    def test_should_create_instance_from_params(self, txt_file: TestItems, result: Dict[str, str], work_path: Path) -> None:
        txt_path, _ = txt_file
        sut = CLIAccessManager(Encrypter, config_path=txt_path, work_path=work_path)
        assert sut._encrypter_class == Encrypter
        assert sut._config_path == txt_path
        assert sut._config == result
        assert sut._encrypter is None

    def test_should_create_instance_from_non_existing_config_path(self, tmp_path: Path) -> None:
        dummy_path = tmp_path / "dummy"
        sut = CLIAccessManager(Encrypter, config_path=dummy_path)
        assert sut._encrypter_class == Encrypter
        assert sut._config_path == dummy_path
        assert sut._config == {"work_dir": str(DEFAULT_WORK_DIR)}
        assert sut._encrypter is None

    def test_should_write_config_content_to_file(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config"
        sut = CLIAccessManager(Encrypter, config_path=config_path)
        assert sut._config == {"work_dir": str(DEFAULT_WORK_DIR)}
        sut._config["key"] = "value"
        sut.write_config()
        with open(config_path, "r", encoding="utf-8") as f:
            assert f.read() == f'{{"work_dir": "{str(DEFAULT_WORK_DIR)}", "key": "value"}}'


# TODO: Create more tests of access manager
