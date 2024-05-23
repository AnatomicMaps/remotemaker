#===============================================================================
#
#  Remote flatmap maker
#
#  Copyright (c) 2024  David Brooks
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#===============================================================================

import argparse
from http.client import HTTPConnection
import json
import logging
import sys
from time import sleep
from typing import Any, Optional

#===============================================================================

import requests

#===============================================================================

try:
    from . import __version__
except ImportError:
    from __init__ import __version__

#===============================================================================

REMOTE_TIMEOUT = (10, 30)     # (connection, read) timeout in seconds

LOG_ENDPOINT  = 'make/log'
MAKE_ENDPOINT = 'make/map'

QUEUED_POLL_TIME  = 20
RUNNING_POLL_TIME =  1

REQUEST_QUEUED_MSG = f'Request queued as other map(s) being made. Will retry in {QUEUED_POLL_TIME} seconds'

# See https://iximiuz.com/en/posts/reverse-proxy-http-keep-alive-and-502s/ with
# comment ``Employ HTTP 5xx retries on the client-side (well, they are often a must-have anyway)``
MAX_PROXY_RETRIES = 5

#===============================================================================

class MakerStatus:
    QUEUED = 'queued'
    RUNNING = 'running'
    TERMINATED = 'terminated'
    ABORTED = 'aborted'
    UNKNOWN = 'unknown'

INITIAL_STATUS = [
    MakerStatus.QUEUED,
    MakerStatus.RUNNING
]

RUNNING_STATUS = [
    MakerStatus.RUNNING
]

FINISHED_STATUS = [
    MakerStatus.TERMINATED,
    MakerStatus.ABORTED
]

#===============================================================================

class RemoteMaker:
    def __init__(self, server: str, token: str, source: str, manifest: str, commit: Optional[str]=None, force: Optional[bool]=False):
        self.__server = server
        self.__token = token
        remote_map: dict[str, Any] = {
            'source': source,
            'manifest': manifest
        }
        if commit is not None:
            remote_map['commit'] = commit
        if force:
            remote_map['force'] = True
        response = self.__request(MAKE_ENDPOINT, remote_map)
        self.__status = response['status']
        if self.__status not in INITIAL_STATUS:
            raise IOError('Unexpected initial status')
        elif self.__status == MakerStatus.QUEUED:
            logging.info(REQUEST_QUEUED_MSG)
        self.__process = response['process']
        self.__last_log_line = 0
        self.__poll_time = QUEUED_POLL_TIME if response['status'] == MakerStatus.QUEUED else RUNNING_POLL_TIME

    def __request(self, endpoint: str, data: Optional[dict]=None):
    #=============================================================
        server_endpoint = f'{self.__server}/{endpoint}'
        headers = {
            'Authorization': f'Bearer {self.__token}'
        }
        logging.debug(f'REQ: {server_endpoint}{f" {str(data)}" if data is not None else ""}')
        retries = 0
        while retries < MAX_PROXY_RETRIES:
            if data is None:
                response = requests.get(server_endpoint, headers=headers, timeout=REMOTE_TIMEOUT)
            else:
                response = requests.post(server_endpoint, headers=headers, json=data, timeout=REMOTE_TIMEOUT)
            logging.debug(f'RSP: {response.status_code} {response.text}')
            if response.status_code not in [502, 503, 504]:
                break
            sleep(0.1)
            retries += 1
        response.raise_for_status()
        try:
            return response.json()
        except json.JSONDecodeError:
            raise TypeError(f'Invalid JSON returned from server: {response.text}')

    def __check_and_print_log(self):
    #===============================
        response = self.__request(f'{LOG_ENDPOINT}/{self.__process}/{self.__last_log_line+1}')
        self.__status = response['status']
        log_data = response.get('log', '')
        if self.__status == MakerStatus.QUEUED:
            logging.info(REQUEST_QUEUED_MSG)
        else:
            self.__poll_time = RUNNING_POLL_TIME
        if log_data != '':
            log_lines = log_data.strip()
            print(log_lines)
            self.__last_log_line += len(log_lines.split('\n'))
        if self.__status == MakerStatus.UNKNOWN:
            logging.info(f'Unknown: {str(response)}')
            raise IOError('Unexpected response')

    def run(self):
    #=============
        while self.__status not in FINISHED_STATUS:
            self.__check_and_print_log()
            sleep(self.__poll_time)
        # Delete process record on server
        self.__request(f'{LOG_ENDPOINT}/{self.__process}/{self.__last_log_line+1}')
        return self.__status == MakerStatus.TERMINATED

#===============================================================================

def parse_args():
#================
    parser = argparse.ArgumentParser(description='Make a flatmap on a remote map server.')
    parser.add_argument('-v', '--version', action='version', version=__version__)
    parser.add_argument('--debug', action='store_true',
                        help='Trace requests to remote server')
    server = parser.add_argument_group('Remote server')
    server.add_argument('--server', required=True,
                        help='The URL of flatmap server')
    server.add_argument('--token', required=True,
                        help='The authorisation token of the flatmap server')
    source = parser.add_argument_group('Flatmap source')
    source.add_argument('--source', required=True,
                        help='The URL of a Git repository with flatmap sources')
    source.add_argument('--manifest', metavar='MANIFEST_PATH', required=True,
                        help='The relative path of the manifest in the source repository')
    source.add_argument('--commit', metavar='GIT_COMMIT',
                        help='The branch/tag/commit to use')
    parser.add_argument('--force', action='store_true',
                        help='Make the map regardless of whether it already exists')
    return parser.parse_args()

def configure_log(debug=False):
#==============================
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        level=logging.DEBUG if debug else logging.INFO)
    if debug:
        HTTPConnection.debuglevel = 1
        requests_log = logging.getLogger("urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

def main():
#==========
    args = parse_args()
    configure_log(args.debug)
    remote_maker = RemoteMaker(args.server, args.token, args.source, args.manifest, args.commit, args.force)
    if not remote_maker.run():
        sys.exit(1)

#===============================================================================

if __name__ == '__main__':
    main()

#===============================================================================
