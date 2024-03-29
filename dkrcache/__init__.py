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
import logging, os, pickle, re, time

log = logging.getLogger(__name__)
NORMAL = lambda o: o.exception() is None
ABRUPT = lambda o: o.exception() is not None
ALWAYS = lambda o: True
NEVER = lambda o: False

class NormalOutcome:

    def __init__(self, obj):
        self.obj = obj

    def result(self):
        return self.obj

    def exception(self):
        pass

class AbruptOutcome:

    def __init__(self, e):
        self.e = e

    def result(self):
        raise self.e

    def exception(self):
        return self.e

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

    log = log
    port = 41118
    sleeptime = .5

    def __init__(self, context, discriminator, task):
        self.context = os.path.abspath(context)
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

    def _imageornoneimpl(self, executor, handlercls, build):
        def bgtask():
            try:
                if build(check = bool):
                    return build.iid.read_text()
            finally:
                server.shutdown()
        with HTTPServer(('', self.port), handlercls) as server:
            return invokeall([server.serve_forever, executor.submit(bgtask).result])[1]

    def _imageornone(self, executor, handlercls):
        with self._builder() as build:
            build('--target', 'key')
            return self._retryport(partial(self._imageornoneimpl, executor, handlercls, build))

    def _outcomeornone(self, executor, handlercls, force):
        image = self._imageornone(executor, handlercls)
        if image is not None:
            with docker.run.__rm[partial](image) as f:
                outcome = pickle.load(f)
            drop = force(outcome)
            self.log.info("Cache hit%s: %s", ' and drop' if drop else '', image)
            if not drop:
                return outcome
            before = set(_pruneids())
            docker.rmi[print](image)
            # If our object is not in the set then nothing to be done, another process or user must have pruned it.
            # The user can docker builder prune at any time, so pruning too much here is not worse than that.
            for pruneid in set(_pruneids()) - before:
                docker.builder.prune._f[print]('--filter', f"id={pruneid}") # Idempotent.

    def run(self, force = NEVER, cache = NORMAL):
        with ThreadPoolExecutor() as executor:
            outcome = self._outcomeornone(executor, MissHandler, force)
            if outcome is not None:
                return outcome.result()
            try:
                outcome = NormalOutcome(self.task())
            except Exception as e:
                outcome = AbruptOutcome(e)
            if cache(outcome):
                self.log.info("Cached as: %s", self._imageornone(executor, partial(SaveHandler, outcome)))
            return outcome.result()

def _pruneids():
    for block in docker.buildx.du.__verbose().decode().split('\n\n'):
        obj = {k: v for l in block.splitlines() for k, v in [re.split(':\t+', l, 1)]}
        if 'false' == obj['Shared'] and 'mount / from exec /bin/sh -c wget localhost:$port' == obj['Description']:
            yield obj['ID']
