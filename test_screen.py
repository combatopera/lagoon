# Copyright 2018, 2019 Andrzej Cichocki

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

from screen import Stuff, screenenv
from pathlib import Path
from contextlib import contextmanager
import unittest, subprocess, tempfile

stufftemplate = r'''plain old line
do not interpolate any of these: $USER ${USER} '$USER' '${USER}' x
none of these are tab: ^I \t '^I' '\t' x
some interesting cases: $ ^ \ '$' '^' '\' x
'''
stufftemplate += """bit of unicode: \u20ac x
double quote against letter: "Z x
arbitrary text: %s x
"""
basestufftext = stufftemplate % ''

class TestScreen(unittest.TestCase):

    maxDiff = None

    @contextmanager
    def _session(self):
        session = self.dirpath.name
        logpath = self.dirpath / 'log'
        fifopath = self.dirpath / 'fifo'
        command = ['bash', '-c', 'cat "$1" - >"$2"', 'cat', str(fifopath), str(logpath)]
        subprocess.check_call(['mkfifo', str(fifopath)])
        screen = subprocess.Popen(['screen', '-S', session, '-d', '-m'] + command, env = screenenv('DUB_QUO'))
        with fifopath.open('w') as f:
            print('consume this', file = f)
        stuff = Stuff(session, '0', 'DUB_QUO')
        yield logpath, stuff
        stuff.eof()
        self.assertEqual(0, screen.wait())
        with logpath.open() as f:
            self.assertEqual(self.expected, f.read().splitlines())

    def setUp(self):
        self.expected = ['consume this']
        self._tempdir = tempfile.TemporaryDirectory()
        self.dirpath = Path(self._tempdir.name)

    def tearDown(self):
        self._tempdir.cleanup()

    def test_escaping(self):
        with self._session() as (logpath, stuff):
            stuff(basestufftext)
            self.expected += basestufftext.splitlines()

    def test_largetext(self):
        with self._session() as (logpath, stuff):
            basesize = sum(len(a) for a in stuff.toatoms(basestufftext))
            for mul in 1, 2:
                for extra in 0, 1:
                    stufftext = stufftemplate % ('A' * (Stuff.buffersize * mul + extra - basesize))
                    stuff(stufftext)
                    self.expected += stufftext.splitlines()

    def test_splitescapesequence(self):
        text = 'x' * (Stuff.buffersize - 1) + '$'
        with self._session() as (logpath, stuff):
            stuff(text)
            self.expected.append(text)

    def test_printable(self):
        printable = ''.join(chr(x) for x in range(ord(' '), ord('~') + 1))
        self.assertEqual(95, len(printable))
        while len(printable) <= Stuff.buffersize:
            printable *= 2
        with self._session() as (logpath, stuff):
            stuff(printable)
            self.expected.append(printable)
