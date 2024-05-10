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
import json
import logging
import sys
from time import sleep
from typing import Optional

#===============================================================================

import requests

#===============================================================================

from . import __version__

#===============================================================================

REMOTE_TIMEOUT = (10, 30)     # (connection, read) timeout in seconds

LOG_ENDPOINT  = 'make/log'
MAKE_ENDPOINT = 'make/map'

QUEUED_POLL_TIME  = 20
RUNNING_POLL_TIME = 10

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
    def __init__(self, server: str, token: str, source: str, manifest: str, commit: Optional[str]=None):
        self.__server = server
        self.__token = token
        remote_map = {
            'source': source,
            'manifest': manifest
        }
        if commit is not None:
            remote_map['commit'] = commit
        response = self.__request(MAKE_ENDPOINT, remote_map)
        logging.info(f'Request: {str(response)}')
        self.__status = response['status']
        if self.__status not in INITIAL_STATUS:
            raise IOError('Unexpected initial status')
        self.__process = response['process']
        self.__last_log_line = 0
        self.__poll_time = QUEUED_POLL_TIME if response['status'] == MakerStatus.QUEUED else RUNNING_POLL_TIME

    def __request(self, endpoint: str, data: Optional[dict]=None):
    #=============================================================
        server_endpoint = f'{self.__server}/{endpoint}'
        headers = {
            'Authorization': f'Bearer {self.__token}'
        }
        if data is None:
            response = requests.get(server_endpoint, headers=headers, timeout=REMOTE_TIMEOUT)
        else:
            response = requests.post(server_endpoint, headers=headers, json=data, timeout=REMOTE_TIMEOUT)
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
        if self.__status != MakerStatus.QUEUED:
            self.__poll_time = RUNNING_POLL_TIME
        if log_data != '':
            print(log_data.strip())
            self.__last_log_line += len(log_data.split('\n'))
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
    return parser.parse_args()

def configure_log():
#===================
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)

def main():
#==========
    configure_log()
    args = parse_args()
    remote_maker = RemoteMaker(args.server, args.token, args.source, args.manifest, args.commit)
    if not remote_maker.run():
        sys.exit(1)

#===============================================================================

if __name__ == '__main__':
    main()

#===============================================================================
