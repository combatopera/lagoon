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

from dkrcache import ALWAYS, ExpensiveTask, NEVER
from lagoon.util import mapcm
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from uuid import uuid4

class TestDkrCache(TestCase):

    class X(Exception): pass

    def setUp(self):
        self.infos = []

    def tearDown(self):
        self.assertFalse(self.infos)

    def info(self, *args):
        self.infos.append(args)

    def _popinfo(self):
        return self.infos.pop(0)

    def test_works(self):
        results = [100]
        with TemporaryDirectory() as context:
            et = ExpensiveTask(context, uuid4(), results.pop)
            et.log = self
            self.assertEqual(100, et.run())
            self.assertFalse(results)
            format, image = self._popinfo()
            self.assertEqual("Cached as: %s", format)
            self.assertEqual(100, et.run(cache = lambda o: self.fail('Should not be called.')))
            self.assertEqual(("Cache hit%s: %s", '', image), self._popinfo())

    def test_nocache(self):
        results = [200, 100]
        with TemporaryDirectory() as context:
            et = ExpensiveTask(context, uuid4(), results.pop)
            et.log = self
            for i, x in enumerate([100, 200]):
                self.assertEqual(x, et.run(cache = NEVER))
                self.assertEqual(1 - i, len(results))

    def test_failingtask(self):
        def task():
            raise exceptions.pop()
        exceptions = [self.X('boom')]
        with TemporaryDirectory() as context:
            et = ExpensiveTask(context, uuid4(), task)
            et.log = self
            with self.assertRaises(self.X) as cm:
                et.run(cache = ALWAYS)
            self.assertEqual(('boom',), cm.exception.args)
            self.assertFalse(exceptions)
            format, image = self._popinfo()
            self.assertEqual("Cached as: %s", format)
            with self.assertRaises(self.X) as cm:
                et.run(cache = lambda o: self.fail('Should not be called.'))
            self.assertEqual(('boom',), cm.exception.args)
            self.assertEqual(("Cache hit%s: %s", '', image), self._popinfo())

    def test_failingtasknocache(self):
        def task():
            raise exceptions.pop()
        exceptions = [self.X(1), self.X(0)]
        with TemporaryDirectory() as context:
            et = ExpensiveTask(context, uuid4(), task)
            et.log = self
            for i in range(2):
                with self.assertRaises(self.X) as cm:
                    et.run()
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

    def test_force(self):
        results = [200, 100]
        with TemporaryDirectory() as context:
            et = ExpensiveTask(context, uuid4(), results.pop)
            et.log = self
            self.assertEqual(100, et.run(force = lambda o: self.fail('Should not be called.')))
            self.assertEqual([200], results)
            format, image = self._popinfo()
            self.assertEqual("Cached as: %s", format)
            self.assertEqual(100, et.run())
            self.assertEqual([200], results)
            self.assertEqual(("Cache hit%s: %s", '', image), self._popinfo())
            self.assertEqual(100, et.run(force = lambda o: 101 == o.result()))
            self.assertEqual([200], results)
            self.assertEqual(("Cache hit%s: %s", '', image), self._popinfo())
            self.assertEqual(200, et.run(force = lambda o: 100 == o.result()))
            self.assertEqual([], results)
            self.assertEqual(("Cache hit%s: %s", ' and drop', image), self._popinfo())
            format, image = self._popinfo()
            self.assertEqual("Cached as: %s", format)
            self.assertEqual(200, et.run())
            self.assertEqual(("Cache hit%s: %s", '', image), self._popinfo())
