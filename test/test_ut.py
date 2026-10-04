import inspect
import unittest

import k3ut

dd = k3ut.dd


class TestProcError(unittest.TestCase):
    def test_nothing(self):
        pass


class TestDd(unittest.TestCase):
    def test_dd_reports_its_caller(self):
        # The first dd() call installs ContextFilter on the "pykitut" logger.
        dd("init")

        with self.assertLogs("pykitut", level="DEBUG") as cm:
            dd_line = inspect.currentframe().f_lineno + 1
            dd("hello")

        record = cm.records[0]
        self.assertEqual("test_ut.py", record._fn)
        self.assertEqual(dd_line, record._ln)
        self.assertEqual("test_dd_reports_its_caller", record._func)
