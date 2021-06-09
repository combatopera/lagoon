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
from collections import defaultdict
from contextlib import contextmanager
from keyword import iskeyword
from pathlib import Path
import functools, os, re, subprocess, sys

unimportablechars = re.compile('|'.join(map(re.escape, '+-.[')))

def scan(modulename):
    programs = {}
    for parent in os.environ['PATH'].split(os.pathsep):
        if os.path.isdir(parent):
            for name in os.listdir(parent):
                if name not in programs:
                    programs[name] = os.path.join(parent, name)
    module = sys.modules[modulename]
    delattr(module, scan.__name__)
    Program._scan(module, binary, programs)

class Program:

    @classmethod
    def _importableornone(cls, anyname):
        name = unimportablechars.sub('_', anyname)
        if name.isidentifier() and not iskeyword(name):
            return name

    @staticmethod
    def _strornone(arg):
        return arg if arg is None else str(arg)

    @classmethod
    def _scan(cls, module, binary, programs):
        def install(key):
            setattr(module, key, textprogram)
            setattr(binary, key, binaryprogram)
        importables = defaultdict(list)
        for name in programs:
            importables[cls._importableornone(name)].append(name)
        for importable, names in importables.items():
            for name in names:
                path = programs[name]
                textprogram = cls.text(path)
                binaryprogram = cls.binary(path)
                install(name)
            if 1 == len(names) and importable not in {None, name}:
                install(importable)

    @classmethod
    def text(cls, path):
        return cls(path, True, None, (), {}, _fgmode, 0)

    @classmethod
    def binary(cls, path):
        return cls(path, None, None, (), {}, _fgmode, 0)

    def __init__(self, path, textmode, cwd, args, kwargs, runmode, ttl):
        self.path = path
        self.textmode = textmode
        self.cwd = cwd
        self.args = args
        self.kwargs = kwargs
        self.runmode = runmode
        self.ttl = ttl

    def _resolve(self, path):
        return Path(path) if self.cwd is None else self.cwd / path

    def cd(self, cwd):
        return _of(self, self.path, self.textmode, self._resolve(cwd), self.args, self.kwargs, self.runmode, self.ttl)

    def __getattr__(self, name):
        return _of(self, self.path, self.textmode, self.cwd, self.args + (unmangle(name).replace('_', '-'),), self.kwargs, self.runmode, self.ttl)

    def __getitem__(self, key):
        for style in (styles[k] for k in (key if isinstance(key, tuple) else [key])):
            self = style(self)
        return self

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
            def streamxforms(name):
                val = kwargs[name]
                if val == subprocess.PIPE:
                    yield lambda res: getattr(res, name)
                elif val in {NOEOL, ONELINE}:
                    kwargs[name] = subprocess.PIPE
                    yield lambda res: val(getattr(res, name))
            if not kwargs['check']:
                yield checkxform
            if kwargs.get('stdin') == subprocess.PIPE:
                yield lambda res: res.stdin
            for stream in 'stdout', 'stderr':
                yield from streamxforms(stream)
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
        if self.ttl:
            return _of(self, self.path, self.textmode, self.cwd, self.args + args, self._mergedkwargs(kwargs), self.runmode, self.ttl - 1)
        return self.runmode(self, *args, **kwargs)

def NOEOL(text, trailingnewlines = re.compile(r'[\r\n]*$')):
    return text[:trailingnewlines.search(text).start()]

def ONELINE(text):
    l, = text.splitlines()
    return l

def _of(program, *args, **kwargs):
    return type(program)(*args, **kwargs)

def _partialstyle(program):
    return _of(program, program.path, program.textmode, program.cwd, program.args, program.kwargs, program.runmode, program.ttl + 1)

def _fgmode(program, *args, **kwargs):
    cmd, kwargs, xform = program._transform(args, kwargs, lambda res: res.returncode)
    return xform(subprocess.run(cmd, **kwargs))

def _bgstyle(program):
    return _of(program, program.path, program.textmode, program.cwd, program.args, program.kwargs, _bgmode, program.ttl)

@contextmanager
def _bgmode(program, *args, **kwargs):
    cmd, kwargs, xform = program._transform(args, kwargs, lambda res: res.wait)
    check = kwargs.pop('check')
    try:
        with subprocess.Popen(cmd, **kwargs) as process:
            yield xform(process)
    finally:
        if check and process.returncode:
            raise subprocess.CalledProcessError(process.returncode, cmd)

def _stdoutstyle(token):
    return lambda program: program[partial](stdout = token)

def _teestyle(program):
    return _of(program, program.path, program.textmode, program.cwd, program.args, program.kwargs, _teemode, program.ttl)

def _teemode(program, *args, **kwargs):
    def lines():
        with program[bg](*args, **kwargs) as stdout:
            while True:
                line = stdout.readline()
                if not line:
                    break
                yield line
                sys.stdout.write(line)
    return ''.join(lines())

def _execstyle(program):
    return _of(program, program.path, program.textmode, program.cwd, program.args, program.kwargs, _execmode, program.ttl)

def _execmode(program, *args, **kwargs): # XXX: Flush stdout (and stderr) first?
    supportedkeys = {'cwd', 'env'}
    keys = kwargs.keys()
    if not keys <= supportedkeys:
        raise Exception("Unsupported keywords: %s" % (keys - supportedkeys))
    cmd, kwargs, _ = program._transform(args, kwargs, None)
    cwd, env = (kwargs[k] for k in ['cwd', 'env'])
    if cwd is None:
        os.execvpe(cmd[0], cmd, env)
    # First replace this program so that failure can't be caught after chdir:
    precmd = [sys.executable, '-c', 'import os, sys; cwd, *cmd = sys.argv[1:]; os.chdir(cwd); os.execvp(cmd[0], cmd)', cwd, *cmd]
    os.execve(precmd[0], precmd, os.environ if env is None else env)

bg = object()
partial = object()
tee = object()
styles = {
    bg: _bgstyle,
    exec: _execstyle,
    functools.partial: _partialstyle,
    NOEOL: _stdoutstyle(NOEOL),
    ONELINE: _stdoutstyle(ONELINE),
    partial: _partialstyle,
    print: _stdoutstyle(None),
    tee: _teestyle,
}
