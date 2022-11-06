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
import re

mangled = re.compile('_.*(__.*[^_]_?)')

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
