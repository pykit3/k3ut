# k3ut

[![Action-CI](https://github.com/pykit3/k3ut/actions/workflows/python-package.yml/badge.svg)](https://github.com/pykit3/k3ut/actions/workflows/python-package.yml)
[![Documentation Status](https://readthedocs.org/projects/k3ut/badge/?version=stable)](https://k3ut.readthedocs.io/en/stable/?badge=stable)
[![Package](https://img.shields.io/pypi/pyversions/k3ut)](https://pypi.org/project/k3ut)

Unittest utilities with debug logging and test helpers.

k3ut is a component of [pykit3](https://github.com/pykit3) project: a python3 toolkit set.

## Installation

```bash
pip install k3ut
```

## Quick Start

```python
import k3ut

# Debug logging in tests (writes to /tmp/pykitut.out)
dd = k3ut.dd
dd("debug message", {"key": "value"})

# Timer context manager
with k3ut.Timer() as t:
    # do something
    pass
print(f"Elapsed: {t.spent():.3f}s")

# Get current test verbosity
verbosity = k3ut.get_ut_verbosity()
```

## API Reference

::: k3ut

## License

The MIT License (MIT) - Copyright (c) 2015 Zhang Yanpo (张炎泼)
