#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.0.2'
#  -------------------------------------------------------------------------

import logging
from pathlib import Path

import pytest

import src.utils as utils

_log = logging.getLogger(__name__)

CONTENT = "example\n\ncontent"


@pytest.fixture
def tmp_file(tmp_path: Path) -> Path:
    directory = tmp_path / "sub"
    directory.mkdir()
    file_path = directory / "example.txt"
    file_path.write_text(CONTENT)
    assert file_path.exists()
    return file_path


@pytest.mark.parametrize("word, pattern, result", [("ABc1", r"\w{3}\d", True), ("ABCD", r"\d{4}", False)])
def test_should_check_if_input_value_is_valid(word: str, pattern: str, result: bool) -> None:
    assert utils.is_input_valid(value=word, pattern=pattern) == result
