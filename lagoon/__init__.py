# Copyright 2018, 2019 Andrzej Cichocki

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

class Program:

    @staticmethod
    def _strorbytes(arg):
        return arg if isinstance(arg, bytes) else str(arg)

    @classmethod
    def scan(cls):
        from . import text
        import os, sys
        programs = {}
        for parent in os.environ['PATH'].split(os.pathsep):
            if os.path.isdir(parent):
                for name in os.listdir(parent):
                    if name not in programs:
                        programs[name] = os.path.join(parent, name)
        module = sys.modules[__name__]
        for name, path in programs.items():
            setattr(module, name, cls(path))
            setattr(text, name, text.TextProgram(path))

    def __init__(self, path):
        self.path = path

    def __call__(self, *args, **kwargs):
        import itertools, subprocess
        kwargs.setdefault('check', True)
        kwargs.setdefault('stdout', subprocess.PIPE)
        # TODO: Simply return stdout if there is nothing else of interest.
        return subprocess.run(list(itertools.chain([self.path], map(self._strorbytes, args))), **kwargs)

    def print(self, *args, **kwargs):
        return self(*args, **kwargs, stdout = None)

    def exec(self, *args):
        import os
        os.execv(self.path, [self.path] + list(args))

Program.scan()