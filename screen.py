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
import re, os

def screenenv(doublequotekey):
    return {**os.environ, doublequotekey: '"'}

class Stuff:

    replpattern = re.compile(r'[$^\\"]')
    buffersize = 756

    def _repl(self, m):
        char = m.group()
        return self.doublequoteexpr if '"' == char else r"\%s" % char

    def todata(self, text):
        return self.replpattern.sub(self._repl, text).encode()

    def __init__(self, session, window, doublequotekey):
        self.session = session
        self.window = window
        self.doublequoteexpr = "${%s}" % doublequotekey

    def __call__(self, text):
        data = self.todata(text)
        for start in range(0, len(data), self.buffersize):
            self._juststuff(data[start:start + self.buffersize])

    def eof(self):
        self._juststuff('^D')

    def _juststuff(self, data):
        screen('-S', self.session, '-p', self.window, '-X', 'stuff', data)
