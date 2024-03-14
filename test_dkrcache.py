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

from dkrcache import ExpensiveTask
from lagoon.util import mapcm
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from uuid import uuid4

class TestDkrCache(TestCase):

    class X(Exception): pass

    def test_works(self):
        results = [100]
        with TemporaryDirectory() as context:
            et = ExpensiveTask(context, uuid4(), results.pop)
            for _ in range(2):
                self.assertEqual(100, et.run())
                self.assertFalse(results)

    def test_force(self):
        results = [200, 100]
        with TemporaryDirectory() as context:
            et = ExpensiveTask(context, uuid4(), results.pop)
            self.assertEqual(100, et.run(force = lambda o: True))
            self.assertEqual([200], results)
            self.assertEqual(100, et.run())
            self.assertEqual([200], results)
            self.assertEqual(200, et.run(force = lambda o: True))
            self.assertEqual([], results)
            self.assertEqual(200, et.run())

    def test_failingtask(self):
        def task():
            raise exceptions.pop()
        exceptions = [self.X('boom')]
        with TemporaryDirectory() as context:
            et = ExpensiveTask(context, uuid4(), task)
            for _ in range(2):
                with self.assertRaises(self.X) as cm:
                    et.run()
                self.assertEqual(('boom',), cm.exception.args)
                self.assertFalse(exceptions)

    def test_failingtasknocache(self):
        def task():
            raise exceptions.pop()
        exceptions = [self.X(1), self.X(0)]
        with TemporaryDirectory() as context:
            et = ExpensiveTask(context, uuid4(), task)
            for i in range(2):
                with self.assertRaises(self.X) as cm:
                    et.run(True)
                self.assertEqual((i,), cm.exception.args)
                self.assertEqual(1 - i, len(exceptions))

    def test_othercontext(self):
        results = [200, 100]
        discriminator = uuid4()
        with mapcm(Path, TemporaryDirectory()) as c1, mapcm(Path, TemporaryDirectory()) as c2:
            (c1 / 'src.txt').write_text('woo\n')
            (c2 / 'src.txt').write_text('yay\n')
            et1 = ExpensiveTask(c1, discriminator, results.pop)
            et2 = ExpensiveTask(c2, discriminator, results.pop)
            for _ in range(2):
                self.assertEqual(100, et1.run())
                self.assertEqual(200, et2.run())
                self.assertFalse(results)
