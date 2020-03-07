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

    @staticmethod
    def _strornone(arg):
        return arg if arg is None else str(arg)

    @classmethod
    def scan(cls):
        from . import binary
        import os, sys
        programs = {}
        for parent in os.environ['PATH'].split(os.pathsep):
            if os.path.isdir(parent):
                for name in os.listdir(parent):
                    if name not in programs:
                        programs[name] = os.path.join(parent, name)
        module = sys.modules[__name__]
        delattr(module, cls.__name__)
        for name, path in programs.items():
            setattr(module, name, cls(path, True, None, ()))
            setattr(binary, name, cls(path, None, None, ()))

    def __init__(self, path, textmode, cwd, subcommand):
        self.path = path
        self.textmode = textmode
        self.cwd = cwd
        self.subcommand = subcommand

    def _resolve(self, path):
        from pathlib import Path
        return Path(path) if self.cwd is None else self.cwd / path

    def cd(self, cwd):
        return type(self)(self.path, self.textmode, self._resolve(cwd), self.subcommand)

    def __getattr__(self, name):
        return type(self)(self.path, self.textmode, self.cwd, self.subcommand + (name,))

    def __call__(self, *args, **kwargs):
        # TODO: Merge env with current instead of replacing by default.
        import itertools, subprocess
        kwargs.setdefault('check', True)
        kwargs.setdefault('stdout', subprocess.PIPE)
        kwargs.setdefault('stderr', None)
        kwargs.setdefault('universal_newlines', self.textmode)
        kwargs['cwd'] = self._strornone(self._resolve(kwargs['cwd']) if 'cwd' in kwargs else self.cwd)
        completed = subprocess.run(list(itertools.chain([self.path], self.subcommand, map(self._strorbytes, args))), **kwargs)
        fields = set()
        if not kwargs['check']:
            fields.add('returncode')
        if kwargs['stdout'] == subprocess.PIPE:
            fields.add('stdout')
        if kwargs['stderr'] == subprocess.PIPE:
            fields.add('stderr')
        if fields:
            try:
                field, = fields
            except ValueError:
                return completed
            return getattr(completed, field)

    def print(self, *args, **kwargs):
        return self(*args, **kwargs, stdout = None)

    def exec(self, *args):
        import os
        os.execv(self.path, [self.path] + list(args))

Program.scan()
