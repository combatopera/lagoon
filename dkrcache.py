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
from diapyr.util import invokeall
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from lagoon.binary import docker, tar
from lagoon.util import mapcm
from pathlib import Path
from tempfile import TemporaryDirectory
import logging, pickle

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

class CacheMissException(Exception): pass

class ExpensiveTask:

    port = 41118 # TODO LATER: Ideally use any available port.

    class FailHandler(BaseHTTPRequestHandler):

        def do_GET(self):
            self.send_response(HTTPStatus.SERVICE_UNAVAILABLE, 'Cache miss')
            self.end_headers()

    class SaveHandler(BaseHTTPRequestHandler):

        def __init__(self, result, *args, **kwargs):
            self.result = result
            super().__init__(*args, **kwargs)

        def do_GET(self):
            self.send_response(HTTPStatus.OK)
            self.end_headers()
            self.wfile.write(pickle.dumps(self.result))

    def __init__(self, context, discriminator, task):
        self.context = context
        self.discriminator = discriminator
        self.task = task

    def _httpget(self, shutdown):
        def build(*args, **kwargs):
            with tar.c._zh[partial]('-C', tempdir, 'Dockerfile', 'context') as f: # XXX: Impact of following all symlinks?
                return docker.build.__network.host[print]('--build-arg', f"discriminator={self.discriminator}", f, *args, **kwargs)
        try:
            with mapcm(Path, TemporaryDirectory()) as tempdir:
                (tempdir / 'Dockerfile').write_text(f"""FROM busybox:1.36 AS base
WORKDIR /io
COPY context context
ARG discriminator

FROM base AS task
RUN wget localhost:{self.port}

FROM task
CMD cat index.html
""")
                (tempdir / 'context').symlink_to(self.context)
                build('--target', 'base')
                if build('--target', 'task', check = False):
                    raise CacheMissException
                iid = tempdir / 'iid'
                build('--iidfile', iid)
                return pickle.loads(docker.run.__rm(iid.read_text()))
        finally:
            shutdown()

    def run(self):
        def tryresult(handlercls):
            with HTTPServer(('', self.port), handlercls) as server:
                return invokeall([server.serve_forever, e.submit(self._httpget, server.shutdown).result])[-1]
        with ThreadPoolExecutor() as e:
            try:
                result = tryresult(self.FailHandler)
            except CacheMissException:
                pass
            else:
                return result.get()
            try:
                result = GoodResult(self.task())
            except BaseException as x:
                result = BadResult(x)
            return tryresult(partial(self.SaveHandler, result)).get()
