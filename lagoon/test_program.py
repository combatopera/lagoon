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

from .program import Program
from types import SimpleNamespace
from unittest import TestCase

class TestProgram(TestCase):

    def test_importable(self):
        t = SimpleNamespace()
        b = SimpleNamespace()
        Program._scan(t, b, {
            'foo': '/foo',
            'from': '/from',
            'foo-bar': '/foo-bar',
            'g++': '/g++',
            'x++': '/x++',
            'x..': '/x..',
            'woo_yay': '/woo_yay',
            'woo-yay': '/woo-yay',
        })
        for m in t, b:
            self.assertEqual(['foo', 'from', 'foo-bar', 'foo_bar', 'g++', 'g__', 'x++', 'x..', 'woo_yay', 'woo-yay'], list(m.__dict__))
            self.assertEqual('/foo', m.foo.path)
            self.assertEqual('/from', getattr(m, 'from').path)
            self.assertEqual('/foo-bar', getattr(m, 'foo-bar').path)
            self.assertEqual('/foo-bar', m.foo_bar.path)
            self.assertEqual('/g++', getattr(m, 'g++').path)
            self.assertEqual('/g++', m.g__.path)
            self.assertEqual('/x++', getattr(m, 'x++').path)
            self.assertEqual('/x..', getattr(m, 'x..').path)
            self.assertEqual('/woo_yay', m.woo_yay.path)
            self.assertEqual('/woo-yay', getattr(m, 'woo-yay').path)
