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

class GoodResult:

    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

class BadResult:

    def __init__(self, exception):
        self.exception = exception

    def get(self):
        raise self.exception

class ExpensiveTask:

    port = 41118
    sleeptime = .5

    class FailHandler(BaseHTTPRequestHandler):

        def do_GET(self):
            self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, 'Cache miss')

    class SaveHandler(BaseHTTPRequestHandler):

        def __init__(self, result, *args, **kwargs):
            self.result = result
            super().__init__(*args, **kwargs)

        def do_GET(self):
            self.send_response(HTTPStatus.OK)
            self.end_headers()
            pickle.dump(self.result, self.wfile)

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

    def _httpget(self, build, shutdown):
        try:
            if build(check = bool):
                return build.iid.read_text()
        finally:
            shutdown()

    def _retrying(self, f):
        while True:
            try:
                return f()
            except OSError as e:
                if EADDRINUSE != e.errno:
                    raise
            log.debug("Port %s unavailable, sleep for %s seconds.", self.port, self.sleeptime)
            time.sleep(self.sleeptime)

    def run(self):
        def tryresult(handlercls):
            def imageornone():
                with HTTPServer(('', self.port), handlercls) as server:
                    return invokeall([server.serve_forever, executor.submit(self._httpget, build, server.shutdown).result])[-1]
            with self._builder() as build:
                build('--target', 'base')
                image = self._retrying(imageornone)
            if image is not None:
                with docker.run.__rm[partial](image) as f:
                    return pickle.load(f)
        with ThreadPoolExecutor() as executor:
            result = tryresult(self.FailHandler)
            if result is not None:
                log.info('Cache hit.')
                return result.get()
            try:
                result = GoodResult(self.task())
            except Exception as e:
                result = BadResult(e)
            return tryresult(partial(self.SaveHandler, result)).get()
