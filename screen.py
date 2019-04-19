# Copyright 2018, 2019 Andrzej Cichocki

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

from system import screen
import re

def stuff(session, window, text):
    Stuff(session, window)(text)

class Stuff:

    replpattern = re.compile(r'[$^\\]')
    buffersize = 756

    @staticmethod
    def _repl(m):
        return r"\%s" % m.group()

    @classmethod
    def todata(cls, text):
        return cls.replpattern.sub(cls._repl, text).encode()

    def __init__(self, session, window):
        self.session = session
        self.window = window

    def __call__(self, text):
        data = self.todata(text)
        for start in range(0, len(data), self.buffersize):
            self._juststuff(data[start:start + self.buffersize])

    def eof(self):
        self._juststuff('^D')

    def _juststuff(self, data):
        screen('-S', self.session, '-p', self.window, '-X', 'stuff', data)
