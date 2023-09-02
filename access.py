#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.0'
#  -------------------------------------------------------------------------

import io
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import List, Optional, Type

import gnupg  # type: ignore

_log = logging.getLogger(__name__)

PRIVACY_ARCHIVE_EXTENSION = "gpg"
FILE_ITEMS_SEPARATOR = "\r\n\r\n"


class Access:
    """
    Wrapper class for 'gnupg' encrypter.
    Save info sets (e.g. "gmail.com login password") separated by 'separator' into an encrypted file.
    Use context manager for automatic encrypting some changed content on exiting.

    :param path: either path to an encrypted file or a directory that will be used as working directory
    :param passphrase: if provided, a modal window for input a passphrase won't appear (useful for testing)
    :param extension: file extension that the class works with
    :param separator: separator for info sets in an encrypted file content
    """

    def __init__(
        self,
        path: Path,
        passphrase: Optional[str] = None,
        extension: str = PRIVACY_ARCHIVE_EXTENSION,
        separator: str = FILE_ITEMS_SEPARATOR,
    ) -> None:
        self.dir: Optional[Path] = None
        self.archive_path: Optional[Path] = None
        self._ext: str = extension
        self._sep: str = separator
        self.__content: str = ""
        self._content_updated: bool = False
        self._gpg = gnupg.GPG()  # verbose=True)
        self._recognize_and_work_with_path(path=path, passphrase=passphrase)

    def __enter__(self) -> "Access":
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        self.encrypt_and_export_to_new_file_if_content_updated()

    def _recognize_and_work_with_path(self, path: Path, passphrase: Optional[str] = None) -> None:
        """
        Recognize path:
            - search for encrypt files if is a dir
            - decrypt if an encrypted file
            - import content into a memory if a text file
        """
        if path.is_file():
            self.dir = path.parent
            if path.name.endswith(self._ext):
                self.decrypt_file(path=path, passphrase=passphrase)
                return
            self._read_file(path)
        elif path.is_dir():
            self.dir = path
            self._find_and_decrypt_file(passphrase=passphrase)
        else:
            raise AssertionError(f"Wrong path passed: {path}")

    def _read_file(self, path: Path) -> None:
        try:
            with open(path, "r", encoding="utf8") as f:
                self.__content = f.read().replace("\n", self._sep)
                _log.debug(f"Got content of the file: {path}")
        except Exception:
            _log.error(f"Unable to read the text file: {path}. Skip reading")

    def _find_and_decrypt_file(self, passphrase: Optional[str] = None) -> None:
        archive_path = self.find_latest_file()
        if archive_path is None:
            _log.warning(f"{self.dir} does not contain any files to decrypt")
            return
        self.decrypt_file(path=archive_path, passphrase=passphrase)

    def find_latest_file(self) -> Optional[Path]:
        """Search for latest file with 'extension' extension"""
        assert self.dir, "Dir path is not set"
        sorted_files_paths = self._get_sorted_files_by_date_desc()
        if not sorted_files_paths:
            return None
        latest_file_path = sorted_files_paths[0]
        _log.info(f"Latest encrypted file: {latest_file_path}")
        return latest_file_path

    def _get_sorted_files_by_date_desc(self) -> List[Path]:
        """Search in a directory for files with "self._ext" extension"""
        assert self.dir, "Dir path is not set"
        _log.debug(f'Search for "{self._ext}" files in {self.dir}...')
        file_paths = [p for p in self.dir.iterdir() if p.name.endswith(self._ext)]
        if not file_paths:
            _log.warning(f"No '{self._ext}' files found in {self.dir}")
        file_paths = sorted(file_paths, key=lambda x: os.path.getctime(str(x)), reverse=True)
        sorted_several_files = ["\n\t" + str(p) for p in file_paths[:10]]
        _log.debug(f"First up to 10 files: {''.join(sorted_several_files)}" + "\n\t...")
        return file_paths

    def decrypt_file(self, path: Path, passphrase: Optional[str] = None) -> None:
        """Decrypt a file either with 'passphrase' or with modal window"""
        if not path.is_file():
            raise AssertionError(f"Path is not a file: {path}")
        if not path.name.endswith(self._ext):
            raise AssertionError(f'File must be a "{self._ext}" file but got: {path}')
        _log.debug(f"Decrypting {path}...")
        result = self._gpg.decrypt_file(str(path), passphrase=passphrase)
        if not result.ok:
            _log.error("Wrong password")
            raise AssertionError("Wrong password")
        self.archive_path = path
        # TODO: use dataclass for credential items
        self.__content = result.data.decode("utf8")
        _log.debug(f"Got content of {path}")
        del result

    def search_in_content(self, keyword: str) -> List[str]:
        """Search for 'keyword' within decrypted file content"""
        if not self.__content:
            _log.error("File content is empty")
            return ["<No content to search in>"]
        # TODO: improve search pattern
        pattern = f".{{,8}}{keyword.lower()}.*"
        found = [item for item in self.__content.split(self._sep) if re.match(pattern, item.lower())]
        if not found:
            _log.info(f'Phrase "{keyword}" not found')
        return found

    def encrypt_and_export_to_new_file_if_content_updated(self, passphrase: Optional[str] = None) -> Optional[Path]:
        """Encrypt updated content into a new file"""
        if not self._content_updated:
            _log.debug("Content has not been changed. Skip new file creation")
            return None
        _log.debug("Content has been changed. Creating new file...")
        content = self.__content.encode("utf8")
        archive_path = self.encrypt_content_and_export_to_file(content=content, passphrase=passphrase)
        del content
        self._content_updated = False
        self.archive_path = archive_path
        return archive_path

    def encrypt_content_and_export_to_file(self, content: bytes, passphrase: Optional[str] = None) -> Path:
        """Encrypt bytes content and export to a new file"""
        v_file = io.BytesIO(initial_bytes=content)
        del content
        archive_path = self._generate_file_path()
        result = self._gpg.encrypt_file(
            v_file,
            recipients="",
            output=str(archive_path),
            symmetric=True,
            passphrase=passphrase,
            extra_args=["--cipher-algo", "AES256"],
        )
        v_file.close()
        if not result.ok:
            raise AssertionError(f"Encryption process failed with status: '{result.status}'")
        _log.info(f"Encrypted file successfully created: {archive_path}")
        return archive_path

    def _generate_file_path(self) -> Path:
        """Generate unique (within a folder) file name, based on current date
        for an encrypted file (e.g 'access_01012023_5')"""
        assert self.dir, "Dir path is not set"
        for i in range(1, 1000):
            ending = f"_{i}" if i > 1 else ""
            basename = "access_" + datetime.today().strftime("%d%m%Y") + ending
            archive_name = basename + "." + self._ext
            path = self.dir / archive_name
            if not path.exists():
                return path
        raise RuntimeError("All possible file names already exist. Remove at least one old file")

    def add_content(self, new_content: str) -> None:
        """Add info to an existing content"""
        if not self.__content.endswith(self._sep):
            self.__content += self._sep
        self.__content = self.__content + new_content
        self._content_updated = True
        _log.debug("New content added to list")
