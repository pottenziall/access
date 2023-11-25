#  Copyright (c) 2022-2023
#  --------------------------------------------------------------------------
#  Created By: Volodymyr Matsydin
#  version ='1.2.2'
#  -------------------------------------------------------------------------

import io
import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import List, Optional, Set, Type

import gnupg  # type: ignore
from dataclasses import dataclass, fields

_log = logging.getLogger(__name__)

FILE_ITEMS_SEPARATOR = "\n"


@dataclass(frozen=True)
class Credentials:
    id: int
    resource: str
    login: str
    password: str
    kind: str = "authentication"
    updated_on: str = datetime.today().strftime("%d.%m.%Y")

    def __post_init__(self) -> None:
        for field in fields(self):
            field_value = getattr(self, field.name)
            if isinstance(field_value, str) and field_value.count(" "):
                raise ValueError(f"Field '{field.name}' shouldn't contain spaces")
        if not re.match(r"\d\d.\d\d.\d\d\d\d", self.updated_on):
            raise ValueError(f"Wrong date string: {self.updated_on}")

    @classmethod
    def from_string(cls, string_value: str, id_start_from: int = 1) -> Set["Credentials"]:
        credentials = set()
        for i, line in enumerate(string_value.strip().split(FILE_ITEMS_SEPARATOR), start=id_start_from):
            try:
                credentials.add(cls(i, *line.split()))
            except Exception:
                _log.error(f"Invalid line {i}. Skip parsing the line")
        return credentials

    @classmethod
    def from_file(cls, path: Path, id_start_from: int = 1) -> Set["Credentials"]:
        with open(path, "r", encoding="utf8") as f:
            return cls.from_string(f.read(), id_start_from=id_start_from)

    def as_line(self) -> str:
        values = [getattr(self, field.name) for field in fields(self) if field.name != "id"]
        return " ".join(values)

    def __str__(self) -> str:
        values = [str(getattr(self, field.name)) for field in fields(self)]
        return (5 * " ").join(values)


class Encrypter:
    """
    Wrapper class for gnupg encrypter.
    Add/remove/search credentials (e.g. "gmail.com login password authentication") to/from/in an encrypted text file.
    Encrypt a changed content on exiting. Show item creation date.

    :param path: either path to an encrypted *.gpg file or a text file or a directory (will be used as working directory)
    :param passphrase: if provided, a modal window for input a passphrase won't appear (for testing only)
    """

    ENCRYPTED_FILE_EXTENSION = "gpg"

    def __init__(self, path: Path, passphrase: Optional[str] = None):
        self.dir: Optional[Path] = None
        self.encrypted_file_path: Optional[Path] = None
        self._is_content_updated: bool = False
        # TODO: provide path to GPG
        self._gpg = gnupg.GPG()
        self.__credentials: Set[Credentials] = set()
        self._handle_input_path(path=path, passphrase=passphrase)

    def __enter__(self) -> "Encrypter":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.encrypt_into_new_file_if_content_updated()

    def items_count(self) -> int:
        return len(self.__credentials)

    def _handle_input_path(self, path: Path, passphrase: Optional[str] = None) -> None:
        """
        Handle path:
         - a dir: search for latest encrypted file
         - an encrypted file with credentials: decrypt and read its content
         - a text file with credentials: read its content and concatenate with an encrypted file's content
         if found in the same folder
        """
        if path.is_file():
            self.dir = path.parent
            if not path.name.endswith(self.ENCRYPTED_FILE_EXTENSION):
                self._get_credentials_from_text_file(path)
                file_to_decrypt = self.find_newest_encrypted_file()
            else:
                file_to_decrypt = path
        elif path.is_dir():
            self.dir = path
            file_to_decrypt = self.find_newest_encrypted_file()
        else:
            raise ValueError(f"Wrong path passed: {path}")

        if file_to_decrypt is not None:
            self.decrypt_file(path=file_to_decrypt, passphrase=passphrase)

    def _get_sorted_files_by_date_desc(self) -> Optional[List[Path]]:
        """Search for encrypted files in a directory"""
        assert self.dir, "Dir path is not set"
        _log.debug(f'Searching for "{self.ENCRYPTED_FILE_EXTENSION}" files in {self.dir}...')
        file_paths = [p for p in self.dir.iterdir() if p.name.endswith(self.ENCRYPTED_FILE_EXTENSION)]
        if not file_paths:
            _log.warning(f'Encrypted files not found in "{self.dir}"')
            return None
        file_paths = sorted(file_paths, key=lambda x: os.path.getmtime(str(x)), reverse=True)
        max_show_files = 5
        sorted_several_files = ["\n\t" + str(p) for p in file_paths[:max_show_files]]
        _log.debug(f'Latest encrypted files: {"".join(sorted_several_files)}')
        return file_paths

    def find_newest_encrypted_file(self) -> Optional[Path]:
        """Search for newest encrypted file in dir"""
        assert self.dir, "Dir path is not set"
        paths = self._get_sorted_files_by_date_desc()
        if not paths:
            _log.warning(f"Directory {self.dir} does not contain any encrypted files")
            return None
        newest_file_path = paths[0]
        _log.info(f"Newest encrypted file: {newest_file_path}")
        return newest_file_path

    def _get_credentials_from_text_file(self, path: Path) -> None:
        self._update_credentials(Credentials.from_file(path, id_start_from=self.items_count() + 1))
        _log.debug(f"Got credentials of the text file: {path}")

    def decrypt_file(self, path: Path, passphrase: Optional[str] = None) -> None:
        """Decrypt a file using 'passphrase' or invoke a modal window"""
        if not path.is_file() or not path.name.endswith(self.ENCRYPTED_FILE_EXTENSION):
            raise ValueError(f'Path is not a file or is not "{self.ENCRYPTED_FILE_EXTENSION}" file: {path}')
        _log.debug(f"Decrypting {path}...")
        result = self._gpg.decrypt_file(str(path), passphrase=passphrase)
        if not result.ok:
            raise ValueError("Wrong password")
        self.encrypted_file_path = path
        self.__credentials.update(
            Credentials.from_string(result.data.decode("utf8"), id_start_from=self.items_count() + 1)
        )
        _log.debug(f"Got credentials of the encrypted file: {path}")
        del result

    def encrypt_into_new_file_if_content_updated(self, passphrase: Optional[str] = None) -> Optional[Path]:
        """Encrypt updated credentials into a new file"""
        if not self._is_content_updated:
            _log.debug("Content has not been changed. Skip new file creation")
            return None
        _log.debug("Content has been changed. Creating new encrypted file...")
        content_string = FILE_ITEMS_SEPARATOR.join([c.as_line() for c in self.__credentials])
        new_encrypted_file_path = self.encrypt_bytes_content_into_file(
            content=content_string.encode("utf8"), passphrase=passphrase
        )
        del content_string
        self._is_content_updated = False
        self.encrypted_file_path = new_encrypted_file_path
        return new_encrypted_file_path

    def encrypt_bytes_content_into_file(self, content: bytes, passphrase: Optional[str] = None) -> Path:
        """Encrypt bytes content into a new file"""
        v_file = io.BytesIO(initial_bytes=content)
        del content
        assert self.dir, "Dir path is not set"
        file_path = self._generate_file_path(self.dir)
        result = self._gpg.encrypt_file(
            v_file,
            recipients="",
            output=str(file_path),
            symmetric=True,
            passphrase=passphrase,
            extra_args=["--cipher-algo", "AES256"],
        )
        v_file.close()
        if not result.ok:
            raise RuntimeError(f"Encryption process failed with status: '{result.status}'")
        _log.info(f"Encrypted file successfully created: {file_path}")
        return file_path

    def _generate_file_path(self, dir_path: Path) -> Path:
        """Generate unique (within a directory) file name, based on current date
        for an encrypted file (e.g 'access_01012023_5')"""
        for i in range(1, 1000):
            ending = f"_{i}" if i > 1 else ""
            basename = "access_" + datetime.today().strftime("%d%m%Y") + ending
            file_name = basename + "." + self.ENCRYPTED_FILE_EXTENSION
            path = dir_path / file_name
            if not path.exists():
                return path
        name = str(uuid.uuid4()) + "." + self.ENCRYPTED_FILE_EXTENSION
        _log.error(f"All possible file names already exist. Generated a random file name: {name}")
        return dir_path / name

    def add_content(self, content: str) -> None:
        """Add credentials to the existing base in memory"""
        self._update_credentials(Credentials.from_string(content, id_start_from=self.items_count() + 1))

    def _update_credentials(self, credentials_sets: Set[Credentials]) -> None:
        self.__credentials.update(credentials_sets)
        self._is_content_updated = True
        _log.debug(f"{len(credentials_sets)} credentials sets have been added to the existing base in memory")
        _log.debug(f"Total number of credentials in memory: {self.items_count}")

    # TODO: return list instead of set. Increase coverage of related tests
    def search_in_content(self, pattern: str) -> Set[Credentials]:
        """Search for "pattern" in the decrypted file content"""
        if not self.__credentials:
            _log.warning("No content to search in")
            return set()
        found = {c for c in self.__credentials if re.search(pattern, str(c))}
        return found

    def remove_credentials(self, pattern: str) -> None:
        if not pattern:
            _log.warning("Please provide a pattern to remove credentials")
            return
        found = self.search_in_content(pattern)
        self.__credentials = self.__credentials - found
        self._is_content_updated = True
        _log.info(f"{len(found)} credentials removed successfully")
