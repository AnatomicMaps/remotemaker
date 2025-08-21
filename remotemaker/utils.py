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

from http.client import HTTPConnection
import logging

#===============================================================================

import structlog

#===============================================================================

log_levels = logging.getLevelNamesMapping()

class LogLevelFilter:
    def __init__(self, min_level: int):
        self.__min_level = min_level

    def __call__(self, _, __, event_dict):
        level = log_levels.get(event_dict.get('level').upper(), logging.ERROR)
        if level >= self.__min_level:
            return event_dict
        raise structlog.DropEvent

#===============================================================================

logger = structlog.get_logger()

def configure_log(debug=False):
#==============================
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            LogLevelFilter(logging.DEBUG if debug else logging.INFO),
            structlog.contextvars.merge_contextvars,
            structlog.processors.MaybeTimeStamper('iso'),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
    if debug:
        HTTPConnection.debuglevel = 1
        requests_log = logging.getLogger("urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    global logger
    logger = structlog.get_logger()

#===============================================================================

def print_log(msg: str, data: dict):
#===================================
    struct_logger = structlog.get_logger()
    level = data.pop('level', 'error')
    try:
        log = struct_logger.__getattr__(level)
    except AttributeError:
        log = struct_logger.error
    log(msg, **data)

#===============================================================================
#===============================================================================
