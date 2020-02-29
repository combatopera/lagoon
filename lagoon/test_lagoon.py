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
import os, subprocess, unittest

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
        self.assertRaises(subprocess.CalledProcessError, false)
        self.assertRaises(subprocess.CalledProcessError, lambda: false(check = 'x'))

    def test_works(self):
        from .binary import echo
        self.assertEqual(b'Hello, world!\n', echo('Hello,', 'world!'))
        from . import echo
        self.assertEqual('Hello, world!\n', echo('Hello,', 'world!'))

    def test_stringify(self):
        from . import echo
        self.assertEqual("text binary 100 eranu%suvavu\n" % os.sep, echo('text', b'binary', 100, Path('eranu', 'uvavu')))

    def test_cd(self):
        from . import pwd
        self.assertEqual("%s\n" % Path.cwd(), pwd())
        self.assertEqual("%s\n" % Path.cwd(), pwd(cwd = '.'))
        self.assertEqual('/tmp\n', pwd(cwd = '/tmp'))
        pwd = pwd.cd('/usr')
        self.assertEqual('/usr\n', pwd())
        self.assertEqual('/usr\n', pwd(cwd = '.'))
        self.assertEqual('/usr/bin\n', pwd(cwd = 'bin'))
        self.assertEqual('/\n', pwd(cwd = '..'))
        self.assertEqual('/tmp\n', pwd(cwd = '/tmp'))
        pwd = pwd.cd('local')
        self.assertEqual('/usr/local\n', pwd())
        self.assertEqual('/usr/local\n', pwd(cwd = '.'))
        self.assertEqual('/usr/local/bin\n', pwd(cwd = 'bin'))
        self.assertEqual('/usr\n', pwd(cwd = '..'))
        self.assertEqual('/tmp\n', pwd(cwd = '/tmp'))

    def test_resultobj(self):
        from . import false, true
        # If we don't check, we need the returncode:
        self.assertEqual(1, false(check = False).returncode)
        self.assertEqual(0, true(check = False).returncode)
        self.assertEqual(1, false.print(check = False))
        self.assertEqual(0, true.print(check = False))
        # Just stdout:
        self.assertEqual('', true())
        self.assertEqual('', true(stderr = subprocess.STDOUT)) # Capture both streams in stdout field.
        # Capture stderr:
        self.assertEqual('', true(stderr = subprocess.PIPE).stderr)
        self.assertEqual('', true.print(stderr = subprocess.PIPE))
        # Simply return None if there are no fields of interest:
        self.assertEqual(None, true.print())
        self.assertEqual(None, true.print(stderr = subprocess.STDOUT)) # Both streams printed on stdout.
