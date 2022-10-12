# SPDX-FileCopyrightText: 2022 Contributors to the Power Grid Model IO project <dynamic.grid.calculation@alliander.com>
#
# SPDX-License-Identifier: MPL-2.0
"""
Helper functions to download (and store) files from the internet
"""

import hashlib
from pathlib import Path
from tempfile import gettempdir
from typing import ByteString, Callable, Optional
from urllib import request

import structlog
import tqdm


def download(
    url: str, file_path: Optional[Path] = None, dir_path: Optional[Path] = None, overwrite: bool = False
) -> Path:
    """
    Download a file from a URL and store it locally

    Args:
        url:       The url to the file
        file_path: An optional file path (absolute or relative to dir_path). If no file_path is given, a file name is
                   generated based on the url
        dir_path:  An optional dir path to store the downloaded file. If no dir_path is given the system's temp dir will
                   be used. Use Path(".") if you intend to use the current working directory.
        overwrite: Should we download the file, even if we have downloaded already (and the file size still matches)?

    Returns:
        The path to the downloaded file
    """
    log = structlog.get_logger(__name__)
    file_path = get_download_path(dir_path=dir_path, file_path=file_path, data=url.encode())

    if file_path.is_file():
        if overwrite:
            log.debug("Forced re-downloading existing file", url=url, file_path=file_path)
        else:
            current_size = get_url_size(url=url)
            previous_size = file_path.stat().st_size
            if previous_size == current_size:
                log.debug("Skip downloading existing file", url=url, file_path=file_path)
                return file_path
            log.debug(
                "Re-downloading existing file, because the size has changed",
                url=url,
                file_path=file_path,
                previous_size=previous_size,
                current_size=current_size,
            )
    else:
        log.debug("Downloading file", url=url, file_path=file_path)

    def progress_hook(progress_bar: tqdm.tqdm) -> Callable[[int, int, int], None]:
        last_block = [0]

        def update_progress_bar(block_num: int, block_size: int, file_size: int) -> None:
            if file_size > 0:
                progress_bar.total = file_size
            progress_bar.update((block_num - last_block[0]) * block_size)
            last_block[0] = block_num

        return update_progress_bar

    # Download to a temp file first, so the results are not stored if the transfer fails
    with tqdm.tqdm(unit="B", unit_scale=True, desc=url, leave=True) as progress_bar:
        temp_file, _headers = request.urlretrieve(url, reporthook=progress_hook(progress_bar))

    # Check if the file contains any content
    temp_path = Path(temp_file)
    if temp_path.stat().st_size == 0:
        log.warning("Downloaded an empty file", url=url, file_path=file_path)

    # Move the file to it's final destination
    file_path.unlink(missing_ok=True)
    temp_path.rename(file_path)
    log.debug("Downloaded file", url=url, file_path=file_path, file_size=file_path.stat().st_size)

    return file_path


def get_url_size(url: str) -> int:
    """
    Retrieve the file size of a given URL (based on it's header)

    Args:
        url: The url to the file

    Return:
        The file size in bytes
    """
    return int(request.urlopen(url).headers["Content-Length"])


def get_download_path(dir_path: Optional[Path], file_path: Optional[Path], data=Optional[ByteString]) -> Path:
    """
    Determine the file path based on dir_path, file_path and/or data

    Args:
        dir_path:  An optional dir path to store the downloaded file. If no dir_path is given the system's temp dir will
                   be used. Use Path(".") if you intend to use the current working directory.
        file_path: An optional file path (absolute or relative to dir_path). If no file_path is given, a file name is
                   generated based on the url
        data:      A bytestring that can be used to generate a filename.
    """
    # If no file_path is given, generate a file name
    if file_path is None:
        if data is None:
            raise ValueError(f"Can't auto generate a file name for a {type(data).__name__}.")
        try:
            md5 = hashlib.md5()
            md5.update(data)
            hash_str = md5.hexdigest()
        except (TypeError, ValueError) as ex:
            raise ValueError(f"Can't auto generate a file name for a {type(data).__name__}.") from ex
        file_path = Path(f"{__name__}.{hash_str}")

    # If no dir_path is given, use the system's temp dir
    if dir_path is None:
        dir_path = Path(gettempdir())

    # Prefix the file_path and allow special path characters like ~
    file_path = dir_path.expanduser() / file_path

    # If the file_path exists, it should be a file (not a dir)
    if file_path.exists() and not file_path.is_file():
        raise ValueError(f"Invalid file path: {file_path}")

    return file_path.absolute()
