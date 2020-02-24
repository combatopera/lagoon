# Copyright 2018, 2019 Andrzej Cichocki

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

from pathlib import Path
from subprocess import CalledProcessError
import os, unittest

class TestLagoon(unittest.TestCase):

    def test_nosuchprogram(self):
        def imp():
            from . import thisisnotanexecutable
            del thisisnotanexecutable
        self.assertRaises(ImportError, imp)

    def test_false(self):
        from . import false
        false(check = False)
        false(check = None)
        false(check = ())
        self.assertRaises(CalledProcessError, false)
        self.assertRaises(CalledProcessError, lambda: false(check = 'x'))

    def test_works(self):
        from . import echo
        self.assertEqual(b'Hello, world!\n', echo('Hello,', 'world!').stdout)
        from .text import echo
        self.assertEqual('Hello, world!\n', echo('Hello,', 'world!').stdout)

    def test_stringify(self):
        from .text import echo
        self.assertEqual(f"text binary 100 eranu{os.sep}uvavu\n", echo('text', b'binary', 100, Path('eranu', 'uvavu')).stdout)

    def test_cd(self):
        from .text import pwd
        self.assertEqual(f"{Path.cwd()}\n", pwd().stdout)
        self.assertEqual(f"{Path.cwd()}\n", pwd(cwd = '.').stdout)
        self.assertEqual('/tmp\n', pwd(cwd = '/tmp').stdout)
        pwd = pwd.cd('/usr')
        self.assertEqual('/usr\n', pwd().stdout)
        self.assertEqual('/usr\n', pwd(cwd = '.').stdout)
        self.assertEqual('/usr/bin\n', pwd(cwd = 'bin').stdout)
        self.assertEqual('/\n', pwd(cwd = '..').stdout)
        self.assertEqual('/tmp\n', pwd(cwd = '/tmp').stdout)
        pwd = pwd.cd('local')
        self.assertEqual('/usr/local\n', pwd().stdout)
        self.assertEqual('/usr/local\n', pwd(cwd = '.').stdout)
        self.assertEqual('/usr/local/bin\n', pwd(cwd = 'bin').stdout)
        self.assertEqual('/usr\n', pwd(cwd = '..').stdout)
        self.assertEqual('/tmp\n', pwd(cwd = '/tmp').stdout)
