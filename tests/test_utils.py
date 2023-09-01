#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.0'
#  -------------------------------------------------------------------------

import logging
from pathlib import Path

import pytest

import utils

_log = logging.getLogger(__name__)

CONTENT = "example\n\ncontent"


# TODO: add test for sorting files


@pytest.fixture
def tmp_file(tmp_path) -> Path:
    directory = tmp_path / "sub"
    directory.mkdir()
    file_path = directory / "example.txt"
    file_path.write_text(CONTENT)
    assert file_path.exists()
    return file_path


@pytest.mark.parametrize(
    "word, pattern, result", [("ABc1", r"\w{3}\d", True), ("ABCD", r"\d{4}", False)]
)
def test_is_valid(word, pattern, result):
    assert utils.validate_input(value=word, pattern=pattern) == result
