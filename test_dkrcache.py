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
from tempfile import TemporaryDirectory
from unittest import TestCase
from uuid import uuid4

class TestDkrCache(TestCase):

    def test_works(self):
        results = [100]
        with TemporaryDirectory() as context:
            et = ExpensiveTask(context, uuid4(), results.pop)
            for _ in range(2):
                self.assertEqual(100, et.run())

    def test_failingtask(self):
        def task():
            raise boom
        boom = Exception('boom')
        with TemporaryDirectory() as context:
            et = ExpensiveTask(context, uuid4(), task)
            try:
                et.run()
            except Exception as e:
                self.assertEqual(type(boom), type(e))
                self.assertEqual(boom.args, e.args)
