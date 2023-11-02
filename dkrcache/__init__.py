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
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from lagoon import docker
from pathlib import Path
from tempfile import TemporaryDirectory
import logging

log = logging.getLogger(__name__)

def runexpensivetask(context, discriminator, task, port = 41118):
    def httpget():
        try:
            with TemporaryDirectory() as tempdir:
                Path(tempdir, 'Dockerfile').write_text(f"""FROM busybox
ARG discriminator
RUN wget -O - localhost:{port}
""")
                return docker.build.__network.host[print, bool]('--build-arg', f"discriminator={discriminator}", tempdir)
        finally:
            server.shutdown()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            try:
                task()
            except:
                log.exception('Failed:')
                self.send_error(555, 'Task Failed')
            else:
                self.send_response(HTTPStatus.OK)
                self.end_headers()
    with HTTPServer(('', port), Handler) as server, ThreadPoolExecutor() as e:
        return invokeall([server.serve_forever, e.submit(httpget).result])[-1]
