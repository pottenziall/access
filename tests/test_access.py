#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.2.1'
#  -------------------------------------------------------------------------

import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Tuple

import pytest
from dataclasses import fields

from src.encrypter import Credentials, Encrypter, FILE_ITEMS_SEPARATOR

CREDENTIALS_1 = "resource_1 login_1 password_1 authentication 01.01.2023"
CREDENTIALS_2 = "resource_2 login_2 password_2 authorization 01.01.2023"
CREDENTIALS_3 = "resource_3 login_3 password_3 authentication 01.01.2023"
CREDENTIALS_SETS = [CREDENTIALS_1, CREDENTIALS_2, CREDENTIALS_3]
CONTENT = FILE_ITEMS_SEPARATOR.join(CREDENTIALS_SETS)
UPDATE_CONTENT = "resource_4 login_4 password_4 authentication 01.01.2023"
PASSPHRASE = "12345678"

_log = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def gpg_file(tmp_dir: Path, txt_file: Path) -> Path:
    gpg_file_path = tmp_dir / "gpg_with_content_example.gpg"
    os.system(f"gpg -o {gpg_file_path} -cre {txt_file}")
    return gpg_file_path


class TestCredentials:
    @pytest.mark.parametrize(
        "credentials",
        [
            ("resource_1", "login_1", "password_1"),
            ("resource_2", "login_2", "password_2", "kind_2"),
            ("resource_3", "login_3", "password_3", "kind_3", "01.01.2023"),
        ],
    )
    def test_should_create_credentials_instance_from_valid_values(self, credentials: Tuple[str, ...]) -> None:
        sut = Credentials(*credentials)
        for field, result in zip(fields(sut), credentials):
            assert getattr(sut, field.name) == result

    def test_should_create_default_fields_properly(self) -> None:
        sut = Credentials("", "", "")
        assert sut.kind == "authentication"
        assert sut.updated_on == datetime.today().strftime("%d.%m.%Y")

    @pytest.mark.parametrize(
        "wrong_credentials",
        [
            ("resou rce_1", "login_1", "password_1"),
            ("resource_1", "lo gin_1", "password_1"),
            ("resource_1", "login_1", "pas sword_1"),
            ("resource_1", "login_1", "password_1", "kind_1", "0101.2023"),
        ],
    )
    def test_should_raise_exception_on_wrong_input_values(self, wrong_credentials: Tuple[str, ...]) -> None:
        with pytest.raises(ValueError):
            Credentials(*wrong_credentials)

    @pytest.mark.parametrize("content", [CONTENT])
    def test_should_create_credentials_instances_from_string(self, content: str) -> None:
        sut = Credentials.from_string(content)
        assert len(sut) == len(content.split(FILE_ITEMS_SEPARATOR))

    @pytest.mark.parametrize("content, txt_file", [(CONTENT, CONTENT)], indirect=["txt_file"])
    def test_should_create_credentials_instances_from_text_file(self, content: str, txt_file: Path) -> None:
        sut = Credentials.from_file(txt_file)
        assert len(sut) == len(content.split(FILE_ITEMS_SEPARATOR))

    def test_should_string_instance_properly(self) -> None:
        sut = Credentials("resource_1", "login_1", "password_1", "kind_1", "01.01.2023")
        assert str(sut) == "resource_1     login_1     password_1     kind_1     01.01.2023"


class TestEncrypterInputPath:
    def test_should_recognize_dir_path(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()
        encrypter = Encrypter(empty_dir)
        assert encrypter.dir == empty_dir
        assert encrypter.encrypted_file_path is None

    @pytest.mark.parametrize("txt_file", [CONTENT], indirect=["txt_file"])
    def test_should_recognize_encrypted_file_path(self, gpg_file: Path, txt_file: Path) -> None:
        encrypter = Encrypter(gpg_file, passphrase=PASSPHRASE)
        assert encrypter.dir == gpg_file.parent
        assert encrypter.encrypted_file_path == gpg_file

    @pytest.mark.parametrize("txt_file", [CONTENT], indirect=["txt_file"])
    def test_should_recognize_both_text_file_and_encrypted_file_in_same_folder(
            self, txt_file: Path, gpg_file: Path
    ) -> None:
        encrypter = Encrypter(txt_file)
        assert encrypter.dir == txt_file.parent
        assert encrypter.encrypted_file_path is not None

    @pytest.mark.parametrize("wrong_path", ["/wrong/dir/path", "/wrong/file/path.txt"])
    def test_should_raise_assertion_error_on_wrong_path(self, wrong_path: str) -> None:
        with pytest.raises(ValueError):
            Encrypter(Path(wrong_path))


class TestEncrypter:
    def test_should_select_latest_encrypted_file_from_list_of_ones(self, monkeypatch: Any, tmp_path: Path) -> None:
        encrypter = Encrypter(tmp_path)
        files_names = ["dummy_1.gpg", "dummy_2.gpg", "dummy_3.gpg", "dummy_4.gpg", "dummy_5.gpg"]
        for name in files_names:
            p = tmp_path / name
            p.write_text("dummy content")
            time.sleep(0.1)
        assert len(list(tmp_path.iterdir())) == len(files_names)
        assert encrypter.find_newest_encrypted_file() == tmp_path / files_names[-1]

    @pytest.mark.parametrize(
        "keyword, result",
        [
            ("resource_1", CREDENTIALS_1),
            ("resource_2", CREDENTIALS_2),
        ],
    )
    @pytest.mark.parametrize("txt_file", [CONTENT], indirect=["txt_file"])
    def test_should_find_proper_result_for_keyword(
            self, keyword: str, result: str, gpg_file: Path, txt_file: Path
    ) -> None:
        with Encrypter(gpg_file, passphrase=PASSPHRASE) as encrypter:
            found = encrypter.search_in_content(keyword)
            assert found == {Credentials(*result.split())}

    @pytest.mark.parametrize("update, txt_file", [(UPDATE_CONTENT, CONTENT)], indirect=["txt_file"])
    def test_should_encrypt_updated_gpg_file_recognized_content_into_new_file(
            self, update: str, txt_file: Path, gpg_file: Path
    ) -> None:
        encrypter = Encrypter(gpg_file, passphrase=PASSPHRASE)
        encrypter.add_content(update)
        encrypter.encrypt_into_new_file_if_content_updated(passphrase=PASSPHRASE)

        new_encrypter = Encrypter(gpg_file.parent, passphrase=PASSPHRASE)
        resource, *rest = update.split()
        found = new_encrypter.search_in_content(pattern=resource)
        assert found == {Credentials(resource, *rest)}
        assert new_encrypter.encrypted_file_path is not None

    @pytest.mark.parametrize("content, update, txt_file", [(CONTENT, UPDATE_CONTENT, CONTENT)], indirect=["txt_file"])
    def test_should_encrypt_updated_text_file_recognized_content_into_new_file(
            self, content: str, update: str, txt_file: Path
    ) -> None:
        encrypter = Encrypter(txt_file)
        encrypter.add_content(update)
        encrypter.encrypt_into_new_file_if_content_updated(passphrase=PASSPHRASE)

        new_encrypter = Encrypter(txt_file.parent, passphrase=PASSPHRASE)
        for line in content.splitlines() + [update]:
            resource, *rest = line.split()
            found = new_encrypter.search_in_content(pattern=resource)
            assert found == {Credentials(resource, *rest)}

        assert new_encrypter.encrypted_file_path is not None

    @pytest.mark.parametrize("content", [CONTENT])
    @pytest.mark.parametrize("txt_file", [CONTENT], indirect=["txt_file"])
    def test_should_remove_credentials_from_memory_for_the_pattern(
            self, gpg_file: Path, txt_file: Path, content: str
    ) -> None:
        encrypter = Encrypter(gpg_file, passphrase=PASSPHRASE)
        pattern = "resource"
        found = encrypter.search_in_content(pattern=pattern)
        assert len(found) == len(content.split(FILE_ITEMS_SEPARATOR))
        encrypter.remove_credentials(pattern=pattern)

        result = encrypter.search_in_content(pattern=pattern)
        assert len(result) == 0
