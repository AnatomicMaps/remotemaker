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

import argparse
import sys
from time import sleep

#===============================================================================

from remotemaker import __version__, RemoteMaker
from remotemaker.utils import logger

#===============================================================================

REQUEST_REPLY_TIME  = 20
REQUEST_QUEUED_MSG = f'Request denied as other map(s) being made. Will retry in {REQUEST_REPLY_TIME} seconds.'

#===============================================================================

def parse_args():
#================
    parser = argparse.ArgumentParser(description='Make a flatmap on a remote map server.')
    parser.add_argument('-v', '--version', action='version', version=__version__)
    parser.add_argument('--debug', action='store_true',
                        help='Trace requests to remote server')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help="Don't print log messages from maker process")
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

def main():
#==========
    args = parse_args()
    try:
        remote_maker = RemoteMaker(args.server, args.token, args.source, args.manifest,
                                   args.commit, args.force, args.debug)
        while not remote_maker.run(print_log=not args.quiet):
            logger.info(REQUEST_QUEUED_MSG)
            sleep(REQUEST_REPLY_TIME)
    except Exception as e:
        logger.exception(str(e), exc_info=True)
        sys.exit(1)

#===============================================================================

if __name__ == '__main__':
    main()

#===============================================================================
#===============================================================================
