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

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, redirect_stdout
from io import StringIO
from lagoon.program import bg, NOEOL, ONELINE, partial, Program, tee
from lagoon.util import PYTHONPATH
from pathlib import Path
from signal import SIGTERM
from tempfile import TemporaryDirectory, TemporaryFile
from threading import Event
from unittest import TestCase
from uuid import uuid4
import os, stat, subprocess, sys

interpret = Program.text(sys.executable)[partial](env = dict(PYTHONPATH = PYTHONPATH))._c

def _env(items):
    return set(''.join(f"{k}={v}\n" for k, v in items).splitlines())

class TestLagoon(TestCase):

    def test_nosuchprogram(self):
        def imp():
            from lagoon import thisisnotanexecutable
            del thisisnotanexecutable
        self.assertRaises(ImportError, imp)

    def test_false(self):
        from lagoon import false
        false(check = False)
        false(check = None)
        false(check = ())
        self.assertRaises(subprocess.CalledProcessError, false)
        self.assertRaises(subprocess.CalledProcessError, lambda: false(check = 'x'))

    def test_works(self):
        from lagoon.binary import echo
        self.assertEqual(b'Hello, world!\n', echo('Hello,', 'world!'))
        from lagoon import echo
        self.assertEqual('Hello, world!\n', echo('Hello,', 'world!'))

    def test_stringify(self):
        from lagoon import echo
        self.assertEqual("text binary 100 eranu%suvavu\n" % os.sep, echo('text', b'binary', 100, Path('eranu', 'uvavu')))

    def test_cd(self):
        from lagoon import pwd
        self.assertEqual("%s\n" % Path.cwd(), pwd())
        self.assertEqual("%s\n" % Path.cwd(), pwd(cwd = '.'))
        self.assertEqual('/tmp\n', pwd(cwd = '/tmp'))
        pwd = pwd.cd('/usr')
        self.assertEqual('/usr\n', pwd())
        self.assertEqual('/usr\n', pwd(cwd = '.'))
        self.assertEqual('/usr/bin\n', pwd(cwd = 'bin'))
        self.assertEqual('/\n', pwd(cwd = '..'))
        self.assertEqual('/tmp\n', pwd(cwd = '/tmp'))
        pwd = pwd.cd('local')
        self.assertEqual('/usr/local\n', pwd())
        self.assertEqual('/usr/local\n', pwd(cwd = '.'))
        self.assertEqual('/usr/local/bin\n', pwd(cwd = 'bin'))
        self.assertEqual('/usr\n', pwd(cwd = '..'))
        self.assertEqual('/tmp\n', pwd(cwd = '/tmp'))

    def test_resultobj(self):
        from lagoon import false, true
        # If we don't check, we need the returncode:
        self.assertEqual(1, false(check = False).returncode)
        self.assertEqual(0, true(check = False).returncode)
        self.assertEqual(1, false[print](check = False))
        self.assertEqual(0, true[print](check = False))
        # Just stdout:
        self.assertEqual('', true())
        self.assertEqual('', true(stderr = subprocess.STDOUT)) # Capture both streams in stdout field.
        # Capture stderr:
        self.assertEqual('', true(stderr = subprocess.PIPE).stderr)
        self.assertEqual('', true[print](stderr = subprocess.PIPE))
        # Simply return None if there are no fields of interest:
        self.assertEqual(None, true[print]())
        self.assertEqual(None, true[print](stderr = subprocess.STDOUT)) # Both streams printed on stdout.

    def test_autostdin(self):
        from lagoon import diff
        text1 = 'Hark, planet!\n'
        text2 = 'xyz\n'
        with TemporaryDirectory() as d:
            p1 = Path(d, 'text1')
            p2 = Path(d, 'text2')
            with p1.open('w') as f1:
                f1.write(text1)
            with p2.open('w') as f2:
                f2.write(text2)
            # Simple cases:
            diff(p1, p1)
            with p1.open() as f1:
                diff(p1, '-', stdin = f1)
            with p1.open() as f1:
                diff(p1, f1)
            with p1.open() as f1:
                diff('-', p1, stdin = f1)
            with p1.open() as f1:
                diff(f1, p1)
            # Can't use stdin twice:
            with p1.open() as f1, p1.open() as g1, self.assertRaises(ValueError):
                diff(f1, g1)
            # Even if it's the same stream:
            with p1.open() as f1, self.assertRaises(ValueError):
                diff(f1, f1) # XXX: Allow this as diff can handle it?
            # Can't use stdin when input in use:
            diff(p1, '-', input = text1)
            self.assertEqual(1, diff(p1, '-', input = text2, check = False, stdout = subprocess.DEVNULL))
            with p1.open() as f1, self.assertRaises(ValueError):
                diff(p1, f1, input = text2)
            # But None is OK:
            with p1.open() as f1:
                diff(p1, f1, input = None)
            # Can't use stdin when it's already in use:
            with p2.open() as f2:
                self.assertEqual(1, diff(p1, '-', stdin = f2, check = False, stdout = subprocess.DEVNULL))
            with p1.open() as f1, p2.open() as f2, self.assertRaises(ValueError):
                diff(p1, f1, stdin = f2)
            # Even if it's None:
            with p1.open() as f1, self.assertRaises(ValueError):
                diff(p1, f1, stdin = None) # XXX: Too strict?

    def test_bg(self):
        from lagoon import echo, false, true
        with echo[bg]('woo') as stdout:
            self.assertEqual('woo\n', stdout.read())
        with self.assertRaises(subprocess.CalledProcessError) as cm, false:
            pass
        self.assertEqual(1, cm.exception.returncode)
        self.assertEqual([false.path], cm.exception.cmd)
        self.assertIs(None, cm.exception.__context__)
        e = Exception()
        with self.assertRaises(subprocess.CalledProcessError) as cm, false:
            raise e
        self.assertEqual(1, cm.exception.returncode)
        self.assertEqual([false.path], cm.exception.cmd)
        self.assertIs(e, cm.exception.__context__)
        x = Exception()
        with self.assertRaises(Exception) as cm, true:
            raise x
        self.assertIs(x, cm.exception)
        with echo[bg]('woo', check = False) as process:
            self.assertEqual('woo\n', process.stdout.read())
        self.assertEqual(0, process.returncode)
        with echo[bg]('woo', check = False, stdout = subprocess.DEVNULL) as wait:
            self.assertEqual(0, wait())

    def test_partial(self):
        from lagoon import expr
        test100 = expr[partial](100, check = False)
        cp = test100('=', '100')
        self.assertEqual('1\n', cp.stdout)
        self.assertEqual(0, cp.returncode)
        cp = test100('=', 101)
        self.assertEqual('0\n', cp.stdout)
        self.assertEqual(1, cp.returncode)
        self.assertEqual(0, test100('=', 100, stdout = subprocess.DEVNULL))
        with self.assertRaises(subprocess.CalledProcessError):
            test100('=', 101, check = True)
        with test100[bg]('=', 100) as process:
            self.assertEqual('1\n', process.stdout.read())

    def test_partial2(self):
        from lagoon import bash
        git = bash._c[partial]('git "$@"', 'git')
        self.assertEqual('', git.rev_parse())

    def test_altpartial(self):
        from lagoon import echo
        from functools import partial
        woo = echo[partial]('woo')
        self.assertEqual('woo\n', woo())

    def test_stylepartial(self):
        from lagoon import echo
        bgecho = echo[bg][partial]('woo')
        with bgecho() as stdout:
            self.assertEqual('woo\n', stdout.read())

    def test_stylepartial2(self):
        from lagoon import echo
        bgecho = echo[bg, partial]('woo')
        with bgecho() as stdout:
            self.assertEqual('woo\n', stdout.read())

    def test_multipartial(self):
        from lagoon import echo
        self.assertEqual('woo yay houpla\n', echo[partial]('woo')[partial]('yay')('houpla'))
        self.assertEqual('woo yay houpla\n', echo[partial][partial]('woo')('yay')('houpla'))
        self.assertEqual('woo yay houpla\n', echo[partial, partial]('woo')('yay')('houpla'))

    def test_partialprint(self):
        self.assertEqual('woo yay\n', interpret('''from lagoon import echo\nfrom lagoon.program import partial\necho[print, partial]('woo')('yay')'''))
        self.assertEqual('woo yay\n', interpret('''from lagoon import echo\nfrom lagoon.program import partial\necho[partial, print]('woo')('yay')'''))

    def test_bgprint(self):
        self.assertEqual('woo\n', interpret('from lagoon import echo\nfrom lagoon.program import bg\nwith echo[print, bg].woo(): pass'))
        self.assertEqual('woo\n', interpret('from lagoon import echo\nfrom lagoon.program import bg\nwith echo[bg, print].woo(): pass'))
        self.assertEqual('woo\n', interpret('from lagoon import echo\nwith echo[print].woo: pass'))

    def test_env(self):
        from lagoon import env
        # Consistency with regular subprocess:
        self.assertEqual(_env(os.environ.items()),
                set(env().splitlines()))
        self.assertEqual(_env(os.environ.items()),
                set(env(env = None).splitlines()))
        self.assertEqual(_env(os.environ.items()),
                set(env(env = os.environ).splitlines()))
        # We modify the env instead of replacing it:
        self.assertEqual(_env((k, v) for k, v in os.environ.items() if k != 'PATH') | {'PATH=override'},
                set(env(env = dict(PATH = 'override')).splitlines()))
        self.assertEqual(_env(os.environ.items()) | {'TestLagoon=new'},
                set(env(env = dict(TestLagoon = 'new')).splitlines()))
        # Use None to delete an entry:
        self.assertEqual(_env((k, v) for k, v in os.environ.items() if k != 'PATH'),
                set(env(env = dict(PATH = None)).splitlines()))
        # Delete is lenient:
        self.assertEqual(_env(os.environ.items()),
                set(env(env = dict(TestLagoon = None)).splitlines()))
        # Easy enough to replace the env if you really want:
        self.assertEqual([],
                env(env = {k: None for k in os.environ}).splitlines())
        self.assertEqual(['TestLagoon='],
                env(env = dict({k: None for k in os.environ}, TestLagoon = '')).splitlines())
        self.assertEqual(['PATH=x'],
                env(env = dict({k: None for k in os.environ}, PATH = 'x')).splitlines())

    def test_partialenv(self):
        from lagoon import env
        partial1 = env[partial](env = dict(PATH = 'x'))
        partial2 = env[partial](env = dict(TestLagoon = 'y'))
        # Not specifying an env means use the partial one:
        self.assertEqual(_env((k, v) for k, v in os.environ.items() if k != 'PATH') | {'PATH=x'},
                set(partial1().splitlines()))
        self.assertEqual(_env((k, v) for k, v in os.environ.items() if k != 'PATH') | {'PATH=x'},
                set(partial1(env = None).splitlines()))
        self.assertEqual(_env(os.environ.items()) | {'TestLagoon=y'},
                set(partial2().splitlines()))
        self.assertEqual(_env(os.environ.items()) | {'TestLagoon=y'},
                set(partial2(env = None).splitlines()))
        # Specified env is merged with partial env:
        def direct(part, env):
            return part(env = env)
        def indirect(part, env):
            return part[partial](env = env)()
        for method in direct, indirect:
            self.assertEqual(_env((k, v) for k, v in os.environ.items() if k != 'PATH') | {'PATH=x', 'TestLagoon=y'},
                    set(method(partial1, dict(TestLagoon = 'y')).splitlines()))
            self.assertEqual(_env((k, v) for k, v in os.environ.items() if k != 'PATH'),
                    set(method(partial1, dict(PATH = None)).splitlines()))
            self.assertEqual(_env(os.environ.items()),
                    set(method(partial1, os.environ).splitlines()))
            self.assertEqual(_env(os.environ.items()),
                    set(method(partial2, dict(TestLagoon = None)).splitlines()))
            self.assertEqual(_env((k, v) for k, v in os.environ.items() if k != 'PATH') | {'PATH=x', 'TestLagoon=y'},
                    set(method(partial2, dict(PATH = 'x')).splitlines()))
            self.assertEqual(_env(os.environ.items()) | {'TestLagoon=y'},
                    set(method(partial2, os.environ).splitlines()))
            self.assertEqual(['TestLagoon=y'],
                    method(partial2, {k: None for k in os.environ}).splitlines())

    def test_api(self):
        for t in str, Path:
            self.assertEqual('woo\n', Program.text(t('/bin/echo'))('woo'))
            self.assertEqual(b'woo\n', Program.binary(t('/bin/echo'))('woo'))

    def test_tee(self):
        from lagoon import echo
        f = StringIO()
        with redirect_stdout(f):
            result = echo[tee]('woo')
        self.assertEqual('woo\n', result)
        self.assertEqual('woo\n', f.getvalue())

    def test_stdoutclash(self):
        from lagoon import echo
        with TemporaryFile() as f:
            echo[print]('override', stdout = f)
            echo('hmm', stdout = f)
            f.seek(0)
            self.assertEqual(b'override\nhmm\n', f.read())

    def test_nameorrelpath(self):
        with TemporaryDirectory() as d:
            localecho = Path(d, 'echo')
            localecho.write_text('#!/bin/bash\necho LOCAL "$@"\n')
            localecho.chmod(localecho.stat().st_mode | stat.S_IXUSR)
            def fire(program):
                return program('hmm', cwd = d)
            self.assertEqual('hmm\n', fire(Program.text('echo')))
            self.assertEqual('LOCAL hmm\n', fire(Program.text(Path('echo'))))
            def fireexec(programsrc):
                return interpret("from lagoon.program import Program\nfrom pathlib import Path\n%s[exec]('hmm', cwd = %r)" % (programsrc, d))
            self.assertEqual('hmm\n', fireexec('''Program.text('echo')'''))
            self.assertEqual('LOCAL hmm\n', fireexec('''Program.text(Path('echo'))'''))

    def test_execcwd(self):
        with TemporaryDirectory() as d:
            self.assertEqual(f"{os.getcwd()}\n", interpret('from lagoon import pwd\npwd[exec]()'))
            self.assertEqual(f"{d}\n", interpret("from lagoon import pwd\npwd[exec](cwd = %r)" % d))

    def test_aux(self):
        from lagoon import sleep
        with self.assertRaises(subprocess.CalledProcessError) as cm, sleep.inf[bg](stdout = None, aux = 'terminate') as terminate:
            terminate()
        self.assertEqual(-SIGTERM, cm.exception.returncode)

    def test_aux2(self):
        from lagoon import sleep
        with sleep.inf[bg](stdout = None, aux = 'terminate', check = False) as p:
            p.terminate()
            self.assertEqual(-SIGTERM, p.wait())

    def test_noeol(self):
        from lagoon import echo
        self.assertEqual('woo', echo._n.woo[NOEOL]())
        self.assertEqual('woo', echo.woo[NOEOL]())
        self.assertEqual('woo', echo.woo(stdout = NOEOL))
        self.assertEqual('woo\t', Program.text(sys.executable)._c[print]('''import sys\nprint('woo\t', file = sys.stderr)''', stderr = NOEOL))
        self.assertEqual('woo ', echo._n[NOEOL]('woo \r'))
        self.assertEqual('woo ', echo._n[NOEOL]('woo \r\n'))
        self.assertEqual('woo ', echo._n[NOEOL]('woo \n\r'))

    def test_oneline(self):
        from lagoon import echo
        self.assertEqual('woo', echo._n.woo[ONELINE]())
        self.assertEqual('woo', echo.woo[ONELINE]())
        self.assertEqual('woo', echo.woo(stdout = ONELINE))
        self.assertEqual('woo', Program.text(sys.executable)._c[print]('''import sys\nprint('woo', file = sys.stderr)''', stderr = ONELINE))
        with self.assertRaises(ValueError):
            echo[ONELINE]._n('woo\nyay')
        with self.assertRaises(ValueError):
            echo[ONELINE]._n()

    def test_noeolbinary(self):
        from lagoon.binary import echo
        self.assertEqual(b'woo', echo.woo[NOEOL]())

    def test_onelinebinary(self):
        from lagoon.binary import echo
        self.assertEqual(b'woo', echo.woo[ONELINE]())

    def test_json(self):
        from lagoon import echo
        from lagoon.binary import echo as echob
        import json
        self.assertEqual(dict(x = 1), echob[json]._n('{"x": 1}'))
        self.assertEqual(dict(x = 1), echob[json]('{"x": 1}'))
        self.assertEqual(b'', echob[json]('{"x": 1}', stderr = subprocess.PIPE).stderr)
        self.assertEqual(dict(x = 1), echo[json]._n('{"x": 1}'))
        self.assertEqual(dict(x = 1), echo[json]('{"x": 1}'))
        self.assertEqual('', echo[json]('{"x": 1}', stderr = subprocess.PIPE).stderr)

    def test_bglaunchfail(self):
        with self.assertRaises(FileNotFoundError), Program.text(str(uuid4()))[print, bg]():
            pass

    def test_bgauxfail(self):
        'Failure to get aux attr should behave as if it happened in user code, in particular do not leak the process.'
        with TemporaryDirectory() as tempdir:
            path = Path(tempdir, 'output')
            with self.assertRaises(AttributeError), interpret[print, bg](f"import time\ntime.sleep(.5)\nwith open({str(path)!r}, 'w') as f: print('woo', file = f)", aux = 'nosuchattr'):
                pass
            self.assertEqual('woo\n', path.read_text())

    def _bgnested(self, program1, program2, expected1, expected2):
        with program1 as stream1:
            with program2 as stream2:
                self.assertEqual(expected2, stream2.read())
            self.assertEqual(expected1, stream1.read())

    def test_bgnested(self):
        from lagoon import echo
        program = echo.woo
        self._bgnested(program, program, 'woo\n', 'woo\n')

    def test_bgnested2(self):
        from lagoon import echo
        self._bgnested(echo.woo, echo.yay, 'woo\n', 'yay\n')

    def _bgstaggered(self, program1, program2, expected1, expected2):
        def task1():
            with program1 as stream:
                running1.set()
                running2.wait()
                return stream.read()
        def task2():
            running1.wait()
            with program2 as stream:
                running2.set()
                future1.result()
                return stream.read()
        running1 = Event()
        running2 = Event()
        with ThreadPoolExecutor() as e:
            future1 = e.submit(task1)
            future2 = e.submit(task2)
            self.assertEqual(expected1, future1.result())
            self.assertEqual(expected2, future2.result())

    def test_bgstaggered(self):
        from lagoon import echo
        program = echo.woo
        self._bgstaggered(program, program, 'woo\n', 'woo\n')

    def test_bgstaggered2(self):
        from lagoon import echo
        self._bgstaggered(echo.woo, echo.yay, 'woo\n', 'yay\n')

    def test_bgstaggered3(self):
        from lagoon import echo
        stack1 = ExitStack()
        stack2 = ExitStack()
        stream1 = stack1.enter_context(echo.woo)
        stream2 = stack2.enter_context(echo.yay)
        self.assertEqual('woo\n', stream1.read())
        stack1.close()
        self.assertEqual('yay\n', stream2.read())
        stack2.close()

    def test_boolcheck(self):
        from lagoon import false, true
        false = false[print]
        true = true[print]
        self.assertIs(False, false(check = bool))
        self.assertIs(True, true(check = bool))
        with false[partial](check = bool) as w:
            self.assertIs(False, w())
        with true[partial](check = bool) as w:
            self.assertIs(True, w())
        self.assertIs(False, false[bool]())
        self.assertIs(True, true[bool]())
        with false[bool] as w:
            self.assertIs(False, w())
        with true[bool] as w:
            self.assertIs(True, w())
