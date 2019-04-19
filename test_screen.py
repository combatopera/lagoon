# Copyright 2018 Andrzej Cichocki

# This file is part of system.
#
# system is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# system is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with system.  If not, see <http://www.gnu.org/licenses/>.

from screen import Stuff
from pathlib import Path
from contextlib import contextmanager
import unittest, subprocess, tempfile

stufftemplate = r'''plain old line
do not interpolate any of these: $USER ${USER} '$USER' '${USER}' x
none of these are tab: ^I \t '^I' '\t' x
some interesting cases: $ ^ \ '$' '^' '\' x
'''
stufftemplate += """bit of unicode: \u20ac x
arbitrary text: %s x
"""
basestufftext = stufftemplate % ''
basesize = len(Stuff.todata(basestufftext))

class TestScreen(unittest.TestCase):

    maxDiff = None

    @contextmanager
    def _session(self, dirpath):
        dirpath = Path(dirpath)
        session = dirpath.name
        logpath = dirpath / 'log'
        fifopath = dirpath / 'fifo'
        command = ['bash', '-c', 'cat "$1" - >"$2"', 'cat', str(fifopath), str(logpath)]
        subprocess.check_call(['mkfifo', str(fifopath)])
        screen = subprocess.Popen(['screen', '-S', session, '-d', '-m'] + command)
        with fifopath.open('w') as f:
            print('consume this', file = f)
        stuff = Stuff(session, '0')
        yield logpath, stuff
        stuff.eof()
        self.assertEqual(0, screen.wait())

    def setUp(self):
        self.expected = ['consume this']

    def test_escaping(self):
        with tempfile.TemporaryDirectory() as dirpath:
            with self._session(dirpath) as (logpath, stuff):
                stuff(basestufftext)
                self.expected += basestufftext.splitlines()
            with logpath.open() as f:
                self.assertEqual(self.expected, f.read().splitlines())

    def test_largetext(self):
        with tempfile.TemporaryDirectory() as dirpath:
            with self._session(dirpath) as (logpath, stuff):
                for mul in 1, 2:
                    for extra in 0, 1:
                        stufftext = stufftemplate % ('A' * (Stuff.buffersize * mul + extra - basesize))
                        stuff(stufftext)
                        self.expected += stufftext.splitlines()
            with logpath.open() as f:
                self.assertEqual(self.expected, f.read().splitlines())
