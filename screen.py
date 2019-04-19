# Copyright 2018 Andrzej Cichocki

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

replpattern = re.compile(r'[$^\\]')
limit = 756

def _repl(m):
    return r"\%s" % m.group()

def stuff(session, window, text, eof = False):
    text = replpattern.sub(_repl, text)
    if eof:
        text += '^D'
    for start in range(0, len(text), limit):
        screen('-S', session, '-p', window, '-X', 'stuff', text[start:start + limit])
