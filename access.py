import os
import re
import logging
import typing

from glob import glob
from datetime import datetime
from os import path, listdir, system

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
_logger.addHandler(logging.StreamHandler())


class Access:
    def __init__(self, path: str):
        self._path = path
        self._file = None
        self.__content = None
        self._get_last_archive()
        self._unpack_gpg()
        self._read_data()

    def _get_last_archive(self) -> None:
        date_pattern = r"\d{7,8}"
        date_format = "%d%m%Y"
        files = [f for f in glob(f"{self._path}/**.*") if f.endswith(".gpg")]
        if not files:
            raise AssertionError(f"Gpg archives not found in: {self._path}")
        target = files[0]
        first_found = re.search(date_pattern, target).group()
        target_date = datetime.strptime(first_found, date_format).date()
        for file in files:
            name, ext = path.splitext(path.basename(file))
            found = re.search(date_pattern, name).group()
            parsed_date = datetime.strptime(found, date_format).date()
            if parsed_date > target_date:
                target_date = parsed_date
                target = file
        self._file = target
        _logger.info(f"Last archive file: {self._file}")

    def _read_data(self) -> None:
        file = path.splitext(self._file)[0]
        assert os.path.isfile(file), "File not found"
        with open(file, "r", encoding='utf8') as f:
            self.__content = f.read().split("\n\n")
        os.remove(file)
        if os.path.exists(file):
            os.remove(file)

    def search(self, key: str) -> typing.List[str]:
        pattern = rf".*{key.lower()}.*[\t\n]"
        result = []
        for item in self.__content:
            if re.match(pattern, item.lower()):#, re.MULTILINE)
                result.append(item)
        return result

    def _unpack_gpg(self) -> None:
        # TODO unpack to the memory
        _logger.debug("Unpacking the last archive file...")
        command = f"gpg --no-symkey-cache {self._file}"
        system(command)

    def pack_gpg(self):
        pass
