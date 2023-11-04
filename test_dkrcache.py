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

from concurrent.futures import ThreadPoolExecutor
from diapyr.util import invokeall
from dkrcache import ExpensiveTask
from lagoon.util import mapcm
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from uuid import uuid4
import errno, time

class TestDkrCache(TestCase):

    class X(Exception): pass

    def test_works(self):
        results = [100]
        with TemporaryDirectory() as context:
            et = ExpensiveTask(context, uuid4(), results.pop)
            for _ in range(2):
                self.assertEqual(100, et.run())

    def test_failingtask(self):
        def task():
            raise boom
        boom = self.X('boom')
        with TemporaryDirectory() as context:
            et = ExpensiveTask(context, uuid4(), task)
            try:
                et.run()
            except self.X as e:
                self.assertEqual(boom.args, e.args)

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

    def test_concurrent(self):
        def task():
            time.sleep(.5)
        with TemporaryDirectory() as context, ThreadPoolExecutor() as e, self.assertRaises(OSError) as cm:
            invokeall([e.submit(ExpensiveTask(context, uuid4(), task).run).result for _ in range(2)])
        self.assertEqual(errno.EADDRINUSE, cm.exception.errno)
        self.assertIs(None, cm.exception.__context__) # One succeeds.
