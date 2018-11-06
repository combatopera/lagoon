#!/usr/bin/env pyven

from system import echo, false
from subprocess import CalledProcessError

def main():
    echo('Hello, world!')
    echo('Hello,', 'world!')
    echo('Hello, world!')
    try:
        false()
    except CalledProcessError:
        pass
    try:
        from system import thisisnotanexecutable
    except ImportError:
        pass

if '__main__' == __name__:
    main()
