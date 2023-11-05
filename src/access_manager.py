#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.2.0'
#  -------------------------------------------------------------------------

import io
import logging
import os
import re
from dataclasses import dataclass, fields
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import List, Optional, Set, Type

import gnupg  # type: ignore

_log = logging.getLogger(__name__)

PRIVACY_ARCHIVE_EXTENSION = "gpg"
FILE_ITEMS_SEPARATOR = "\n"


@dataclass(frozen=True)
class Credentials:
    resource: str
    login: str
    password: str
    kind: str = "authentication"
    updated_on: str = datetime.today().strftime("%d.%m.%Y")

    def __post_init__(self) -> None:
        for field in fields(self):
            field_value = getattr(self, field.name)
            if field_value.count(" "):
                raise ValueError(f"Field '{field.name}' shouldn't contain spaces")
        if not re.match(r"\d\d.\d\d.\d\d\d\d", self.updated_on):
            raise ValueError(f"Wrong date string: {self.updated_on}")

    @classmethod
    def from_string(cls, string_value: str) -> Set["Credentials"]:
        credentials = set()
        for i, line in enumerate(string_value.strip().split(FILE_ITEMS_SEPARATOR), start=1):
            try:
                credentials.add(cls(*line.split()))
            except Exception:
                _log.error(f"Invalid line {i}. Skip parsing the line")
        return credentials

    @classmethod
    def from_file(cls, path: Path) -> Set["Credentials"]:
        with open(path, "r", encoding="utf8") as f:
            return cls.from_string(f.read())

    def as_line(self) -> str:
        values = [getattr(self, field.name) for field in fields(self)]
        return " ".join(values)

    def __str__(self) -> str:
        values = [getattr(self, field.name) for field in fields(self)]
        return (5 * " ").join(values)


class Access:
    """
    Wrapper class for 'gnupg' encrypter.
    Save credentials (e.g. "gmail.com login password authentication") into an encrypted file.
    Automatic changed content encryption on exiting.

    :param path: either path to an encrypted file or a directory that will be used as working directory
    :param passphrase: if provided, a modal window for input a passphrase won't appear (useful for testing)
    :param extension: file extension that the class works with
    """

    def __init__(
            self,
            path: Path,
            passphrase: Optional[str] = None,
            extension: str = PRIVACY_ARCHIVE_EXTENSION,
    ) -> None:
        self.dir: Optional[Path] = None
        self.archive_path: Optional[Path] = None
        self._ext: str = extension
        self.__credentials: Set[Credentials] = set()
        self._content_updated: bool = False
        self._gpg = gnupg.GPG()
        self._recognize_and_work_with_path(path=path, passphrase=passphrase)

    def __enter__(self) -> "Access":
        return self

    def __exit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc_val: Optional[BaseException],
            exc_tb: Optional[TracebackType],
    ) -> None:
        self.encrypt_and_export_to_new_file_if_content_updated()

    def _recognize_and_work_with_path(self, path: Path, passphrase: Optional[str] = None) -> None:
        """
        Recognize path:
            - a dir: search for latest encrypted file
            - an encrypted file: decrypt and load its content
            - a text file: load its content and concatenate with an encrypted file if found in the folder
        """
        if path.is_file():
            self.dir = path.parent
            if path.name.endswith(self._ext):
                self.decrypt_file(path=path, passphrase=passphrase)
                return
            self._read_file(path)
            self._find_and_decrypt_file(passphrase=passphrase)
        elif path.is_dir():
            self.dir = path
            self._find_and_decrypt_file(passphrase=passphrase)
        else:
            raise ValueError(f"Wrong path passed: {path}")

    def _read_file(self, path: Path) -> None:
        self._update_credentials(Credentials.from_file(path))
        _log.debug(f"Got content of the file: {path}")

    def _find_and_decrypt_file(self, passphrase: Optional[str] = None) -> None:
        archive_path = self.find_latest_file()
        if archive_path is None:
            _log.warning(f"Directory {self.dir} does not contain any files to decrypt")
            return
        self.decrypt_file(path=archive_path, passphrase=passphrase)

    def find_latest_file(self) -> Optional[Path]:
        """Search for latest file with 'extension' extension"""
        assert self.dir, "Dir path is not set"
        sorted_files_paths = self._get_sorted_files_by_date_desc()
        if not sorted_files_paths:
            return None
        latest_file_path = sorted_files_paths[0]
        _log.info(f"Latest encrypted archive: {latest_file_path}")
        return latest_file_path

    def _get_sorted_files_by_date_desc(self) -> Optional[List[Path]]:
        """Search in a directory for files with "self._ext" extension"""
        assert self.dir, "Dir path is not set"
        _log.debug(f'Searching for "{self._ext}" files in {self.dir}...')
        file_paths = [p for p in self.dir.iterdir() if p.name.endswith(self._ext)]
        if not file_paths:
            _log.warning(f"No '{self._ext}' files found in {self.dir}")
            return None
        file_paths = sorted(file_paths, key=lambda x: os.path.getmtime(str(x)), reverse=True)
        max_show_files = 5
        sorted_several_files = ["\n\t" + str(p) for p in file_paths[:max_show_files]]
        _log.debug(f'First up to {max_show_files} "{self._ext}" files: {"".join(sorted_several_files)}')
        return file_paths

    def decrypt_file(self, path: Path, passphrase: Optional[str] = None) -> None:
        """Decrypt a file either with 'passphrase' or with modal window"""
        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        if not path.name.endswith(self._ext):
            raise ValueError(f'File must be a "{self._ext}" file but got: {path}')
        _log.debug(f"Decrypting {path}...")
        result = self._gpg.decrypt_file(str(path), passphrase=passphrase)
        if not result.ok:
            _log.error("Wrong password")
            raise ValueError("Wrong password")
        self.archive_path = path
        self.__credentials.update(Credentials.from_string(result.data.decode("utf8")))
        _log.debug(f"Got credentials of the file: {path}")
        del result

    def search_in_content(self, pattern: str) -> Set[Credentials]:
        """Search for 'keyword' within decrypted file content"""
        if not self.__credentials:
            _log.warning("No content to search in")
            return set()
        found = {c for c in self.__credentials if re.search(pattern, str(c))}
        _log.info(f"Found {len(found)} credentials")
        return found

    def encrypt_and_export_to_new_file_if_content_updated(self, passphrase: Optional[str] = None) -> Optional[Path]:
        """Encrypt updated content into a new file"""
        if not self._content_updated:
            _log.debug("Content has not been changed. Skip new file creation")
            return None
        _log.debug("Content has been changed. Creating new archive file...")
        content_string = FILE_ITEMS_SEPARATOR.join([c.as_line() for c in self.__credentials])
        archive_path = self.encrypt_content_and_export_to_file(
            content=content_string.encode("utf8"), passphrase=passphrase
        )
        del content_string
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
            raise RuntimeError(f"Encryption process failed with status: '{result.status}'")
        _log.info(f"Encrypted archive successfully created: {archive_path}")
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
        """Add credentials to the existing base in memory"""
        self._update_credentials(Credentials.from_string(new_content))

    def _update_credentials(self, credentials_sets: Set[Credentials]) -> None:
        self.__credentials.update(credentials_sets)
        self._content_updated = True
        _log.debug(f"{len(credentials_sets)} new credentials sets has been added to the existing base in memory")

    def remove_credentials(self, pattern: str) -> None:
        if not pattern:
            _log.warning("Please provide a pattern to remove credentials")
            return
        found = self.search_in_content(pattern)
        self.__credentials = self.__credentials - found
        self._content_updated = True
        _log.info(f"{len(found)} credentials removed successfully")
