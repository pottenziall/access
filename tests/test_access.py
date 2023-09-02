#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.0'
#  -------------------------------------------------------------------------

import logging
import os
from pathlib import Path
from typing import List

import pytest

from access import Access

PRIVACY_ARCHIVE_EXAMPLE_PATH = Path("access_example_10032023.gpg")
PRIVACY_ARCHIVE_CONTENT = "abc.com\nname1\npassword1\r\n\r\nxyz.com\nname2\npassword2"
UPDATE_PRIVACY_ARCHIVE_CONTENT = "google.com name3 password3"
TEXT_FILE_EXAMPLE_PATH = Path("text_file_example.txt")
TEXT_FILE_CONTENT = "first line of content\nsecond line of content"
UPDATE_TEXT_FILE_CONTENT = "third line of content"
PASSPHRASE = "12345678"

_log = logging.getLogger(__name__)


class TestInputPath:
    def test_should_recognize_input_dir_path(self, tmp_path) -> None:
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
        with pytest.raises(AssertionError):
            Access(Path(path))


class TestAccess:
    @pytest.mark.parametrize(
        "keyword, result",
        [
            ("abc.com", ["abc.com\nname1\npassword1"]),
            ("xyz.com", ["xyz.com\nname2\npassword2"]),
        ],
    )
    def test_should_find_proper_result_for_keyword(
        self, keyword: str, result: List[str]
    ) -> None:
        with Access(PRIVACY_ARCHIVE_EXAMPLE_PATH, passphrase=PASSPHRASE) as access:
            found = access.search_in_content(keyword)
            assert found == result

    def test_pack_updated_content_of_existing_archive_to_new_archive(self) -> None:
        access = Access(PRIVACY_ARCHIVE_EXAMPLE_PATH, passphrase=PASSPHRASE)
        access.add_content(UPDATE_PRIVACY_ARCHIVE_CONTENT)
        access.encrypt_and_export_to_new_file_if_content_updated(passphrase=PASSPHRASE)

        new_access = Access(PRIVACY_ARCHIVE_EXAMPLE_PATH.parent, passphrase=PASSPHRASE)
        found = new_access.search_in_content(keyword="google.com")
        assert found == [UPDATE_PRIVACY_ARCHIVE_CONTENT]
        assert new_access.archive_path is not None
        os.remove(new_access.archive_path)

    def test_pack_updated_content_of_text_file_to_new_archive(self) -> None:
        access = Access(TEXT_FILE_EXAMPLE_PATH, passphrase=PASSPHRASE)
        access.add_content(UPDATE_TEXT_FILE_CONTENT)
        access.encrypt_and_export_to_new_file_if_content_updated(passphrase=PASSPHRASE)

        new_access = Access(PRIVACY_ARCHIVE_EXAMPLE_PATH.parent, passphrase=PASSPHRASE)
        for line in TEXT_FILE_CONTENT.splitlines() + [UPDATE_TEXT_FILE_CONTENT]:
            found = new_access.search_in_content(keyword=line)
            assert found == [line]
        assert new_access.archive_path is not None
        os.remove(new_access.archive_path)
