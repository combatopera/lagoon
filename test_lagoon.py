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

from subprocess import CalledProcessError
import unittest

class TestLagoon(unittest.TestCase):

    def test_nosuchprogram(self):
        def imp():
            from lagoon import thisisnotanexecutable
            del thisisnotanexecutable
        self.assertRaises(ImportError, imp)

    def test_false(self):
        from lagoon import false
        false(check = False)
        false(check = None)
        false(check = ())
        self.assertRaises(CalledProcessError, false)
        self.assertRaises(CalledProcessError, lambda: false(check = 'x'))

    def test_works(self):
        from lagoon import echo
        echo.decode = True
        self.assertEqual('Hello, world!\n', echo('Hello,', 'world!').stdout)
