import io
import logging
import os
import re
from datetime import datetime
from typing import List

import utils

_log = logging.getLogger(__name__)

PRIVACY_ARCHIVE_EXTENSION = "gpg"
PRIVACY_FILE_EXTENSION = "txt"


def generate_archive_name() -> str:
    basename = "dos_" + datetime.today().strftime("%d%m%Y")
    return basename + "." + PRIVACY_ARCHIVE_EXTENSION


# TODO: Add possibility to unpack, add content and pack again


class Access:
    def __init__(self, dir_path: str):
        self._path = dir_path
        self.__content: str = ""
        self._added_new_content: bool = False

    def search_and_decrypt_latest_file(self) -> None:
        try:
            archives = self._sorted_files(extension=PRIVACY_ARCHIVE_EXTENSION)
            _log.info(f"Latest archive file: {archives[0]}")
            unpacked_file = self._unpack_gpg(archives[0])
            self.__content = utils.get_file_content(unpacked_file)
            utils.remove_file(unpacked_file)
        except AssertionError:
            _log.exception("Error on decrypting the archive")

    def _sorted_files(self, extension: str) -> List[str]:
        _log.debug(f'Searching files in "{self._path}" with extension "{extension}"')
        file_paths = [os.path.join(self._path, p) for p in os.listdir(self._path) if p.endswith(extension)]
        if not file_paths:
            raise AssertionError(f"Files not found in {self._path}")
        return sorted(file_paths, key=lambda x: os.path.getctime(x), reverse=True)

    def search(self, key: str) -> List[str]:
        pattern = rf".*{key.lower()}.*[\t\n]"
        if not self.__content:
            _log.error("File content is empty")
            return [""]
        found = [item for item in self.__content.split("\n\n") if re.match(pattern, item.lower())]
        if not found:
            _log.info(f'Phrase "{key}" not found')
        return found

    @staticmethod
    def _unpack_gpg(archive_path: str) -> str:
        # TODO unpack into a memory
        _log.debug("Unpacking the private archive...")
        command = f'gpg --decrypt --no-symkey-cache --output {archive_path.split(".")[0]} {archive_path}'
        result = os.system(command)
        if result != 0:
            raise AssertionError(f'Exit code "{result}" of decryption command. Wrong password?')
        file_path = archive_path.split(".")[0]
        assert os.path.exists(file_path), "Unpacked file not found"
        return file_path

    def pack_content_to_gpg(self) -> None:
        """

        try:
            p = Popen(cmd, shell=False, stdin=PIPE, stdout=PIPE, stderr=PIPE
            stdin = p.stdin
            if passphrase:
                _write_passphrase(stdin, passphrase, self.encoding)
            writer = _threaded_copy_data(fileobj, stdin)
            self._collect_output(p, result, writer, stdin)
            return result
        finally:
            writer.join(0.01)
            if fileobj is not fileobj_or_path:
                fileobj.close()
        """
        if not self._added_new_content:
            _log.info("Content not changed, archive creation canceled")
            # return
        vfile = io.StringIO(initial_value=self.__content)
        archive_name = generate_archive_name()
        new_archive_path = os.path.join(self._path, archive_name)
        encrypt_file_command = f"gpg --symmetric --output {new_archive_path} " \
                               f"--no-symkey-cache {vfile}"
        exit_code = os.system(encrypt_file_command)
        if exit_code != 0:
            raise AssertionError(f'Error when encrypting: {exit_code}')
        _log.info(f"Archive with new content successfully created: {new_archive_path}")

    def add_content(self, new_content: str) -> None:
        self.__content = self.__content + new_content
        self._added_new_content = True
