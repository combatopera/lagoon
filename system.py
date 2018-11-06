class Program:

    @classmethod
    def scan(cls):
        import os, sys
        programs = {}
        for parent in os.environ['PATH'].split(os.pathsep):
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

Program.scan()
