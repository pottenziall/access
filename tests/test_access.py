#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.0.2'
#  -------------------------------------------------------------------------

import logging
import os
import time
from pathlib import Path
from typing import List, Tuple

import pytest

from src.access_manager import Access, Credentials

PRIVACY_ARCHIVE_EXAMPLE_PATH = Path("encrypted_archive_example.gpg")
TEXT_FILE_EXAMPLE_PATH = Path("text_file_example.txt")
CREDENTIALS_1 = "resource_1 login_1 password_1"
CREDENTIALS_2 = "resource_2 login_2 password_2"
CONTENT = f"{CREDENTIALS_1}\n{CREDENTIALS_2}"
UPDATE_CONTENT = "resource_3 login_3 password_3"
PASSPHRASE = "12345678"

_log = logging.getLogger(__name__)


class TestCredentials:
    @pytest.mark.parametrize(
        "credentials",
        [
            (["resource_1", "login_1", "password_1"],),
            (["resource_2", "login_2", "password_2", "kind_2"],),
        ],
    )
    def test_should_create_credentials_instance_with_valid_values(self, credentials: Tuple[List[str]]) -> None:
        params = credentials[0]
        sut = Credentials(*params)
        assert sut.resource == params[0]
        assert sut.login == params[1]
        assert sut.password == params[2]
        if len(params) == 4:
            assert sut.kind == params[3]

    @pytest.mark.parametrize(
        "wrong_credentials",
        [
            (["resou rce_1", "login_1", "password_1"],),
            (["resource_1", "lo gin_1", "password_1"],),
            (["resource_1", "login_1", "pas sword_1"],),
        ],
    )
    def test_should_raise_exception_on_wrong_input_values(self, wrong_credentials: Tuple[List[str]]) -> None:
        with pytest.raises(ValueError):
            params = wrong_credentials[0]
            Credentials(*params)

    def test_should_string_instance_properly(self) -> None:
        sut = Credentials("resource_1", "login_1", "password_1", "kind_1")
        assert str(sut) == "resource_1     kind_1     login_1     password_1"


class TestInputPath:
    def test_should_recognize_input_dir_path(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()
        access = Access(empty_dir)
        assert access.dir == empty_dir
        assert access.archive_path is None

    def test_should_recognize_input_encrypted_file_path(self) -> None:
        path = PRIVACY_ARCHIVE_EXAMPLE_PATH
        access = Access(path, passphrase=PASSPHRASE)
        assert access.dir == path.parent
        assert access.archive_path == path

    @pytest.mark.parametrize("path", ["/wrong/dir/path", "/wrong/file/path.txt"])
    def test_should_raise_assertion_error_on_wrong_path(self, path: str) -> None:
        with pytest.raises(ValueError):
            Access(Path(path))


class TestAccess:
    def test_should_select_latest_encrypted_archive_from_list_of_ones(  # type: ignore
        self, monkeypatch, tmp_path: Path
    ) -> None:
        access = Access(tmp_path)
        files_names = ["dummy_1.gpg", "dummy_2.gpg", "dummy_3.gpg", "dummy_4.gpg", "dummy_5.gpg"]
        for name in files_names:
            p = tmp_path / name
            p.write_text("dummy content")
            time.sleep(0.1)
        assert len(list(tmp_path.iterdir())) == len(files_names)
        assert access.find_latest_file() == tmp_path / files_names[-1]

    @pytest.mark.parametrize(
        "keyword, result",
        [
            ("resource_1", CREDENTIALS_1),
            ("resource_2", CREDENTIALS_2),
        ],
    )
    def test_should_find_proper_result_for_keyword(self, keyword: str, result: str) -> None:
        resource, login, password = result.split()
        with Access(PRIVACY_ARCHIVE_EXAMPLE_PATH, passphrase=PASSPHRASE) as access:
            found = access.search_in_content(keyword)
            assert found == {Credentials(resource, login, password)}

    def test_pack_updated_content_of_existing_archive_to_new_archive(self) -> None:
        access = Access(PRIVACY_ARCHIVE_EXAMPLE_PATH, passphrase=PASSPHRASE)
        access.add_content(UPDATE_CONTENT)
        access.encrypt_and_export_to_new_file_if_content_updated(passphrase=PASSPHRASE)

        new_access = Access(PRIVACY_ARCHIVE_EXAMPLE_PATH.parent, passphrase=PASSPHRASE)
        resource, login, password = UPDATE_CONTENT.split()
        found = new_access.search_in_content(pattern=resource)
        assert found == {Credentials(resource, login, password)}
        assert new_access.archive_path is not None
        os.remove(new_access.archive_path)

    def test_pack_updated_content_of_text_file_to_new_archive(self) -> None:
        access = Access(TEXT_FILE_EXAMPLE_PATH, passphrase=PASSPHRASE)
        access.add_content(UPDATE_CONTENT)
        access.encrypt_and_export_to_new_file_if_content_updated(passphrase=PASSPHRASE)

        new_access = Access(PRIVACY_ARCHIVE_EXAMPLE_PATH.parent, passphrase=PASSPHRASE)
        for line in CONTENT.splitlines() + [UPDATE_CONTENT]:
            resource, login, password = line.split()
            found = new_access.search_in_content(pattern=resource)
            assert found == {Credentials(resource, login, password)}

        assert new_access.archive_path is not None
        os.remove(new_access.archive_path)

    def test_should_remove_credentials_for_the_pattern(self) -> None:
        access = Access(PRIVACY_ARCHIVE_EXAMPLE_PATH, passphrase=PASSPHRASE)
        pattern = "resource"
        exist = access.search_in_content(pattern=pattern)
        assert len(exist) == 2
        access.remove_credentials(pattern=pattern)

        exist = access.search_in_content(pattern=pattern)
        assert len(exist) == 0

