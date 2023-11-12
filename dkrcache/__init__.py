# Copyright 2018, 2019, 2020 Andrzej Cichocki

# This file is part of lagoon.
#
# lagoon is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# lagoon is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with lagoon.  If not, see <http://www.gnu.org/licenses/>.

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from diapyr.util import invokeall
from errno import EADDRINUSE
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from lagoon.binary import docker, tar
from lagoon.util import mapcm
from pathlib import Path
from pkg_resources import resource_string
from tempfile import TemporaryDirectory
import logging, pickle, time

log = logging.getLogger(__name__)

class NormalOutcome:

    def __init__(self, obj):
        self.obj = obj

    def get(self):
        return self.obj

class AbruptOutcome:

    def __init__(self, e):
        self.e = e

    def get(self):
        raise self.e

class MissHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, 'Cache miss')

class SaveHandler(BaseHTTPRequestHandler):

    def __init__(self, outcome, *args, **kwargs):
        self.outcome = outcome
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.send_response(HTTPStatus.OK)
        self.end_headers()
        pickle.dump(self.outcome, self.wfile)

class ExpensiveTask:

    port = 41118
    sleeptime = .5

    def __init__(self, context, discriminator, task):
        self.context = context
        self.discriminator = discriminator
        self.task = task

    @contextmanager
    def _builder(self):
        def build(*args, **kwargs):
            with tar.c._zh[partial]('-C', tempdir, 'Dockerfile', 'context') as f: # XXX: Impact of following all symlinks?
                return docker.build.__network.host.__quiet[print]('--iidfile', iid, '--build-arg', f"discriminator={self.discriminator}", '--build-arg', f"port={self.port}", f, *args, **kwargs)
        with mapcm(Path, TemporaryDirectory()) as tempdir:
            (tempdir / 'Dockerfile').write_bytes(resource_string(__name__, 'Dockerfile.dkr'))
            (tempdir / 'context').symlink_to(self.context)
            build.iid = iid = tempdir / 'iid'
            yield build

    def _retryport(self, openport):
        while True:
            try:
                return openport()
            except OSError as e:
                if EADDRINUSE != e.errno:
                    raise
            log.debug("Port %s unavailable, sleep for %s seconds.", self.port, self.sleeptime)
            time.sleep(self.sleeptime)

    def _imageornone(self, executor, handlercls, build):
        def bgtask():
            try:
                if build(check = bool):
                    return build.iid.read_text()
            finally:
                server.shutdown()
        with HTTPServer(('', self.port), handlercls) as server:
            return invokeall([server.serve_forever, executor.submit(bgtask).result])[1]

    def _outcomeornone(self, executor, handlercls):
        with self._builder() as build:
            build('--target', 'key')
            image = self._retryport(partial(self._imageornone, executor, handlercls, build))
        if image is not None:
            with docker.run.__rm[partial](image) as f:
                return pickle.load(f)

    def run(self):
        with ThreadPoolExecutor() as executor:
            outcome = self._outcomeornone(executor, MissHandler)
            if outcome is not None:
                log.info('Cache hit.')
                return outcome.get()
            try:
                outcome = NormalOutcome(self.task())
            except Exception as e:
                outcome = AbruptOutcome(e)
            return self._outcomeornone(executor, partial(SaveHandler, outcome)).get()
