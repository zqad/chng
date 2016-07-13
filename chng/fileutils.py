# chng - Deploy ATLauncher modpacks
#
# Copyright (C) 2016  Jonas Eriksson
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from unshortenit import unshorten
import urllib.parse
from pathlib import Path
import hashlib
import urllib.request
import requests
import logging

class DownloadException(Exception):
    pass
class DownloadableFile():
    def __init__(self, url, directory, md5sum=None, filename=None):
        self._url = url
        self._md5sum = md5sum

        if filename is None:
            # Make sure we know the correct url
            self._unshorten()

            # Use last part of url as filename
            parsed_url = urllib.parse.urlparse(url)
            path_parts = str(urllib.parse.unquote(parsed_url.path)).split("/")
            if len(path_parts) == 0 or path_parts[-1] is None \
                    or path_parts[-1] == "":
                raise DownloadException("Unable to figure out filename for %s"
                                        % (url,))
            filename = path_parts[-1]

        # Save the filename and the full path
        self._filename = filename
        self._path = Path(directory) / filename

    def _unshorten(self):
        # Unshorten any shorted urls
        if self._url.startswith("http://adf.ly"):
            new_url, status = unshorten(self._url)
            if not status == 200:
                raise DownloadException("Unable to unshorten url: '%s'"
                                        % (self._url,))
            self._url = new_url

    def ensure(self):
        # Create parent directory
        if not self._path.parent.exists():
            logging.info("Creating directory '%s'", self._path.parent)
            #3.5
            #self._path.parent.mkdir(mode=0o755, parents=True, exists_ok=True)
            self._path.parent.mkdir(mode=0o755, parents=True)

        # If the file exists, validate it
        if self._path.exists():
            if self._md5sum is not None:
                hasher = hashlib.md5()
                with self._path.open(mode='rb') as f:
                    while True:
                        hasher.update(f.read(1024*1024))
                        if f.eof():
                            break
                file_md5sum = hasher.hexdigest()
                if (file_md5sum == self._md5sum):
                    # All is well
                    logging.info("Hash ok for '%s', not downloading",
                                 self._path)
                    return
                else:
                    # There should not be any mismatches here, strange.
                    logging.warning("Hash mismatch for '%s' (expected: %s, got: %s) removing file",
                                    (self._path, self._md5sum, file_md5sum))
                    self._path.unlink()

        # Make sure that we don't use a link to a url shortener service
        self._unshorten()
        
        # Download the file
        headers = {}
        if self._md5sum is not None:
            headers['etag'] = self._md5sum
        logging.info("Downloading %s", self._url)
        request = requests.get(self._url, headers=headers)
        if not request.status_code == 200:
            logging.error("Unable to download url '%s'"
                                    % (self._url,))
            request.raise_for_status()

        # Write the file, and check the md5 checksum while doing it
        hasher = hashlib.md5()
        with self._path.open(mode='wb') as f:
            hasher.update(request.content)
            f.write(request.content)
        file_md5sum = hasher.hexdigest()

        # Check the ETag, if we got one from the server
        #etag = request.headers.get('etag')
        etag = None
        if (not etag is None) and etag != file_md5sum:
            self._path.unlink()
            raise DownloadException("ETag mismatch for '%s' (expected: %s, got: %s) removing file" %
                                    (self._url, etag, file_md5sum))

        # Check the md5sum, if we got one from the caller
        if not (self._md5sum is None or file_md5sum == self._md5sum):
            # The server did not serve the expected file, raise an error
            self._path.unlink()
            raise DownloadException("Hash mismatch for '%s' (expected: %s, got: %s) removing file" %
                                    (self._url, self._md5sum, file_md5sum))

from zipfile import ZipFile
from binascii import crc32
from pathlib import Path
import logging
class UnpackException(Exception):
    pass
class AutoUnpackableFile(DownloadableFile):
    def __init__(self, url, directory, pack_format=None, md5sum=None,
                 filename=None):
        super().__init__(url, directory, md5sum, filename)

        # Create unpack handlers dict
        self._unpack_handlers = {
            'none': None,
            'zip': self._unpack_zip,
        }

        # Figure out / validate and save pack_format
        if pack_format == None:
            filename_parts = self._filename.split(".")
            if len(filename_parts) == 0 or \
                    not filename_parts[-1] in self._unpack_handlers:
                logging.debug("Unable to figure out packing scheme for %s, assuming no packing",
                              (self._filename,))
                pack_format = "none"
            else:
                pack_format = filename_parts[-1]
        elif not pack_format in self._unpack_handlers:
            raise UnpackException("Unsupported packing format %s for %s" %
                                  (pack_format, url)) 
        self._pack_format = pack_format

        # Save the directory
        self._dest_path = self._path.parent
        # Rewrite the download path to make sure packed files are saved in
        # the .packed directory
        if not pack_format == "none":
            self._path = self._path.parent / ".packed" / self._path.name

    def ensure(self):
        # Take care of the download
        super().ensure()

        # Call the unpack handler
        handler = self._unpack_handlers[self._pack_format]
        if handler is not None:
            handler()

    @staticmethod
    def _get_crc32(path):
        with path.open('rb') as f:
            crc = 0
            while True:
                data = f.read(1024*1024)
                if data == b'':
                    break
                crc = crc32(data, crc)
            return crc & 0xFFFFFFFF

    def _unpack_zip(self):
        with ZipFile(str(self._path), 'r') as f:
            logging.debug("In %s", self._path)
            for info in f.infolist():
                file_path = self._dest_path / Path(info.filename)
                extract = False
                logging.debug("Checking out %s", info.filename)
                if info.filename.endswith("/"):
                    if not file_path.exists():
                        file_path.mkdir(mode=0o755, parents=True)
                else:
                    if file_path.exists():
                        # Check crc of file on disk
                        file_crc = self._get_crc32(file_path)
                        if info.CRC != file_crc:
                            extract = True
                    else:
                        extract = True

                # Time to extract?
                if extract:
                    to = str(self._dest_path)
                    logging.debug("Extracting %s to %s", info.filename, to)
                    f.extract(info, to)
