#===============================================================================
#
#  Remote flatmap maker
#
#  Copyright (c) 2024 - 2025 David Brooks
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

__version__ = '0.2.1'

#===============================================================================

from datetime import datetime
import json
import logging
from time import sleep
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse

#===============================================================================

import requests
import websockets.sync.client

#===============================================================================
#===============================================================================

REMOTE_TIMEOUT = (10, 30)     # (connection, read) timeout in seconds

LOG_ENDPOINT  = 'make/log'
MAKE_ENDPOINT = 'make/map'
WS_LOG_ENDPOINT = 'make/maker-log'

RUNNING_POLL_TIME =  1
WS_RECV_POLL_TIME =  1
WS_IDLE_POLL_TIME =  0.01

# See https://iximiuz.com/en/posts/reverse-proxy-http-keep-alive-and-502s/ with
# comment ``Employ HTTP 5xx retries on the client-side (well, they are often a must-have anyway)``
MAX_REQUEST_RETRIES = 5

#===============================================================================

def ws_server(server: str) -> str:
#=================================
    parts = urlparse(server)
    if parts.scheme == 'https':
        return urlunparse(parts._replace(scheme='wss'))
    else:
        return urlunparse(parts._replace(scheme='ws'))

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
        self.__ws_server = ws_server(server)
        self.__websocket = None
        self.__token = token
        self.__process = None
        self.__poll_time = QUEUED_POLL_TIME
        self.__uuid = None
        self.__print_log = False

        self.__remote_map: dict[str, Any] = {
            'source': source,
            'manifest': manifest
        }
        if commit is not None:
            self.__remote_map['commit'] = commit
        if force:
            self.__remote_map['force'] = True

    @property
    def uuid(self):
        return self.__uuid

    def __request(self, endpoint: str, data: Optional[dict]=None):
    #=============================================================
        server_endpoint = f'{self.__server}/{endpoint}'
        headers = {
            'Authorization': f'Bearer {self.__token}'
        }
        logging.debug(f'REQ: {server_endpoint}{f" {str(data)}" if data is not None else ""} at {datetime.now()}')
        retries = 0
        response = None
        while retries < MAX_REQUEST_RETRIES:
            try:
                if data is None:
                    response = requests.get(server_endpoint, headers=headers, timeout=REMOTE_TIMEOUT)
                else:
                    response = requests.post(server_endpoint, headers=headers, json=data, timeout=REMOTE_TIMEOUT)
            except (requests.ConnectTimeout, requests.ReadTimeout):
                continue
            logging.debug(f'RSP: {response.status_code} {response.text} at {datetime.now()}')
            if response.status_code not in [502, 503, 504]:
                break
            sleep(0.1)
            retries += 1
        if response is None:
            raise IOError(f'Timed out: No response from {server_endpoint} after {MAX_REQUEST_RETRIES} retries')
        response.raise_for_status()
        try:
            return response.json()
        except json.JSONDecodeError:
            raise TypeError(f'Invalid JSON returned from server: {response.text}')

    def __check_and_print_log_line(self, log_data: dict):
    #====================================================
        if log_data.get('level') == 'critical' and log_data.get('msg', '') == 'Mapmaker succeeded':
            self.__uuid = log_data.get('uuid')
        if self.__print_log:
            print(log_data)

    def __check_and_print_log(self, response: dict):
    #===============================================
        self.__status = response['status']
        log_data = response.get('log', '')
        if self.__status == MakerStatus.QUEUED:
            logging.info(REQUEST_QUEUED_MSG)
        elif self.__websocket is None:
            self.__poll_time = RUNNING_POLL_TIME
        if log_data != '':
            if self.__websocket is None:
                log_lines = log_data.strip().split('\n')
                for line in log_lines:
                    self.__check_and_print_log_line(json.loads(line))
            else:
                self.__check_and_print_log_line(log_data)
        if self.__status == MakerStatus.UNKNOWN:
            raise IOError(f'Unexpected response: {str(response)}')

    def __check_websockets(self):
    #============================
        return
    '''
        if self.__websocket is None:
            ws_log_endpoint = f'{self.__ws_server}/{WS_LOG_ENDPOINT}'
            try:
                self.__websocket = websockets.sync.client.connect(ws_log_endpoint, ping_timeout=None)
            except Exception as e:
                if self.__print_log:
                    print('WS:', str(e))
    '''

    def __close_websocket(self):
    #===========================
        if self.__websocket is not None:
            self.__websocket.close()
            self.__websocket = None

    def __receive_json(self, timeout=WS_RECV_POLL_TIME):
    #===================================================
        if self.__websocket is not None:
            try:
                data = self.__websocket.recv(timeout=timeout)
                return json.loads(data)
            except websockets.exceptions.ConnectionClosedOK:
                self.__websocket = None
            except TimeoutError:
                pass

    def __send_json(self, data):
    #========================
        if self.__websocket is not None:
            self.__websocket.send(json.dumps(data))

    def __poll_for_status_and_log(self):
    #===================================
        self.__check_websockets()
        if self.__websocket is None:
            while self.__status not in FINISHED_STATUS:
                response = self.__request(f'{LOG_ENDPOINT}/{self.__process}')
                self.__check_and_print_log(response)
                sleep(self.__poll_time)
        else:
            response = self.__receive_json()
            if response is None or response.get('status') != 'connected':
                self.__close_websocket()
                return
            self.__send_json({
                'type': 'status',
                'id': self.__process
            })
            self.__poll_time = WS_IDLE_POLL_TIME
            while self.__status not in FINISHED_STATUS:
                response = self.__receive_json(timeout=0)
                if response is not None:
                    self.__check_and_print_log(response)
                    if self.__status == MakerStatus.QUEUED:
                        self.__close_websocket()
                        return
                elif self.__websocket is None:
                    return          # Connection has been closed
                sleep(self.__poll_time)

    def __connect(self) -> bool:
    #===========================
        response = self.__request(MAKE_ENDPOINT, self.__remote_map)
        self.__status = response['status']
        if self.__status not in INITIAL_STATUS:
            raise IOError('Unexpected initial status')
        elif self.__status == MakerStatus.QUEUED:
            return False
        self.__process = response['id']
        return True

    def run(self, print_log=False) -> bool:
    #======================================
        self.__print_log = print_log
        if self.__connect():
            self.__poll_for_status_and_log()
            return True
        return False

#===============================================================================
#===============================================================================
