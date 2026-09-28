#!/usr/bin/env python
"""Run ambit's test suite: `python runtests.py`."""
import os
import sys

import django
from django.conf import settings


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    django.setup()
    from django.test.utils import get_runner

    runner = get_runner(settings)(verbosity=2)
    sys.exit(bool(runner.run_tests(["tests"])))


if __name__ == "__main__":
    main()
