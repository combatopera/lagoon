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

stufftext = r'''plain old line
do not interpolate any of these: $USER ${USER} '$USER' '${USER}' x
none of these are tab: ^I \t '^I' '\t' x
some interesting cases: $ ^ \ '$' '^' '\' x
'''

class TestScreen(unittest.TestCase):

    maxDiff = None

    @contextmanager
    def _session(self, dirpath):
        dirpath = Path(dirpath)
        session = dirpath.name
        logpath = dirpath / 'log'
        fifopath = dirpath / 'fifo'
        subprocess.check_call(['mkfifo', str(fifopath)])
        screen = subprocess.Popen([
                'screen', '-S', session, '-L', str(logpath), '-d', '-m', 'cat', str(fifopath), '-'])
        with fifopath.open('w') as f:
            print('consume this', file = f)
        stuff = Stuff(session, '0')
        yield logpath, stuff
        stuff.eof()
        self.assertEqual(0, screen.wait())

    def test_escaping(self):
        with tempfile.TemporaryDirectory() as dirpath:
            with self._session(dirpath) as (logpath, stuff):
                stuff(stufftext)
            expected = ['consume this'] + stufftext.splitlines() * 2
            with logpath.open() as f:
                self.assertEqual(expected, f.read().splitlines())

    def test_largetext(self):
        pass # TODO: Implement me.
