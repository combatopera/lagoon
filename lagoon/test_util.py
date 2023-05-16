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

from .util import atomic, mapcm, unmangle
from diapyr.util import singleton
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

@singleton
class Unmangle:

    def __getattr__(self, name):
        return unmangle(name)

class TestUtil(TestCase):

    def _common(self, context):
        exec("""%s:
    # No non-underscore:
    self.assertEqual('_', Unmangle._)
    self.assertEqual('__', Unmangle.__)
    self.assertEqual('___', Unmangle.___)
    self.assertEqual('____', Unmangle.____)
    # Too few leading:
    self.assertEqual('x', Unmangle.x)
    self.assertEqual('x_', Unmangle.x_)
    self.assertEqual('_x', Unmangle._x)
    self.assertEqual('_x_', Unmangle._x_)
    # Too many trailing:
    self.assertEqual('__x__', Unmangle.__x__)
    self.assertEqual('__x___', Unmangle.__x___)
    self.assertEqual('___x__', Unmangle.___x__)
    self.assertEqual('___x___', Unmangle.___x___)
    # Correctly unmangle:
    self.assertEqual('__help', Unmangle.__help)
    self.assertEqual('__log_level', Unmangle.__log_level)
    # Incorrectly unmangle:
    self.assertEqual('__x', Unmangle.___x)
    # Erroneously unmangle:
    self.assertEqual('__x', Unmangle._A__x)
    self.assertEqual('__x', Unmangle._A___x)
    self.assertEqual('__x', Unmangle._A_B__x)
    self.assertEqual('__x', Unmangle._A____x)
    self.assertEqual('__x', Unmangle._A__B__x)
""" % context, dict(globals(), self = self))

    def test_unmangle(self):
        self._common('if True')
        self._common('class _')
        self._common('class A')
        self._common('class A_')
        self._common('class A_B')
        self._common('class A__')
        self._common('class A__B')

class TestAtomic(TestCase):

    def test_works(self):
        for relpath in ['x'], ['x', 'y'], ['x', 'y', 'z']:
            with TemporaryDirectory() as d:
                p = Path(d, *relpath)
                for _ in range(2):
                    with atomic(p) as q, q.open('w') as f:
                        print('doc', file = f)
                    self.assertFalse(q.exists())
                    self.assertEqual('doc\n', p.read_text())

    def test_symlink(self):
        with mapcm(Path, TemporaryDirectory()) as d:
            target = 'target'
            (d / target).write_text('data')
            link = d / 'link'
            link.symlink_to('null')
            with self.assertRaises(FileExistsError):
                link.symlink_to(target)
            with atomic(link) as l:
                l.symlink_to(target)
            self.assertEqual('data', link.read_text())

    def test_fail(self):
        class X(Exception): pass
        with TemporaryDirectory() as d:
            p = Path(d, 'x')
            with self.assertRaises(X), atomic(p) as q, q.open('w') as f:
                print('doc', file = f)
                raise X
            self.assertFalse(q.exists())
            self.assertFalse(p.exists())
