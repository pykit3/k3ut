import inspect
import socket
import time
import unittest
import warnings

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


class TestWaitListening(unittest.TestCase):
    def test_wait_listening_gives_up_after_timeout(self):
        # Nothing is bound to a port just released, so every connect() is refused.
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        port = srv.getsockname()[1]
        srv.close()

        t0 = time.time()
        with self.assertRaises(ConnectionRefusedError):
            k3ut.wait_listening("127.0.0.1", port, timeout=0.2, interval=0.1)
        spent = time.time() - t0

        self.assertLess(spent, 2)

    def test_wait_listening_gives_up_on_a_hanging_connect(self):
        # When the accept queue is full, the kernel drops a new SYN, so connect() hangs.
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]

        clients = []
        for _ in range(100):
            c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            c.settimeout(0.2)
            try:
                c.connect(("127.0.0.1", port))
            except TimeoutError:
                c.close()
                break
            clients.append(c)
        else:
            self.fail("the accept queue never filled")

        t0 = time.time()
        with self.assertRaises(TimeoutError):
            k3ut.wait_listening("127.0.0.1", port, timeout=0.5, interval=0.1)
        spent = time.time() - t0

        for c in clients:
            c.close()
        srv.close()

        self.assertLess(spent, 2)

    def test_wait_listening_closes_its_socket(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]

        # CPython warns with ResourceWarning when it frees a socket that is still open.
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ResourceWarning)
            k3ut.wait_listening("127.0.0.1", port)
        srv.close()

        unclosed = [w for w in caught if issubclass(w.category, ResourceWarning)]
        self.assertEqual([], unclosed)
