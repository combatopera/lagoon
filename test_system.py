from subprocess import PIPE, CalledProcessError
import unittest

class TestSystem(unittest.TestCase):

    def test_nosuchprogram(self):
        def imp():
            from system import thisisnotanexecutable
        self.assertRaises(ImportError, imp)

    def test_false(self):
        from system import false
        false(check = False)
        false(check = None)
        false(check = ())
        self.assertRaises(CalledProcessError, false)
        self.assertRaises(CalledProcessError, lambda: false(check = 'x'))

    def test_works(self):
        from system import echo
        echo('Hello, world!')
        echo('Hello,', 'world!')
        print(echo('Hello, world!', stdout = PIPE).stdout)
