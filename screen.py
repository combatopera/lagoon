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

from lagoon import screen
import re

def stuffablescreen(doublequotekey):
    return screen.partial(env = {doublequotekey: '"'})

class Stuff:

    class Part:

        def __init__(self, text):
            self.data = text.encode()

        def consume(self, chunk, maxsize):
            if len(self.data) <= maxsize:
                chunk.append(self.data)
                return True

    class Text(Part):

        def consume(self, chunk, maxsize):
            if super().consume(chunk, maxsize):
                return True
            chunk.append(self.data[:maxsize])
            self.data = self.data[maxsize:]

    replpattern = re.compile(r'[$^\\"]')
    buffersize = 756

    def toparts(self, text):
        mark = 0
        for m in self.replpattern.finditer(text):
            yield self.Text(text[mark:m.start()])
            char = m.group()
            yield self.doublequoteatom if '"' == char else self.Part(r"\%s" % char)
            mark = m.end()
        yield self.Text(text[mark:])

    def __init__(self, session, window, doublequotekey):
        self.session = session
        self.window = window
        self.doublequoteatom = self.Part("${%s}" % doublequotekey)

    def __call__(self, text):
        parts = list(self.toparts(text))
        k = 0
        while k < len(parts):
            maxsize = self.buffersize
            chunk = []
            while k < len(parts) and parts[k].consume(chunk, maxsize):
                maxsize -= len(chunk[-1])
                k += 1
            self._juststuff(b''.join(chunk))

    def interrupt(self):
        self._juststuff('^C')

    def eof(self):
        'May not cause EOF if not at the start of a line.'
        self._juststuff('^D')

    def _juststuff(self, data):
        screen.print('-S', self.session, '-p', self.window, '-X', 'stuff', data)
