"""
unittest utility
"""

import inspect
import logging
import os
import socket
import sys
import tempfile
import time
import unittest
from importlib.metadata import version

__version__ = version("k3ut")

tmpdir = tempfile.gettempdir()

_glb = {
    "pykitut_logger": None,
}

debug_to_stderr = os.environ.get("UT_DEBUG") == "1"


# TODO make this configurable
# logging.basicConfig(level='INFO',
#                     format='[%(asctime)s,%(process)d-%(thread)d,%(filename)s,%(lineno)d,%(levelname)s] %(message)s',
#                     datefmt='%H:%M:%S'
#                     )

# logger = logging.getLogger('kazoo')
# logger.setLevel('INFO')


class Timer(object):
    def __init__(self):
        self.start = None
        self.end = None

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, errtype, errval, _traceback):
        self.end = time.time()

    def spent(self):
        return (self.end or time.time()) - self.start


class ContextFilter(logging.Filter):
    """
    Add correct func, line number, line info to log record.

    To fix the issue that when test case function use dd() instead of
    logger.debug(), logging alwasy print context info of dd(), but not the
    caller test_xxx.
    """

    def filter(self, record):
        # skip this function
        stack = inspect.stack()[1:]

        for i, (frame, path, ln, func, line, xx) in enumerate(stack):
            if frame.f_globals.get("__name__") == "pykitut" and func == "dd":
                # this frame is dd(), find the caller
                _, path, ln, func, line, xx = stack[i + 1]

                record._fn = os.path.basename(path)
                record._ln = ln
                record._func = func
                return True

        record._fn = record.filename
        record._ln = record.lineno
        record._func = record.funcName
        return True


def _init():
    if _glb["pykitut_logger"] is not None:
        return

    log_name = "pykitut"
    lvl = "DEBUG"
    base_dir = tmpdir
    log_fn = log_name + ".out"

    logger = logging.getLogger(log_name)
    logger.setLevel(lvl)

    # do not add 2 handlers to one logger by default
    if len(logger.handlers) == 0:
        log_path = os.path.join(base_dir, log_fn)
        fmt = "[%(asctime)s %(process)d-%(thread)d %(_fn)s:%(_ln)d %(_func)s] %(levelname)s %(message)s"
        datefmt = "%H:%M:%S"

        fh = logging.FileHandler(log_path)
        fh.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
        logger.addHandler(fh)

        logger.addFilter(ContextFilter())

        if debug_to_stderr:
            fmt = "[%(asctime)s %(process)d-%(thread)d %(_fn)s:%(_ln)d %(_func)s] %(levelname)s\n%(message)s"

            stream = sys.stderr
            stdhandler = logging.StreamHandler(stream)
            stdhandler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
            stdhandler.setLevel(lvl)

            logger.addHandler(stdhandler)

    _glb["pykitut_logger"] = logger


def dd(*msg):
    """
    debug level logging in a test case function test_xx.

    dd() write log to stdout if unittest verbosity is 2.
    And dd always write log to log file in /tmp dir.
    """

    s = " ".join([str(x) for x in msg])

    _init()

    logger = _glb["pykitut_logger"]
    if logger:
        logger.debug(s)


def get_ut_verbosity():
    """
    Return the verbosity setting of the currently running unittest
    program, or 0 if none is running.
    """

    frame = _find_frame_by_self(unittest.TestProgram)
    if frame is None:
        return 0

    self = frame.f_locals.get("self")

    return self.verbosity


def get_case_logger():
    """
    Get a case specific logger.
    The logger name is: `<module>.<class>.<function>`,
    such as: `pykit.strutil.test.test_strutil.TestStrutil.test_format_line`

    It must be called inside a test_* function of unittest.TestCase, or no
    correct module/class/function name can be found.
    """

    frame = _find_frame_by_self(unittest.TestCase)

    self = frame.f_locals.get("self")

    module_name = frame.f_globals.get("__name__")
    class_name = self.__class__.__name__
    func_name = frame.f_code.co_name

    nm = module_name + "." + class_name + "." + func_name

    logger = logging.getLogger(nm)
    for f in logger.filters:
        if isinstance(f, ContextFilter):
            break
    else:
        logger.addFilter(ContextFilter())

    return logger


def _find_frame_by_self(clz):
    """
    Find the first frame on stack in which there is local variable 'self' of
    type clz.
    """

    frame = inspect.currentframe()

    while frame:
        self = frame.f_locals.get("self")
        if isinstance(self, clz):
            return frame

        frame = frame.f_back

    return None


def wait_listening(ip, port, timeout=15, interval=0.5):
    # Wait at most `timeout` second for a tcp listening service to serve.

    laste = None
    for ii in range(40):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.connect((ip, port))
            break
        except socket.error as e:
            dd("trying to connect to {0} failed".format(str((ip, port))))
            sock.close()
            time.sleep(0.4)
            laste = e
    else:
        raise laste


def has_env(kv):
    # kv: KEY=value

    k, v = kv.split("=", 1)
    return os.environ.get(k) == v


def pyver():
    return sys.version
