#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.1.0'
#  -------------------------------------------------------------------------

import logging
from pathlib import Path
from typing import Any, Dict

import pytest

import src.utils as utils

_log = logging.getLogger(__name__)


@pytest.fixture
def tmp_file(tmp_path: Path, request: Any) -> Path:
    directory = tmp_path / "sub"
    directory.mkdir()
    file_path = directory / "example_file"
    file_path.write_text(request.param)
    assert file_path.exists()
    return file_path


@pytest.mark.parametrize("word, pattern, result", [("ABc1", r"\w{3}\d", True), ("ABCD", r"\d{4}", False)])
def test_should_check_if_input_value_is_valid(word: str, pattern: str, result: bool) -> None:
    assert utils.is_input_valid(value=word, pattern=pattern) == result


@pytest.mark.parametrize(
    "tmp_file, data, result",
    [
        ('{"work_path": "/dummy/path"}', {"work_path": "/dummy/path1"}, '{"work_path": "/dummy/path1"}'),
        ('{"timeout_coef": 3.6}', {"timeout_coef": 3.6}, '{"timeout_coef": 3.6}'),
        ('{"work_path": "/dummy/path"}', {"timeout_coef": 3.6}, '{"work_path": "/dummy/path", "timeout_coef": 3.6}'),
        ("{}", {"timeout_coef": 3.6}, '{"timeout_coef": 3.6}'),
    ],
    indirect=["tmp_file"],
)
def test_should_add_content_to_config_file(tmp_file: Path, data: Dict[str, str], result: utils.JsonContent) -> None:
    utils.update_config(tmp_file, data)
    with open(tmp_file, "r", encoding="utf8") as f:
        assert f.read() == result


@pytest.mark.parametrize(
    "tmp_file, result",
    [
        ('{"work_path": "/dummy/path"}', {"work_path": "/dummy/path"}),
        ('{"timeout_coef": 3}', {"timeout_coef": 3}),
        ('{"float_coef": 3.6}', {"float_coef": 3.6}),
    ],
    indirect=["tmp_file"],
)
def test_should_read_config_file_content(tmp_file: Path, result: utils.JsonContent) -> None:
    assert utils.read_config(tmp_file) == result
