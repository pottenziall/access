#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.2.3'
#  -------------------------------------------------------------------------

import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Tuple, Iterator, List

import pytest
from dataclasses import fields

from src.encrypter import Credentials, Encrypter, FILE_ITEMS_SEPARATOR

_log = logging.getLogger(__name__)

CREDENTIALS_1 = "resource_1 login_1 password_1 authentication 01.01.2023"
CREDENTIALS_2 = "resource_2 login_2 password_2 authorization 01.01.2023"
CREDENTIALS_3 = "resource_3 login_3 password_3 authentication 01.01.2023"
CREDENTIALS_SETS = [CREDENTIALS_1, CREDENTIALS_2, CREDENTIALS_3]
CONTENT = FILE_ITEMS_SEPARATOR.join(CREDENTIALS_SETS)
UPDATE_CONTENT = "resource_4 login_4 password_4 authentication 01.01.2023"
PASSPHRASE = "12345678"

TestItems = Tuple[Path, List[str]]


@pytest.fixture(scope="session")
def gpg_file(tmp_dir: Path, txt_file: TestItems) -> TestItems:
    gpg_file_path = tmp_dir / "gpg_with_content_example.gpg"
    txt_path, content = txt_file
    os.system(f"gpg -o {gpg_file_path} -cre {txt_path}")
    return gpg_file_path, content


@pytest.fixture(scope="function")
def updated_gpg_file(tmp_dir: Path, gpg_file: TestItems, request: Any) -> Iterator[TestItems]:
    gpg_path, content = gpg_file
    encrypter = Encrypter(gpg_path, passphrase=PASSPHRASE)
    encrypter.add_content(request.param)
    updated_file_path = encrypter.encrypt_into_new_file_if_content_updated(passphrase=PASSPHRASE)
    assert updated_file_path is not None
    yield updated_file_path, content + [request.param]
    os.remove(updated_file_path)


class TestCredentials:
    @pytest.mark.parametrize(
        "row_id, credentials",
        [
            (1, ("resource_1", "login_1", "password_1")),
            (2, ("resource_2", "login_2", "password_2", "kind_2")),
            (3, ("resource_3", "login_3", "password_3", "kind_3", "01.01.2023")),
        ],
    )
    def test_should_create_credentials_instance_from_valid_values(
        self, row_id: int, credentials: Tuple[str, ...]
    ) -> None:
        sut = Credentials(row_id, *credentials)
        for field, result in zip(fields(sut), [row_id, *credentials]):
            assert getattr(sut, field.name) == result

    def test_should_create_default_fields_properly(self) -> None:
        sut = Credentials(1, "", "", "")
        assert sut.kind == "authentication"
        assert sut.updated_on == datetime.today().strftime("%d.%m.%Y")

    @pytest.mark.parametrize(
        "row_id, wrong_credentials",
        [
            (1, ("resou rce_1", "login_1", "password_1")),
            (2, ("resource_1", "lo gin_1", "password_1")),
            (3, ("resource_1", "login_1", "pas sword_1")),
            (4, ("resource_1", "login_1", "password_1", "kind_1", "0101.2023")),
        ],
    )
    def test_should_raise_exception_on_wrong_input_values(
        self, row_id: int, wrong_credentials: Tuple[str, ...]
    ) -> None:
        with pytest.raises(ValueError):
            Credentials(row_id, *wrong_credentials)

    @pytest.mark.parametrize("content", [CONTENT])
    def test_should_create_credentials_instances_from_string(self, content: str) -> None:
        sut = Credentials.from_string(content)
        assert len(sut) == len(content.split(FILE_ITEMS_SEPARATOR))

    @pytest.mark.parametrize("txt_file", [CONTENT], indirect=["txt_file"])
    def test_should_create_credentials_instances_from_text_file(self, txt_file: TestItems) -> None:
        txt_path, content = txt_file
        sut = Credentials.from_file(txt_path)
        assert len(sut) > 0
        assert len(sut) == len(content)

    def test_should_string_instance_properly(self) -> None:
        sut = Credentials(1, "resource_1", "login_1", "password_1", "kind_1", "01.01.2023")
        assert str(sut) == "1     resource_1     login_1     password_1     kind_1     01.01.2023"

    @pytest.mark.parametrize(
        "txt_file, updated_gpg_file", [(CONTENT, UPDATE_CONTENT)], indirect=["txt_file", "updated_gpg_file"]
    )
    def test_should_assign_proper_credentials_id(
            self,
            txt_file: TestItems,
            updated_gpg_file: TestItems,
    ) -> None:
        updated_gpg_path, content = updated_gpg_file
        encrypter = Encrypter(updated_gpg_path, passphrase=PASSPHRASE)
        for line_number, item in enumerate(content, start=1):
            resource, *rest = item.split()
            found = encrypter.search_in_content(resource)
            assert len(found) == 1
            assert found[0].id == line_number


class TestEncrypterInputPath:
    def test_should_recognize_dir_path(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()
        encrypter = Encrypter(empty_dir)
        assert encrypter.dir == empty_dir
        assert encrypter.encrypted_file_path is None

    @pytest.mark.parametrize("txt_file", [CONTENT], indirect=["txt_file"])
    def test_should_recognize_encrypted_file_path(self, gpg_file: TestItems, txt_file: TestItems) -> None:
        gpg_path, _ = gpg_file
        encrypter = Encrypter(gpg_path, passphrase=PASSPHRASE)
        assert encrypter.dir == gpg_path.parent
        assert encrypter.encrypted_file_path == gpg_path

    @pytest.mark.parametrize("txt_file", [CONTENT], indirect=["txt_file"])
    def test_should_recognize_both_text_file_and_encrypted_file_in_same_folder(
            self, txt_file: TestItems, gpg_file: TestItems
    ) -> None:
        gpg_path, _ = gpg_file
        txt_path, _ = txt_file
        encrypter = Encrypter(txt_path)
        assert encrypter.dir == txt_path.parent
        assert encrypter.encrypted_file_path == gpg_path

    @pytest.mark.parametrize("wrong_path", ["/wrong/dir/path", "/wrong/file/path.txt"])
    def test_should_raise_assertion_error_on_wrong_path(self, wrong_path: str) -> None:
        with pytest.raises(ValueError):
            Encrypter(Path(wrong_path))


class TestEncrypter:
    def test_should_select_latest_encrypted_file_from_list_of_ones(self, tmp_path: Path) -> None:
        encrypter = Encrypter(tmp_path)
        file_names = ["dummy_1.gpg", "dummy_2.gpg", "dummy_3.gpg", "dummy_4.gpg", "dummy_5.gpg"]
        for name in file_names:
            p = tmp_path / name
            p.write_text("dummy content")
            time.sleep(0.1)
        assert len(list(tmp_path.iterdir())) == len(file_names)
        assert encrypter.find_newest_encrypted_file() == tmp_path / file_names[-1]

    @pytest.mark.parametrize("txt_file", [CONTENT], indirect=["txt_file"])
    def test_should_find_proper_result_for_keyword(self, gpg_file: TestItems, txt_file: TestItems) -> None:
        gpg_path, content = gpg_file
        with Encrypter(gpg_path, passphrase=PASSPHRASE) as encrypter:
            for i, credentials_set in enumerate(content, start=1):
                resource, *rest = credentials_set.split()
                found = encrypter.search_in_content(resource)
                assert len(found) > 0
                assert found == [Credentials(i, *credentials_set.split())]

    @pytest.mark.parametrize(
        "updated_gpg_file, txt_file",
        [(UPDATE_CONTENT, CONTENT)],
        indirect=["updated_gpg_file", "txt_file"],
    )
    def test_should_encrypt_updated_gpg_file_recognized_content_into_new_file(
            self, txt_file: TestItems, updated_gpg_file: TestItems
    ) -> None:
        updated_gpg_path, content = updated_gpg_file
        encrypter = Encrypter(updated_gpg_path, passphrase=PASSPHRASE)
        resource, *rest = content[3].split()
        found = encrypter.search_in_content(pattern=resource)
        assert len(found) == 1
        assert found[0].resource == resource
        assert found[0].id == 4
        assert encrypter.encrypted_file_path == updated_gpg_path

    @pytest.mark.parametrize("txt_file", [CONTENT], indirect=["txt_file"])
    def test_should_remove_credentials_from_memory_for_the_pattern(
            self, gpg_file: TestItems, txt_file: TestItems
    ) -> None:
        gpg_path, content = gpg_file
        resource, *rest = content[0].split()
        encrypter = Encrypter(gpg_path, passphrase=PASSPHRASE)
        found = encrypter.search_in_content(pattern=resource)
        assert len(found) == 1
        removed = encrypter.remove_credentials(pattern=resource)
        assert removed == 1

        result = encrypter.search_in_content(pattern=resource)
        assert len(result) == 0
