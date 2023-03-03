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

from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import local
import os, re, sys

mangled = re.compile('_.*(__.*[^_]_?)')
PYTHONPATH = os.pathsep.join(sys.path[1:]) # XXX: Include first entry?

def unmangle(name):
    m = mangled.fullmatch(name)
    return name if m is None else m.group(1)

@contextmanager
def atomic(path):
    path.parent.mkdir(parents = True, exist_ok = True)
    with TemporaryDirectory(dir = path.parent) as d:
        q = Path(d, f"{path.name}.part")
        yield q
        q.rename(path) # XXX: Or replace?

class threadlocalproperty:

    def __init__(self, default):
        self.local = local()
        self.default = default

    def __get__(self, obj, objtype):
        try:
            return self.local.lookup[obj]
        except (AttributeError, KeyError):
            return self.default

    def __set__(self, obj, value):
        try:
            lookup = self.local.lookup
        except AttributeError:
            self.local.lookup = lookup = {}
        lookup[obj] = value
