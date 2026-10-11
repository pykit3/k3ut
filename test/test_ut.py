import inspect
import socket
import time
import unittest
import warnings
from unittest import mock

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

    def test_wait_listening_bounds_each_wait_by_timeout(self):
        # interval is longer than timeout, so the time left must bound both connect() and the sleep after it.
        sock = mock.MagicMock()
        sock.__enter__.return_value = sock
        sock.connect.side_effect = TimeoutError("timed out")

        t0 = time.monotonic()
        with mock.patch("socket.socket", return_value=sock), self.assertRaises(TimeoutError):
            k3ut.wait_listening("127.0.0.1", 1, timeout=0.05, interval=1)
        spent = time.monotonic() - t0

        first_timeout = sock.settimeout.call_args_list[0].args[0]
        self.assertLessEqual(first_timeout, 0.05)
        self.assertLess(spent, 0.5)

    def test_wait_listening_rejects_a_nonpositive_interval(self):
        for interval in (0, -1):
            with self.assertRaises(ValueError):
                k3ut.wait_listening("127.0.0.1", 1, timeout=0.05, interval=interval)

    def test_wait_listening_retries_a_failed_socket(self):
        # socket() fails when the process runs out of file descriptors.
        with (
            mock.patch("socket.socket", side_effect=OSError(24, "Too many open files")) as socket_cls,
            self.assertRaises(OSError) as ctx,
        ):
            k3ut.wait_listening("127.0.0.1", 1, timeout=0.05, interval=0.01)

        self.assertEqual(24, ctx.exception.errno)
        self.assertGreater(socket_cls.call_count, 1)

    def test_wait_listening_connects_after_a_refusal(self):
        sock = mock.MagicMock()
        sock.__enter__.return_value = sock
        sock.connect.side_effect = [ConnectionRefusedError(61, "Connection refused"), None]

        with mock.patch("socket.socket", return_value=sock):
            k3ut.wait_listening("127.0.0.1", 1, timeout=1, interval=0.01)

        self.assertEqual([mock.call(("127.0.0.1", 1))] * 2, sock.connect.call_args_list)

    def test_wait_listening_closes_the_socket_when_setsockopt_fails(self):
        sock = mock.MagicMock()
        sock.__enter__.return_value = sock
        sock.setsockopt.side_effect = OSError(22, "Invalid argument")

        with mock.patch("socket.socket", return_value=sock), self.assertRaises(OSError) as ctx:
            k3ut.wait_listening("127.0.0.1", 1, timeout=0.05, interval=0.01)

        self.assertEqual(22, ctx.exception.errno)
        self.assertEqual(0, sock.connect.call_count)
        self.assertEqual(sock.setsockopt.call_count, sock.__exit__.call_count)

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
