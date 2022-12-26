import logging
import os
import re
from datetime import datetime
from typing import List, Optional

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
_logger.addHandler(logging.StreamHandler())

PRIVACY_ARCHIVE_EXTENSION = "gpg"
PRIVACY_FILE_EXTENSION = "txt"
ARCHIVE_NAME = f'dos_{datetime.today().strftime("%d%m%Y")}.{PRIVACY_ARCHIVE_EXTENSION}'
# TODO: Add possibility to unpack, add content and pack again


def remove_file(file_path: str) -> None:
    if not os.path.exists(file_path):
        raise AssertionError(f"Try to remove non-existing file: {file_path}")
    while range(5):
        os.remove(file_path)
        if not os.path.exists(file_path):
            return
    raise AssertionError(f"Not possible to remove file: {file_path}")


class Access:
    def __init__(self, dir_path: str):
        self._path = dir_path
        self.__content: Optional[List[str]] = None

    def search_and_encrypt_file(self) -> None:
        try:
            files = self._sorted_files(extension=PRIVACY_FILE_EXTENSION)
            assert len(files) == 1, f"More than one file found to pack: {files}"
            file_to_pack = files[0]
            self._pack_file_to_gpg(file_to_pack)
        except AssertionError:
            _logger.exception("Error on encrypting new file")

    def search_and_decrypt_file(self) -> None:
        try:
            archives = self._sorted_files(extension=PRIVACY_ARCHIVE_EXTENSION)
            _logger.info(f"Latest archive file: {archives[0]}")
            unpacked_file = self._unpack_gpg(archives[0])
            self.__content = self._read_file(unpacked_file)
        except AssertionError:
            _logger.exception("Error on decrypting the archive")

    def _sorted_files(self, extension: str) -> List[str]:
        _logger.debug(f'Searching files in "{self._path}" with extension "{extension}"')
        file_paths = [os.path.join(self._path, p) for p in os.listdir(self._path) if p.endswith(extension)]
        if not file_paths:
            raise AssertionError(f"Files not found in {self._path}")
        return sorted(file_paths, key=lambda x: os.path.getctime(x), reverse=True)

    @staticmethod
    def _read_file(file_path: str) -> List[str]:
        with open(file_path, "r", encoding='utf8') as f:
            content = f.read().split("\n\n")
        remove_file(file_path)
        return content

    def search(self, key: str) -> List[str]:
        pattern = rf".*{key.lower()}.*[\t\n]"
        if self.__content is None:
            _logger.error("File content is empty")
            return [""]
        return [item for item in self.__content if re.match(pattern, item.lower())]

    @staticmethod
    def _unpack_gpg(archive_path: str) -> str:
        # TODO unpack to the memory
        _logger.debug("Unpacking the private archive...")
        command = f'gpg --decrypt --no-symkey-cache --output {archive_path.split(".")[0]} {archive_path}'
        result = os.system(command)
        if result != 0:
            raise AssertionError(f'Exit code "{result}" of decryption command. Wrong password?')
        file_path = archive_path.split(".")[0]
        assert os.path.exists(file_path), "Unpacked file not found"
        return file_path

    def _pack_file_to_gpg(self, file_path: str) -> str:
        new_archive_path = os.path.join(self._path, ARCHIVE_NAME)
        encrypt_file_command = f"gpg --symmetric --output {new_archive_path} " \
                               f"--no-symkey-cache {file_path}"
        exit_code = os.system(encrypt_file_command)
        if exit_code != 0:
            raise AssertionError(f'Error when encrypting "{file_path}": {exit_code}')
        remove_file(file_path)
        return new_archive_path
