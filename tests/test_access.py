import logging
import os

import pytest

from access import ARCHIVE_NAME, Access

CONTENT_EXAMPLE = "abc.com\nname1\npassword1\n\nxyz.com\nname2\npassword2"
PASSWORD_EXAMPLE = "12345678"

_logger = logging.getLogger(__name__)


@pytest.fixture(scope="class")
def file_with_content(tmpdir_factory) -> str:
    _logger.debug("Creating a content file in tmp")
    file_name = "example10102021.txt"
    tmp = tmpdir_factory.mktemp("access")
    file_path = tmp.join(file_name)
    with open(file_path, "w+", encoding='utf8') as f:
        f.write(CONTENT_EXAMPLE)
    return str(file_path)


@pytest.fixture(scope="class")
def archive(tmpdir_factory, file_with_content):
    _logger.debug("Creating a private archive file")
    tmp = tmpdir_factory.mktemp("archive")
    archive_path = tmp.join("private_archive.gpg")
    create_archive_command = f"gpg --pinentry-mode=loopback --passphrase {PASSWORD_EXAMPLE} -c -o {archive_path} " \
                             f"--no-symkey-cache {file_with_content}"
    os.system(create_archive_command)
    return archive_path


class TestAccess:
    @staticmethod
    @pytest.mark.parametrize(
        "key, result",
        [
            ("abc.com", ['abc.com\nname1\npassword1']),
            ("xyz.com", ['xyz.com\nname2\npassword2']),
        ])
    def test_found_proper_result_for_key(archive, key, result):
        access = Access(os.path.dirname(archive))
        access.search_and_decrypt_file()
        assert access.search(key) == result

    @staticmethod
    def test_pack_file_to_archive(file_with_content):
        assert os.path.exists(file_with_content)
        tmp_dir = os.path.dirname(file_with_content)
        access = Access(tmp_dir)
        access.search_and_encrypt_file()
        archive_path = os.path.join(tmp_dir, ARCHIVE_NAME)
        assert not os.path.exists(file_with_content)
        assert os.path.exists(archive_path)
