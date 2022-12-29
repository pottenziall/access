import logging
import os
from pathlib import Path

import pytest

import utils

_log = logging.getLogger(__name__)

CONTENT = "example\n\ncontent"


@pytest.fixture
def tmp_file(tmp_path) -> Path:
    directory = tmp_path / "sub"
    directory.mkdir()
    file_path = directory / "example.txt"
    file_path.write_text(CONTENT)
    assert file_path.exists()
    return file_path


@pytest.mark.parametrize("name, return_code, result", [("exist_program", 0, True), ("non-exist_program", 1, False)])
def test_program_exist(monkeypatch, name, return_code, result):
    monkeypatch.setattr(os, "system", lambda x: return_code)
    assert utils.program_exists(name=name) == result


@pytest.mark.parametrize("word, pattern, result", [("ABc1", r"\w{3}\d", True), ("ABCD", r"\d{4}", False)])
def test_is_valid(word, pattern, result):
    assert utils.validate_input(value=word, pattern=pattern) == result


def test_get_file_content(tmp_file):
    file_path = str(tmp_file)
    result = utils.get_file_content(file_path)
    assert result == CONTENT


def test_remove_file(tmp_file):
    utils.remove_file(file_path=str(tmp_file))
    assert not tmp_file.exists()
