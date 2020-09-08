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

from . import binary
from .util import unmangle
from contextlib import contextmanager
from keyword import iskeyword
from pathlib import Path
import os, subprocess, sys

class Program:

    @staticmethod
    def _strornone(arg):
        return arg if arg is None else str(arg)

    @classmethod
    def scan(cls, modulename):
        programs = {}
        for parent in os.environ['PATH'].split(os.pathsep):
            if os.path.isdir(parent):
                for name in os.listdir(parent):
                    if name not in programs:
                        programs[name] = os.path.join(parent, name)
        module = sys.modules[modulename]
        delattr(module, cls.__name__)
        def install(key):
            setattr(module, key, textprogram)
            setattr(binary, key, binaryprogram)
        for name, path in programs.items():
            textprogram = cls.text(path)
            binaryprogram = cls.binary(path)
            install(name)
            if '-' in name:
                importable = name.replace('-', '_')
                if importable.isidentifier() and not iskeyword(importable) and importable not in programs:
                    install(importable)

    @classmethod
    def text(cls, path):
        return cls(path, True, None, (), {})

    @classmethod
    def binary(cls, path):
        return cls(path, None, None, (), {})

    def __init__(self, path, textmode, cwd, args, kwargs):
        self.path = path
        self.textmode = textmode
        self.cwd = cwd
        self.args = args
        self.kwargs = kwargs

    def _resolve(self, path):
        return Path(path) if self.cwd is None else self.cwd / path

    def cd(self, cwd):
        return type(self)(self.path, self.textmode, self._resolve(cwd), self.args, self.kwargs)

    def __getattr__(self, name):
        return type(self)(self.path, self.textmode, self.cwd, self.args + (unmangle(name).replace('_', '-'),), self.kwargs)

    def partial(self, *args, **kwargs):
        return type(self)(self.path, self.textmode, self.cwd, self.args + args, self._mergedkwargs(kwargs))

    def _mergedkwargs(self, kwargs):
        merged = {**self.kwargs, **kwargs}
        k = 'env'
        if k in self.kwargs and k in kwargs:
            d1 = self.kwargs[k]
            if d1 is not None: # Otherwise d2 wins, whatever it is.
                d2 = kwargs[k]
                merged[k] = d1 if d2 is None else {**d1, **d2}
        return merged

    def _transform(self, args, kwargs, checkxform):
        args = self.args + args
        kwargs = self._mergedkwargs(kwargs)
        kwargs.setdefault('check', True) # XXX: Support a check function?
        kwargs.setdefault('stdout', subprocess.PIPE)
        kwargs.setdefault('stderr', None)
        kwargs.setdefault('universal_newlines', self.textmode)
        kwargs['cwd'] = self._strornone(self._resolve(kwargs['cwd']) if 'cwd' in kwargs else self.cwd)
        env = kwargs.get('env')
        kwargs['env'] = (None if env is None else
                {**{k: v for k, v in os.environ.items() if env.get(k, v) is not None}, **{k: v for k, v in env.items() if v is not None}})
        aux = kwargs.pop('aux', None)
        readables = {i for i, f in enumerate(args) if getattr(f, 'readable', lambda: False)()}
        if readables:
            i, = readables
            if 'stdin' in kwargs:
                raise ValueError
            kwargs['stdin'] = args[i]
        def transformargs():
            for i, arg in enumerate(args):
                yield '-' if i in readables else (arg if isinstance(arg, bytes) else str(arg))
        def xforms():
            if not kwargs['check']:
                yield checkxform
            if kwargs.get('stdin') == subprocess.PIPE:
                yield lambda res: res.stdin
            if kwargs['stdout'] == subprocess.PIPE:
                yield lambda res: res.stdout
            if kwargs['stderr'] == subprocess.PIPE:
                yield lambda res: res.stderr
            if aux is not None:
                yield lambda res: getattr(res, aux)
        xforms = xforms()
        try:
            xform = next(xforms)
            try:
                next(xforms)
                xform = lambda res: res
            except StopIteration:
                pass
        except StopIteration:
            xform = lambda res: None
        return [self._xformpath(), *transformargs()], kwargs, xform

    def _xformpath(self):
        try:
            is_absolute = self.path.is_absolute
        except AttributeError:
            return self.path
        return self.path if is_absolute() else f"{os.curdir}{os.sep}{self.path}"

    def __call__(self, *args, **kwargs):
        cmd, kwargs, xform = self._transform(args, kwargs, lambda res: res.returncode)
        return xform(subprocess.run(cmd, **kwargs))

    @contextmanager
    def bg(self, *args, **kwargs):
        cmd, kwargs, xform = self._transform(args, kwargs, lambda res: res.wait)
        check = kwargs.pop('check')
        try:
            with subprocess.Popen(cmd, **kwargs) as process:
                yield xform(process)
        finally:
            if check and process.returncode:
                raise subprocess.CalledProcessError(process.returncode, cmd)

    def print(self, *args, **kwargs): # TODO LATER: Allow as non-terminal subcommand.
        return self(*args, **kwargs, stdout = None)

    def tee(self, *args, **kwargs):
        def lines():
            with self.bg(*args, **kwargs) as stdout:
                while True:
                    line = stdout.readline()
                    if not line:
                        break
                    yield line
                    sys.stdout.write(line)
        return ''.join(lines())

    def exec(self, *args, **kwargs):
        supportedkeys = {'cwd', 'env'}
        keys = kwargs.keys()
        if not keys <= supportedkeys:
            raise Exception("Unsupported keywords: %s" % (keys - supportedkeys))
        cmd, kwargs, _ = self._transform(args, kwargs, None)
        cwd, env = (kwargs[k] for k in ['cwd', 'env'])
        if cwd is None:
            os.execvpe(cmd[0], cmd, env)
        # First replace this program so that failure can't be caught after chdir:
        precmd = [sys.executable, '-c', 'import os, sys; cwd, *cmd = sys.argv[1:]; os.chdir(cwd); os.execvp(cmd[0], cmd)', cwd, *cmd]
        os.execve(precmd[0], precmd, os.environ if env is None else env)
