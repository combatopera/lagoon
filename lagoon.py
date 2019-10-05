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

    @classmethod
    def scan(cls):
        import os, sys
        programs = {}
        for parent in os.environ['PATH'].split(os.pathsep):
            if os.path.isdir(parent):
                for name in os.listdir(parent):
                    if name not in programs:
                        programs[name] = cls(os.path.join(parent, name))
        module = sys.modules[__name__]
        for name, program in programs.items():
            setattr(module, name, program)

    decode = False

    def __init__(self, path):
        self.path = path

    def __call__(self, *args, **kwargs):
        import subprocess
        kwargs.setdefault('check', True)
        kwargs.setdefault('stdout', subprocess.PIPE)
        completed = subprocess.run([self.path] + list(args), **kwargs)
        if self.decode:
            completed.stdout = completed.stdout.decode()
        return completed

    def exec(self, *args):
        import os
        os.execv(self.path, [self.path] + list(args))

Program.scan()
