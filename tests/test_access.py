import pytest
import os
import logging

from access import Access

EXAMPLE = "abc.com\nname1\npassword1\n\nxyz.com\nname2\npassword2"
PASSWORD = "12345678"
_logger = logging.getLogger(__name__)


@pytest.fixture(scope="class")
def content_file(tmpdir_factory):
    _logger.debug("Creating a content file...")
    file_name = "example10102021.txt"
    tmp = tmpdir_factory.mktemp("access")
    with open(tmp.join(file_name), "w+", encoding='utf8') as f:
        f.write(EXAMPLE)
    return tmp, file_name


@pytest.fixture(scope="class")
def archive(content_file):
    _logger.debug("Creating an archive file...")
    tmp, file_name = content_file
    archive_path = tmp.join(f"{file_name}.gpg")
    os.system(f"gpg --pinentry-mode=loopback --passphrase {PASSWORD} -c -o {archive_path} --no-symkey-cache {tmp.join(file_name)}")
    return archive_path


class TestAccess:
    @staticmethod
    def test_key_search(archive):
        access = Access(os.path.dirname(archive))
        found = access.search("abc.com")
        assert found
